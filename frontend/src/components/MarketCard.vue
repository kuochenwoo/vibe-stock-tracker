<script setup>
import * as echarts from "echarts/core";
import { GridComponent, TooltipComponent } from "echarts/components";
import { LineChart } from "echarts/charts";
import { CanvasRenderer } from "echarts/renderers";
import { computed, nextTick, onBeforeUnmount, onMounted, onUpdated, ref, watch } from "vue";

echarts.use([LineChart, GridComponent, TooltipComponent, CanvasRenderer]);

const DEFAULT_API_BASE =
  typeof window === "undefined"
    ? "http://127.0.0.1:8000"
    : `${window.location.protocol}//${window.location.hostname}:8000`;
const API_BASE = import.meta.env.VITE_API_BASE ?? DEFAULT_API_BASE;
const MOVING_AVERAGE_WINDOWS = [
  { key: "ma20", label: "MA20", window: 20, color: "#f59e0b" },
  { key: "ma30", label: "MA30", window: 30, color: "#7c5cff" },
  { key: "ma60", label: "MA60", window: 60, color: "#00a3a3" },
];

const props = defineProps({
  card: {
    type: Object,
    required: true,
  },
  onDelete: {
    type: Function,
    default: null,
  },
  isExpanded: {
    type: Boolean,
    default: false,
  },
  isDeleting: {
    type: Boolean,
    default: false,
  },
  hasActiveAlarm: {
    type: Boolean,
    default: false,
  },
  alertSummary: {
    type: Object,
    default: () => ({ count: 0, alerts: [] }),
  },
  layoutVersion: {
    type: Number,
    default: 0,
  },
});
const emit = defineEmits(["open-alarm", "expanded-change"]);

const actionMenuOpen = ref(false);
const actionMenuRef = ref(null);
const collapsedControlsRef = ref(null);
const chartCanvasRef = ref(null);
const backgroundFlashTone = ref("");
const selectedRange = ref("1d");
const yearHistory = ref(null);
const yearHistoryLoading = ref(false);
const yearHistoryError = ref("");
const activeMovingAverages = ref([]);
const maMenuOpen = ref(false);

let chartInstance = null;
let resizeObserver = null;
let backgroundFlashTimer = null;
const ACTION_MENU_EVENT = "market-card-action-menu-open";

function toggleExpanded() {
  const nextExpanded = !props.isExpanded;
  if (!nextExpanded) {
    actionMenuOpen.value = false;
    disposeChart();
  }
  emit("expanded-change", {
    code: props.card.code,
    expanded: nextExpanded,
  });
}

function openAlarmDrawer() {
  emit("expanded-change", {
    code: props.card.code,
    expanded: true,
  });
  emit("open-alarm", {
    code: props.card.code,
    name: props.card.title,
    symbol: props.card.subtitle,
    price: props.card.data?.price ?? null,
    change: props.card.data?.change ?? null,
    change_percent: props.card.data?.change_percent ?? null,
  });
  actionMenuOpen.value = false;
}

async function handleDeleteTicker() {
  const confirmed = window.confirm(`Delete ${props.card.code} from tracked tickers?`);
  if (!confirmed) {
    return;
  }
  actionMenuOpen.value = false;
  await props.onDelete?.(props.card.code);
}

function toggleActionMenu() {
  const nextOpen = !actionMenuOpen.value;
  if (nextOpen) {
    window.dispatchEvent(
      new CustomEvent(ACTION_MENU_EVENT, {
        detail: { code: props.card.code },
      }),
    );
  }
  actionMenuOpen.value = nextOpen;
}

function handleOutsideClick(event) {
  if (!actionMenuOpen.value) return;
  if (actionMenuRef.value?.contains(event.target)) return;
  actionMenuOpen.value = false;
}

function handleOtherMenuOpened(event) {
  if (event.detail?.code === props.card.code) return;
  actionMenuOpen.value = false;
}

function syncCollapsedControlsWidth() {
  const elements = Array.from(document.querySelectorAll(".card-collapsed-controls"));
  const maxWidth = elements.reduce((largest, element) => {
    return Math.max(largest, Math.ceil(element.getBoundingClientRect().width));
  }, 0);

  document.documentElement.style.setProperty("--collapsed-controls-width", `${maxWidth || 0}px`);
}

function formatPrice(value) {
  if (typeof value !== "number") return "--";
  return value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatDelta(value) {
  if (typeof value !== "number") return "--";
  return `${value > 0 ? "+" : ""}${value.toFixed(2)}`;
}

function formatPercent(value) {
  if (typeof value !== "number") return "--";
  return `${value > 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function formatAlarmValue(value) {
  if (typeof value !== "number") return "--";
  return value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatCollapsedPriceParts(value) {
  if (typeof value !== "number") {
    return { integer: "--", decimal: "" };
  }

  const [integer, decimal] = value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).split(".");

  return {
    integer,
    decimal: decimal ? `.${decimal}` : "",
  };
}

const activeHistoryState = computed(() => {
  if (selectedRange.value === "1y") {
    return {
      points: yearHistory.value?.points ?? [],
      startedAt: yearHistory.value?.startedAt ?? null,
      endedAt: yearHistory.value?.endedAt ?? null,
      loading: yearHistoryLoading.value,
      error: yearHistoryError.value,
    };
  }

  const points = props.card.history ?? [];
  return {
    points,
    startedAt: props.card.historyStartedAt ?? points[0]?.timestamp ?? null,
    endedAt: points.at(-1)?.timestamp ?? null,
    loading: false,
    error: "",
  };
});

const chartPlotPoints = computed(() => {
  const history = activeHistoryState.value.points ?? [];
  return history
    .map((point) => ({
      timestamp: point?.timestamp ?? null,
      price: Number(point?.price),
    }))
    .filter((point) => Number.isFinite(point.price));
});

const chartWindowStart = computed(() => {
  const explicitStart = activeHistoryState.value.startedAt;
  if (explicitStart) {
    const parsed = new Date(explicitStart);
    if (!Number.isNaN(parsed.getTime())) {
      return parsed;
    }
  }

  const firstPoint = chartPlotPoints.value[0]?.timestamp;
  if (firstPoint) {
    const parsed = new Date(firstPoint);
    if (!Number.isNaN(parsed.getTime())) {
      return parsed;
    }
  }

  return null;
});

const chartWindowEnd = computed(() => {
  if (!chartWindowStart.value) return null;
  if (selectedRange.value === "1y") {
    const explicitEnd = activeHistoryState.value.endedAt;
    if (explicitEnd) {
      const parsed = new Date(explicitEnd);
      if (!Number.isNaN(parsed.getTime())) {
        return parsed;
      }
    }
    return new Date(chartWindowStart.value.getTime() + 365 * 24 * 60 * 60 * 1000);
  }
  return new Date(chartWindowStart.value.getTime() + 24 * 60 * 60 * 1000);
});

const chartValues = computed(() => {
  return chartPlotPoints.value.map((point) => point.price);
});

const priceTone = computed(() => {
  const fiveMinuteChange = props.card.data?.five_min_change;

  if (typeof fiveMinuteChange !== "number") {
    return "";
  }

  if (fiveMinuteChange > 0) return "price-up";
  if (fiveMinuteChange < 0) return "price-down";
  return "price-flat";
});

function toneFromFiveMinuteChange(value) {
  if (typeof value !== "number") return "";
  if (value > 0) return "up";
  if (value < 0) return "down";
  return "";
}

const collapsedPriceParts = computed(() => formatCollapsedPriceParts(props.card.data?.price));

const intradayHigh = computed(() => {
  const values = chartValues.value;
  if (!values.length) return null;
  return Math.max(...values);
});

const intradayLow = computed(() => {
  const values = chartValues.value;
  if (!values.length) return null;
  return Math.min(...values);
});
const marketStateTone = computed(() => {
  return props.card.data?.market_state === "LIVE" ? "metric-live" : "metric-offline";
});

const movingAverageOptions = computed(() =>
  MOVING_AVERAGE_WINDOWS.map((option) => ({
    ...option,
    active: activeMovingAverages.value.includes(option.key),
  })),
);

function formatHoverTime(value) {
  if (!value) return "--";
  const formatOptions =
    selectedRange.value === "1y"
      ? {
          year: "numeric",
          month: "short",
          day: "numeric",
        }
      : {
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        };

  return new Intl.DateTimeFormat(undefined, formatOptions).format(new Date(value));
}

function setRange(nextRange) {
  if (selectedRange.value === nextRange) return;
  selectedRange.value = nextRange;
}

function toggleMovingAverage(key) {
  activeMovingAverages.value = activeMovingAverages.value.includes(key)
    ? activeMovingAverages.value.filter((item) => item !== key)
    : [...activeMovingAverages.value, key];
}

function openMaMenu() {
  maMenuOpen.value = true;
}

function closeMaMenu() {
  maMenuOpen.value = false;
}

async function ensureYearHistory() {
  if (yearHistory.value || yearHistoryLoading.value) {
    return;
  }

  yearHistoryLoading.value = true;
  yearHistoryError.value = "";
  try {
    const response = await fetch(`${API_BASE}/api/markets/${props.card.code}/history?range=1y`);
    if (!response.ok) {
      throw new Error("Failed to load 1Y history.");
    }

    const payload = await response.json();
    yearHistory.value = {
      points: Array.isArray(payload?.points)
        ? payload.points
            .map((point) => ({
              timestamp: point.timestamp,
              price: Number(point.price),
            }))
            .filter((point) => Number.isFinite(point.price))
        : [],
      startedAt: payload?.started_at ?? payload?.points?.[0]?.timestamp ?? null,
      endedAt:
        payload?.ended_at ??
        (Array.isArray(payload?.points) && payload.points.length
          ? payload.points[payload.points.length - 1].timestamp
          : null),
    };
  } catch (error) {
    yearHistoryError.value = error instanceof Error ? error.message : "Failed to load 1Y history.";
  } finally {
    yearHistoryLoading.value = false;
  }
}

const movingAverageSeries = computed(() => {
  if (selectedRange.value !== "1y") {
    return [];
  }

  return movingAverageOptions.value
    .filter((option) => option.active)
    .map((option) => ({
      ...option,
      points: buildMovingAverageSeries(chartPlotPoints.value, option.window),
    }))
    .filter((option) => option.points.some((point) => point[1] != null));
});

const movingAverageReadings = computed(() =>
  movingAverageSeries.value
    .map((series) => {
      const lastPoint = [...series.points].reverse().find((point) => point[1] != null);
      return {
        key: series.key,
        label: series.label,
        color: series.color,
        value: lastPoint?.[1] ?? null,
      };
    })
    .filter((series) => typeof series.value === "number"),
);

function initChart() {
  if (!chartCanvasRef.value) return;
  if (chartInstance?.getDom?.() === chartCanvasRef.value) return;
  disposeChart();

  chartInstance = echarts.init(chartCanvasRef.value, null, {
    renderer: "canvas",
  });
  updateChart();

  if (typeof ResizeObserver !== "undefined") {
    resizeObserver = new ResizeObserver(() => {
      chartInstance?.resize();
    });
    resizeObserver.observe(chartCanvasRef.value);
  }
}

function disposeChart() {
  resizeObserver?.disconnect();
  resizeObserver = null;
  chartInstance?.dispose();
  chartInstance = null;
}

function updateChart() {
  if (!chartInstance) return;

  const points = chartPlotPoints.value;
  if (points.length === 0) {
    chartInstance.clear();
    return;
  }

  const previousClose = props.card.data?.previous_close;
  const lastPrice = props.card.data?.price ?? points.at(-1)?.price ?? null;
  const windowStart = chartWindowStart.value;
  const windowEnd = chartWindowEnd.value;
  const prevCloseLineData =
    selectedRange.value === "1d" &&
    typeof previousClose === "number" &&
    windowStart &&
    windowEnd
      ? [
          [windowStart.getTime(), previousClose],
          [windowEnd.getTime(), previousClose],
        ]
      : [];

  chartInstance.setOption(
    {
      animation: false,
      grid: {
        left: 0,
        right: 0,
        top: 2,
        bottom: 0,
        containLabel: false,
      },
      tooltip: {
        trigger: "axis",
        confine: true,
        appendToBody: false,
        backgroundColor: "rgba(255,255,255,0.98)",
        borderColor: "rgba(91, 107, 134, 0.18)",
        borderWidth: 1,
        padding: [8, 10],
        textStyle: {
          color: "#182230",
          fontSize: 12,
        },
        extraCssText:
          "box-shadow: 0 14px 28px rgba(58, 76, 102, 0.16); border-radius: 12px;",
        formatter(params) {
          const items = Array.isArray(params) ? params : [params];
          const priceItem = items.find((item) => item.seriesType === "line" && item.seriesName !== "MA20" && item.seriesName !== "MA30" && item.seriesName !== "MA60") ?? items[0];
          const point = points[priceItem?.dataIndex];
          const maRows = items
            .filter((item) => item.seriesName === "MA20" || item.seriesName === "MA30" || item.seriesName === "MA60")
            .filter((item) => Array.isArray(item.data) && item.data[1] != null)
            .map(
              (item) => `
                <span style="display:flex;justify-content:space-between;gap:12px;">
                  <span style="color:${item.color};font-weight:700;">${item.seriesName}</span>
                  <strong style="font-size:12px;font-weight:700;">${formatPrice(item.data[1])}</strong>
                </span>
              `,
            )
            .join("");

          return `
            <div style="display:grid;grid-template-columns:auto ${maRows ? "auto" : ""};gap:12px;align-items:start;">
              <div style="display:grid;gap:4px;">
                <strong style="font-size:13px;">${formatPrice(point?.price)}</strong>
                <span style="color:#627085;font-size:11px;">${formatHoverTime(point?.timestamp)}</span>
              </div>
              ${maRows ? `<div style="display:grid;gap:4px;min-width:108px;padding-left:12px;border-left:1px solid rgba(91, 107, 134, 0.14);">${maRows}</div>` : ""}
            </div>
          `;
        },
        axisPointer: {
          type: "line",
          snap: true,
          lineStyle: {
            color: "rgba(24, 34, 48, 0.22)",
            width: 1,
            type: "dashed",
          },
        },
      },
      xAxis: {
        type: "time",
        min: windowStart ? windowStart.getTime() : undefined,
        max: windowEnd ? windowEnd.getTime() : undefined,
        show: false,
      },
      yAxis: {
        type: "value",
        show: false,
        scale: true,
      },
      series: [
        ...(prevCloseLineData.length
          ? [
              {
                type: "line",
                name: "Prev Close",
                data: prevCloseLineData,
                symbol: "none",
                silent: true,
                lineStyle: {
                  color: "rgba(95, 113, 138, 0.72)",
                  width: 1.1,
                  type: "dashed",
                },
                z: 1,
              },
            ]
          : []),
        {
          type: "line",
          name: "Price",
          data: points.map((point) => [new Date(point.timestamp).getTime(), point.price]),
          smooth: false,
          symbol: "circle",
          showSymbol: points.length === 1,
          symbolSize: 4,
          lineStyle: {
            color: "#1565c0",
            width: 1.1,
          },
          areaStyle: {
            color: {
              type: "linear",
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: "rgba(62, 166, 255, 0.16)" },
                { offset: 1, color: "rgba(62, 166, 255, 0)" },
              ],
            },
          },
          markLine: {
            symbol: "none",
            silent: true,
            animation: false,
            label: {
              show: false,
            },
            lineStyle: {
              width: 1,
            },
            data: [
              ...(typeof lastPrice === "number"
                ? [
                    {
                      yAxis: lastPrice,
                      lineStyle: {
                        color: "rgba(21, 101, 192, 0.26)",
                        type: "dashed",
                      },
                    },
                  ]
                : []),
            ],
          },
        },
        ...movingAverageSeries.value.map((series) => ({
          type: "line",
          name: series.label,
          data: series.points,
          smooth: false,
          symbol: "none",
          connectNulls: false,
          lineStyle: {
            color: series.color,
            width: 1,
            opacity: 0.95,
          },
          emphasis: {
            disabled: true,
          },
        })),
      ],
    },
    true,
  );
}

function buildMovingAverageSeries(points, windowSize) {
  const closes = points.map((point) => point.price);
  return points.map((point, index) => {
    if (index + 1 < windowSize) {
      return [new Date(point.timestamp).getTime(), null];
    }

    const window = closes.slice(index + 1 - windowSize, index + 1);
    const average = window.reduce((sum, value) => sum + value, 0) / window.length;
    return [new Date(point.timestamp).getTime(), Number(average.toFixed(6))];
  });
}

onMounted(() => {
  document.addEventListener("click", handleOutsideClick);
  window.addEventListener(ACTION_MENU_EVENT, handleOtherMenuOpened);
  nextTick(syncCollapsedControlsWidth);
  nextTick(initChart);
});

onBeforeUnmount(() => {
  document.removeEventListener("click", handleOutsideClick);
  window.removeEventListener(ACTION_MENU_EVENT, handleOtherMenuOpened);
  if (backgroundFlashTimer) {
    window.clearTimeout(backgroundFlashTimer);
  }
  nextTick(syncCollapsedControlsWidth);
  disposeChart();
  emit("expanded-change", {
    code: props.card.code,
    expanded: false,
  });
});

onUpdated(() => {
  nextTick(syncCollapsedControlsWidth);
});

watch(
  () => props.isExpanded,
  (isExpanded) => {
    nextTick(syncCollapsedControlsWidth);
    if (isExpanded) {
      ensureYearHistory();
      nextTick(() => {
        initChart();
        chartInstance?.resize();
        updateChart();
      });
    } else {
      actionMenuOpen.value = false;
      disposeChart();
    }
  },
);

watch(
  selectedRange,
  (nextRange) => {
    if (nextRange === "1y") {
      ensureYearHistory();
    } else {
      activeMovingAverages.value = [];
      maMenuOpen.value = false;
    }
    nextTick(updateChart);
  },
);

watch(
  () => props.layoutVersion,
  () => {
    if (!props.isExpanded) return;
    nextTick(() => {
      window.requestAnimationFrame(() => {
        chartInstance?.resize();
        updateChart();
      });
    });
  },
);

watch(
  [chartPlotPoints, movingAverageSeries, () => props.card.data?.previous_close, () => props.card.data?.price, selectedRange],
  () => {
    nextTick(updateChart);
  },
  { deep: true },
);

watch(
  () => props.card.data?.price,
  (nextPrice, previousPrice) => {
    if (typeof nextPrice !== "number" || typeof previousPrice !== "number" || nextPrice === previousPrice) {
      return;
    }

    const tone = toneFromFiveMinuteChange(props.card.data?.five_min_change);
    if (!tone) {
      backgroundFlashTone.value = "";
      return;
    }

    backgroundFlashTone.value = `market-card-flash-${tone}`;
    if (backgroundFlashTimer) {
      window.clearTimeout(backgroundFlashTimer);
    }
    backgroundFlashTimer = window.setTimeout(() => {
      backgroundFlashTone.value = "";
    }, 5000);
  },
);

</script>

<template>
  <article
    :class="[
      'market-card',
      backgroundFlashTone,
      {
        'market-card-menu-open': actionMenuOpen,
        'market-card-removing': isDeleting,
      },
    ]"
  >
    <div v-if="isExpanded">
      <div class="card-head">
        <div>
          <div class="card-subtitle-row">
            <p class="label">{{ card.subtitle }}</p>
            <span
              v-if="hasActiveAlarm"
              class="alarm-indicator alarm-indicator-subtitle"
              aria-label="Alarm set"
              title="Alarm set"
            >
              <svg viewBox="0 0 20 20" aria-hidden="true">
                <path
                  d="M10 17a2.1 2.1 0 0 0 2-1.5H8A2.1 2.1 0 0 0 10 17Zm5-3.5H5l1.2-1.5V8.6A3.9 3.9 0 0 1 9 4.82V4.5a1 1 0 1 1 2 0v.32a3.9 3.9 0 0 1 2.8 3.78V12l1.2 1.5Z"
                  fill="currentColor"
                />
              </svg>
            </span>
          </div>
          <h2>{{ card.title }}</h2>
        </div>
        <div class="card-head-actions">
          <span :class="['badge', priceTone]">{{ card.code }}</span>
          <div ref="actionMenuRef" class="card-action-menu">
            <button class="action-btn" type="button" aria-label="Open actions menu" @click.stop="toggleActionMenu">...</button>
            <div
              v-if="actionMenuOpen"
              class="action-menu-list"
            >
              <button
                class="action-menu-item"
                type="button"
                @click.stop="openAlarmDrawer"
              >
                Set alarm
              </button>
              <button
                class="action-menu-item action-menu-item-delete"
                type="button"
                @click.stop="handleDeleteTicker"
              >
                Delete ticker
              </button>
            </div>
          </div>
          <button class="collapse-btn" type="button" @click="toggleExpanded">−</button>
        </div>
      </div>

      <div class="price-row">
        <p :class="['price', priceTone]">{{ formatPrice(card.data?.price) }}</p>
        <span :class="['price-percent-inline', priceTone]">{{ formatPercent(card.data?.change_percent) }}</span>
      </div>

      <button
        v-if="alertSummary.count"
        class="alarm-summary"
        type="button"
        @click="openAlarmDrawer"
      >
        <p class="alarm-summary-copy">
          <span class="alarm-summary-count">{{ alertSummary.count }} active {{ alertSummary.count === 1 ? "alarm" : "alarms" }}</span>
          <span class="alarm-summary-separator"> · </span>
          {{ alertSummary.alerts.slice(0, 2).map((rule) => `${rule.direction} ${formatAlarmValue(rule.value)}`).join(" · ") }}
          <span v-if="alertSummary.count > 2"> · +{{ alertSummary.count - 2 }} more</span>
        </p>
      </button>
    </div>

    <div v-else class="card-head card-head-collapsed">
      <div class="card-collapsed-copy">
        <div>
          <div class="card-subtitle-row">
            <p class="label">{{ card.subtitle }}</p>
            <span
              v-if="hasActiveAlarm"
              class="alarm-indicator alarm-indicator-subtitle"
              aria-label="Alarm set"
              title="Alarm set"
            >
              <svg viewBox="0 0 20 20" aria-hidden="true">
                <path
                  d="M10 17a2.1 2.1 0 0 0 2-1.5H8A2.1 2.1 0 0 0 10 17Zm5-3.5H5l1.2-1.5V8.6A3.9 3.9 0 0 1 9 4.82V4.5a1 1 0 1 1 2 0v.32a3.9 3.9 0 0 1 2.8 3.78V12l1.2 1.5Z"
                  fill="currentColor"
                />
              </svg>
            </span>
          </div>
          <h2>{{ card.title }}</h2>
        </div>
      </div>
      <p :class="['price', 'price-inline', priceTone]">
        <span class="price-inline-integer">{{ collapsedPriceParts.integer }}</span>
        <span class="price-inline-decimal">{{ collapsedPriceParts.decimal }}</span>
      </p>
      <div ref="collapsedControlsRef" class="card-collapsed-controls">
        <span :class="['badge', 'badge-collapsed', priceTone]">{{ card.code }}</span>
        <div ref="actionMenuRef" class="card-action-menu card-action-menu-collapsed">
          <button class="action-btn" type="button" aria-label="Open actions menu" @click.stop="toggleActionMenu">...</button>
          <div
            v-if="actionMenuOpen"
            class="action-menu-list"
          >
            <button
              class="action-menu-item"
              type="button"
              @click.stop="openAlarmDrawer"
            >
              Set alarm
            </button>
            <button
              class="action-menu-item action-menu-item-delete"
              type="button"
              @click.stop="handleDeleteTicker"
            >
              Delete ticker
            </button>
          </div>
        </div>
        <button class="collapse-btn collapse-btn-collapsed" type="button" @click="toggleExpanded">▾</button>
      </div>
    </div>

    <div v-if="isExpanded">
      <div class="sparkline-shell">
        <div class="sparkline-head">
          <div class="chart-toolbar">
            <div class="chart-range-switch">
              <button
                :class="['chart-range-btn', { 'chart-range-btn-active': selectedRange === '1d' }]"
                type="button"
                @click="setRange('1d')"
              >
                1D
              </button>
              <button
                :class="['chart-range-btn', { 'chart-range-btn-active': selectedRange === '1y' }]"
                type="button"
                @click="setRange('1y')"
              >
                1Y
              </button>
            </div>

            <div
              v-if="selectedRange === '1y'"
              class="ma-menu"
              @mouseenter="openMaMenu"
              @mouseleave="closeMaMenu"
            >
              <button class="chart-range-btn ma-trigger" type="button">MA</button>
              <div v-if="maMenuOpen" class="ma-menu-list">
                <button
                  v-for="option in movingAverageOptions"
                  :key="option.key"
                  :class="['ma-menu-item', { 'ma-menu-item-active': option.active }]"
                  type="button"
                  @click="toggleMovingAverage(option.key)"
                >
                  <span>{{ option.label }}</span>
                  <span v-if="option.active" class="ma-menu-check" aria-hidden="true">✓</span>
                </button>
              </div>
            </div>
          </div>
          <div v-if="selectedRange === '1y' && movingAverageReadings.length" class="ma-readings">
            <span
              v-for="reading in movingAverageReadings"
              :key="reading.key"
              class="ma-reading"
              :style="{ '--ma-color': reading.color }"
            >
              <span class="ma-reading-label">{{ reading.label }}</span>
              <strong>{{ formatPrice(reading.value) }}</strong>
            </span>
          </div>
        </div>
        <div class="sparkline-frame">
          <div
            v-if="chartPlotPoints.length > 0"
            ref="chartCanvasRef"
            class="sparkline-chart"
            aria-hidden="true"
          ></div>
          <div v-if="card.data?.price != null" class="price-level price-level-current price-level-right-outer price-level-middle">
            C {{ formatPrice(card.data?.price) }}
          </div>
          <div v-if="intradayHigh !== null" class="price-level price-level-high price-level-right-outer price-level-top">
            H {{ formatPrice(intradayHigh) }}
          </div>
          <div v-if="intradayLow !== null" class="price-level price-level-low price-level-right-outer price-level-bottom">
            L {{ formatPrice(intradayLow) }}
          </div>
          <p v-if="activeHistoryState.loading" class="sparkline-empty">Loading 1Y history.</p>
          <p v-else-if="activeHistoryState.error" class="sparkline-empty">{{ activeHistoryState.error }}</p>
          <p v-else-if="chartPlotPoints.length === 0" class="sparkline-empty">Waiting for price history.</p>
        </div>
      </div>

      <div class="metrics-inline">
        <span><span class="metrics-label">5m</span> <strong>{{ formatDelta(card.data?.five_min_change) }}</strong></span>
        <span><span class="metrics-label">5m %</span> <strong>{{ formatPercent(card.data?.five_min_change_percent) }}</strong></span>
        <span><span class="metrics-label">Prev Close</span> <strong>{{ formatPrice(card.data?.previous_close) }}</strong></span>
        <span><span class="metrics-label">State</span> <strong :class="marketStateTone">{{ card.data?.market_state ?? "--" }}</strong></span>
        <span><span class="metrics-label">Source</span> <strong>{{ card.data?.source ?? "--" }}</strong></span>
      </div>

      <p v-if="card.data?.metadata?.fallback_symbol_used" class="provider-note">
        Requested {{ card.data.metadata.requested_symbol }}, using fallback
        {{ card.data.metadata.fallback_symbol_used }} for this provider.
      </p>
    </div>
  </article>
</template>
