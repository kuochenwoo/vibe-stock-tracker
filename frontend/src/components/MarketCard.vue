<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, onUpdated, ref, watch } from "vue";

const CHART_HEIGHT = 44;
const TOP_RIM_Y = 0.5;
const BOTTOM_RIM_Y = CHART_HEIGHT - 0.5;

const props = defineProps({
  card: {
    type: Object,
    required: true,
  },
});
const emit = defineEmits(["open-alarm"]);

const expanded = ref(false);
const actionMenuOpen = ref(false);
const actionMenuRef = ref(null);
const collapsedControlsRef = ref(null);

function toggleExpanded() {
  expanded.value = !expanded.value;
  if (!expanded.value) {
    actionMenuOpen.value = false;
  }
}

function openAlarmDrawer() {
  expanded.value = true;
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

function handleOutsideClick(event) {
  if (!actionMenuOpen.value) return;
  if (actionMenuRef.value?.contains(event.target)) return;
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

const sparklinePoints = computed(() => {
  const values = chartValues.value;
  if (values.length < 2) return "";

  const width = 100;
  const height = CHART_HEIGHT;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  return values
    .map((value, index) => {
      const x = (index / (values.length - 1)) * width;
      const y = height - ((value - min) / range) * height;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
});

const sparklineAreaPoints = computed(() => {
  const points = sparklinePoints.value;
  if (!points) return "";

  return `0,${CHART_HEIGHT} ${points} 100,${CHART_HEIGHT}`;
});

const chartValues = computed(() => {
  const history = props.card.history ?? [];
  const current = props.card.data?.price;
  const values = [...history];

  if (typeof current === "number" && values.at(-1) !== current) {
    values.push(current);
  }

  return values;
});

const referenceLineY = computed(() => {
  return valueToY(props.card.data?.previous_close);
});

const collapsedPriceTone = computed(() => {
  const price = props.card.data?.price;
  const previousClose = props.card.data?.previous_close;

  if (typeof price !== "number" || typeof previousClose !== "number") {
    return "";
  }

  if (price > previousClose) return "price-up";
  if (price < previousClose) return "price-down";
  return "price-flat";
});

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

const currentLineY = computed(() => CHART_HEIGHT / 2);
const highLineY = computed(() => (intradayHigh.value === null ? null : TOP_RIM_Y));
const lowLineY = computed(() => (intradayLow.value === null ? null : BOTTOM_RIM_Y));
function valueToY(value) {
  const values = chartValues.value;

  if (values.length < 2 || typeof value !== "number") return null;

  const min = Math.min(...values, value);
  const max = Math.max(...values, value);
  const range = max - min || 1;

  return CHART_HEIGHT - ((value - min) / range) * CHART_HEIGHT;
}

onMounted(() => {
  document.addEventListener("click", handleOutsideClick);
  nextTick(syncCollapsedControlsWidth);
});

onBeforeUnmount(() => {
  document.removeEventListener("click", handleOutsideClick);
  nextTick(syncCollapsedControlsWidth);
});

onUpdated(() => {
  nextTick(syncCollapsedControlsWidth);
});

watch(expanded, () => {
  nextTick(syncCollapsedControlsWidth);
});

</script>

<template>
  <article class="market-card">
    <div v-if="expanded">
      <div class="card-head">
        <div>
          <p class="label">{{ card.subtitle }}</p>
          <h2>{{ card.title }}</h2>
        </div>
        <div class="card-head-actions">
          <span class="badge">{{ card.code }}</span>
          <div ref="actionMenuRef" class="card-action-menu">
            <button class="action-btn" type="button" aria-label="Open actions menu" @click.stop="actionMenuOpen = !actionMenuOpen">...</button>
            <button
              v-if="actionMenuOpen"
              class="action-menu-item"
              type="button"
              @click.stop="openAlarmDrawer"
            >
              Set alarm
            </button>
          </div>
          <button class="collapse-btn" type="button" @click="toggleExpanded">−</button>
        </div>
      </div>

      <p class="price">{{ formatPrice(card.data?.price) }}</p>
    </div>

    <div v-else class="card-head card-head-collapsed">
      <div class="card-collapsed-copy">
        <div>
          <p class="label">{{ card.subtitle }}</p>
          <h2>{{ card.title }}</h2>
        </div>
      </div>
      <p :class="['price', 'price-inline', collapsedPriceTone]">
        <span class="price-inline-integer">{{ collapsedPriceParts.integer }}</span>
        <span class="price-inline-decimal">{{ collapsedPriceParts.decimal }}</span>
      </p>
      <div ref="collapsedControlsRef" class="card-collapsed-controls">
        <span class="badge badge-collapsed">{{ card.code }}</span>
        <div ref="actionMenuRef" class="card-action-menu card-action-menu-collapsed">
          <button class="action-btn" type="button" aria-label="Open actions menu" @click.stop="actionMenuOpen = !actionMenuOpen">...</button>
          <button
            v-if="actionMenuOpen"
            class="action-menu-item"
            type="button"
            @click.stop="openAlarmDrawer"
          >
            Set alarm
          </button>
        </div>
        <button class="collapse-btn collapse-btn-collapsed" type="button" @click="toggleExpanded">▾</button>
      </div>
    </div>

    <div v-if="expanded">
      <div class="sparkline-shell">
        <div class="sparkline-head">
          <span class="label">Price Line</span>
          <strong>1D</strong>
        </div>
        <div class="sparkline-frame">
          <svg
            v-if="sparklinePoints"
            class="sparkline-chart"
            viewBox="0 0 100 44"
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            <defs>
              <linearGradient id="price-area-fill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="rgba(62, 166, 255, 0.16)" />
                <stop offset="100%" stop-color="rgba(62, 166, 255, 0)" />
              </linearGradient>
            </defs>
            <rect
              v-if="currentLineY !== null && lowLineY !== null"
              class="sparkline-band"
              x="0"
              width="100"
              :y="currentLineY"
              :height="Math.max(lowLineY - currentLineY, 0)"
            />
            <line
              v-if="referenceLineY !== null"
              class="sparkline-reference"
              x1="0"
              x2="100"
              :y1="referenceLineY"
              :y2="referenceLineY"
            />
            <line
              v-if="currentLineY !== null"
              class="sparkline-current-guide"
              x1="0"
              x2="100"
              :y1="currentLineY"
              :y2="currentLineY"
            />
            <line
              v-if="highLineY !== null"
              class="sparkline-guide"
              x1="0"
              x2="100"
              :y1="highLineY"
              :y2="highLineY"
            />
            <line
              v-if="lowLineY !== null"
              class="sparkline-guide"
              x1="0"
              x2="100"
              :y1="lowLineY"
              :y2="lowLineY"
            />
            <polygon class="sparkline-area" :points="sparklineAreaPoints" />
            <polyline class="sparkline-stroke" :points="sparklinePoints" />
          </svg>
          <div v-if="card.data?.price != null" class="price-level price-level-current price-level-right-outer price-level-middle">
            C {{ formatPrice(card.data?.price) }}
          </div>
          <div v-if="highLineY !== null" class="price-level price-level-high price-level-right-outer price-level-top">
            H {{ formatPrice(intradayHigh) }}
          </div>
          <div v-if="lowLineY !== null" class="price-level price-level-low price-level-right-outer price-level-bottom">
            L {{ formatPrice(intradayLow) }}
          </div>
          <p v-else class="sparkline-empty">Waiting for enough price updates to draw the line.</p>
        </div>
      </div>

      <div class="metrics">
        <div>
          <span>Change</span>
          <strong>{{ formatDelta(card.data?.change) }}</strong>
        </div>
        <div>
          <span>Change %</span>
          <strong>{{ formatPercent(card.data?.change_percent) }}</strong>
        </div>
        <div>
          <span>State</span>
          <strong>{{ card.data?.market_state ?? "--" }}</strong>
        </div>
        <div>
          <span>Symbol</span>
          <strong>{{ card.data?.symbol ?? "--" }}</strong>
        </div>
        <div>
          <span>Source</span>
          <strong>{{ card.data?.source ?? "--" }}</strong>
        </div>
      </div>

      <p v-if="card.data?.metadata?.fallback_symbol_used" class="provider-note">
        Requested {{ card.data.metadata.requested_symbol }}, using fallback
        {{ card.data.metadata.fallback_symbol_used }} for this provider.
      </p>
    </div>
  </article>
</template>
