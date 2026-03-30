<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import draggable from "vuedraggable";
import AlertsManager from "./components/AlertsManager.vue";
import ErrorPanel from "./components/ErrorPanel.vue";
import FearGreedGauge from "./components/FearGreedGauge.vue";
import MacroPanel from "./components/MacroPanel.vue";
import MarketCard from "./components/MarketCard.vue";
import NotificationPopup from "./components/NotificationPopup.vue";
import TickerAlarmDrawer from "./components/TickerAlarmDrawer.vue";
import TickerManager from "./components/TickerManager.vue";
import { useAlerts } from "./composables/useAlerts";
import { useMarketStream } from "./composables/useMarketStream";
import { useSentiment } from "./composables/useSentiment";

const {
  cards,
  connectionState,
  createTicker,
  deleteTicker,
  setTickerOrder,
  snapshot,
  trackedTickers,
} = useMarketStream();
const {
  error: fearGreedError,
  loading: fearGreedLoading,
  snapshot: fearGreedSnapshot,
} = useSentiment();
const {
  activeAlerts,
  addAlert,
  dismissPopup,
  popupNotice,
  removeAlert,
} = useAlerts(snapshot, trackedTickers);
const showTickerSettings = ref(false);
const showAlarmSettings = ref(false);
const alarmDrawerTicker = ref(null);
const displayCards = ref([]);
const localClock = ref(new Date());
const layoutVersion = ref(0);
const fearGreedCollapsed = ref(false);
const showTopRightClock = ref(true);

let localClockTimer;

function handleWindowScroll() {
  showTopRightClock.value = window.scrollY < 48;
}

const drawerAlerts = computed(() =>
  alarmDrawerTicker.value
    ? activeAlerts.value.filter((rule) => rule.market === alarmDrawerTicker.value.code)
    : [],
);
const marketsWithAlerts = computed(
  () => new Set(activeAlerts.value.map((rule) => rule.market)),
);
const alertSummaryByMarket = computed(() => {
  const summary = new Map();

  for (const rule of activeAlerts.value) {
    const current = summary.get(rule.market) ?? { count: 0, alerts: [] };
    current.count += 1;
    current.alerts.push(rule);
    summary.set(rule.market, current);
  }

  return summary;
});
const macroItems = computed(() =>
  (snapshot.value.macro_tickers ?? [])
    .map((ticker) => {
      const quote = snapshot.value.markets?.[ticker.code];
      return {
        code: ticker.code,
        symbol: ticker.symbol,
        name: ticker.name,
        price: quote?.price ?? null,
        change_percent: quote?.change_percent ?? null,
      };
    })
    .filter((item) => item.price != null || item.change_percent != null),
);

const daypart = computed(() => {
  const hour = localClock.value.getHours();

  if (hour >= 5 && hour < 7) {
    return { icon: "◔", label: "Dawn" };
  }
  if (hour >= 7 && hour < 17) {
    return { icon: "☀", label: "Daytime" };
  }
  if (hour >= 17 && hour < 19) {
    return { icon: "◕", label: "Dusk" };
  }
  return { icon: "☾", label: "Nighttime" };
});

const jstDateTime = computed(() =>
  new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Tokyo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(localClock.value),
);

function getNewYorkDateParts(date) {
  const formatter = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
    weekday: "short",
  });

  const parts = Object.fromEntries(
    formatter
      .formatToParts(date)
      .filter((part) => part.type !== "literal")
      .map((part) => [part.type, part.value]),
  );

  return {
    year: Number(parts.year),
    month: Number(parts.month),
    day: Number(parts.day),
    hour: Number(parts.hour),
    minute: Number(parts.minute),
    second: Number(parts.second),
    weekday: parts.weekday,
  };
}

function getOffsetMinutes(timeZone, date) {
  const utcDate = new Date(date.toLocaleString("en-US", { timeZone: "UTC" }));
  const zonedDate = new Date(date.toLocaleString("en-US", { timeZone }));
  return Math.round((zonedDate.getTime() - utcDate.getTime()) / 60000);
}

function zonedTimeToUtc(timeZone, year, month, day, hour, minute = 0, second = 0) {
  const utcGuess = Date.UTC(year, month - 1, day, hour, minute, second);
  const offsetMinutes = getOffsetMinutes(timeZone, new Date(utcGuess));
  return new Date(utcGuess - offsetMinutes * 60 * 1000);
}

const usMarketOpenCountdown = computed(() => {
  const now = localClock.value;
  const ny = getNewYorkDateParts(now);
  const weekdayMap = {
    Sun: 0,
    Mon: 1,
    Tue: 2,
    Wed: 3,
    Thu: 4,
    Fri: 5,
    Sat: 6,
  };
  const currentWeekday = weekdayMap[ny.weekday] ?? 0;
  const marketOpenToday = zonedTimeToUtc(
    "America/New_York",
    ny.year,
    ny.month,
    ny.day,
    9,
    30,
    0,
  );
  const marketCloseToday = zonedTimeToUtc(
    "America/New_York",
    ny.year,
    ny.month,
    ny.day,
    16,
    0,
    0,
  );

  let targetOpen = marketOpenToday;

  if (currentWeekday === 0) {
    targetOpen = zonedTimeToUtc("America/New_York", ny.year, ny.month, ny.day + 1, 9, 30, 0);
  } else if (currentWeekday === 6) {
    targetOpen = zonedTimeToUtc("America/New_York", ny.year, ny.month, ny.day + 2, 9, 30, 0);
  } else if (now >= marketOpenToday && now < marketCloseToday) {
    return "US stock market open now";
  } else if (now >= marketCloseToday) {
    const daysUntilNextOpen = currentWeekday === 5 ? 3 : 1;
    targetOpen = zonedTimeToUtc(
      "America/New_York",
      ny.year,
      ny.month,
      ny.day + daysUntilNextOpen,
      9,
      30,
      0,
    );
  }

  const diffMs = Math.max(targetOpen.getTime() - now.getTime(), 0);
  const totalSeconds = Math.floor(diffMs / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  return `US open in ${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
});

function formatTime(value) {
  if (!value) return "--";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(new Date(value));
}

function handleDragEnd() {
  setTickerOrder(displayCards.value.map((card) => card.code));
}

function handleCloseAlarmDrawer() {
  alarmDrawerTicker.value = null;
  layoutVersion.value += 1;
}

watch(
  cards,
  (nextCards) => {
    displayCards.value = nextCards.map((card) => ({ ...card }));
  },
  { immediate: true },
);

onMounted(() => {
  localClockTimer = window.setInterval(() => {
    localClock.value = new Date();
  }, 1000);
  handleWindowScroll();
  window.addEventListener("scroll", handleWindowScroll, { passive: true });
});

onBeforeUnmount(() => {
  if (localClockTimer) {
    window.clearInterval(localClockTimer);
  }
  window.removeEventListener("scroll", handleWindowScroll);
});
</script>

<template>
  <div class="page">
    <div
      class="localtime-indicator"
      :class="{ 'localtime-indicator-hidden': !showTopRightClock }"
      :title="`Local time: ${daypart.label} | JST ${jstDateTime}`"
      aria-label="Local time daypart"
    >
      <div class="localtime-meta">
        <span class="jst-datetime">JST {{ jstDateTime }}</span>
        <div class="market-open-countdown">{{ usMarketOpenCountdown }}</div>
      </div>
      <span class="localtime-icon" :class="`localtime-${daypart.label.toLowerCase()}`">{{ daypart.icon }}</span>
    </div>

    <aside class="settings-nav">
      <button class="settings-trigger" type="button">Settings</button>
      <div class="settings-menu">
        <button class="settings-menu-item" type="button" @click="showTickerSettings = true">
          Tracked Tickers
        </button>
        <button class="settings-menu-item" type="button" @click="showAlarmSettings = true">
          All Alarms
        </button>
      </div>
    </aside>

    <header class="page-header">
      <div class="header-status">
        <div class="header-item">
          <span>Connection</span>
          <strong :class="`status-${connectionState}`">{{ connectionState }}</strong>
        </div>
        <div class="header-item">
          <span>Last Update</span>
          <strong>{{ formatTime(snapshot.updated_at) }}</strong>
        </div>
      </div>
    </header>

    <main class="layout">
      <div class="workspace" :class="{ 'workspace-drawer-open': !!alarmDrawerTicker }">
        <div class="workspace-main">
          <draggable
            v-model="displayCards"
            item-key="code"
            class="cards"
            ghost-class="market-card-ghost"
            chosen-class="market-card-chosen"
            drag-class="market-card-dragging"
            filter=".action-btn, .collapse-btn, .action-menu-item"
            :prevent-on-filter="false"
            :animation="220"
            @end="handleDragEnd"
          >
            <template #item="{ element }">
              <MarketCard
                :card="element"
                :has-active-alarm="marketsWithAlerts.has(element.code)"
                :alert-summary="alertSummaryByMarket.get(element.code) ?? { count: 0, alerts: [] }"
                :layout-version="layoutVersion"
                @open-alarm="alarmDrawerTicker = $event"
              />
            </template>
          </draggable>

          <section v-if="!alarmDrawerTicker" class="sidebar">
            <MacroPanel v-if="macroItems.length" :items="macroItems" />

            <FearGreedGauge
              :snapshot="fearGreedSnapshot"
              :loading="fearGreedLoading"
              :error="fearGreedError"
              :collapsed="fearGreedCollapsed"
              @update:collapsed="fearGreedCollapsed = $event"
            />

            <section class="news-panel">
              <div class="panel-head">
                <div>
                  <p class="label">Realtime News</p>
                  <h2>Signal deck</h2>
                </div>
              </div>
              <div class="news-placeholder">
                <p class="news-copy">
                  Reserved for live news modules. This area is ready for market-moving
                  headlines, sentiment updates, and Truth Social feeds later.
                </p>
                <div class="news-placeholder-list">
                  <span>Breaking market headlines</span>
                  <span>Macro event watch</span>
                  <span>Social signal stream</span>
                </div>
              </div>
            </section>
          </section>

          <ErrorPanel :errors="snapshot.errors ?? []" />
        </div>

        <TickerAlarmDrawer
          v-if="alarmDrawerTicker"
          :ticker="alarmDrawerTicker"
          :alerts="drawerAlerts"
          @close="handleCloseAlarmDrawer"
          @add-alert="addAlert"
          @remove-alert="removeAlert"
        />
      </div>
    </main>

    <NotificationPopup :notice="popupNotice" @dismiss="dismissPopup" />

    <Teleport to="body">
      <div
        v-if="showTickerSettings"
        class="settings-modal-backdrop"
        @click.self="showTickerSettings = false"
      >
        <section class="settings-modal" role="dialog" aria-modal="true">
          <button class="icon-btn settings-modal-close" type="button" @click="showTickerSettings = false">×</button>
          <TickerManager
            :tickers="trackedTickers"
            :on-add="createTicker"
            :on-remove="deleteTicker"
          />
        </section>
      </div>
    </Teleport>

    <Teleport to="body">
      <div
        v-if="showAlarmSettings"
        class="settings-modal-backdrop"
        @click.self="showAlarmSettings = false"
      >
        <section class="settings-modal" role="dialog" aria-modal="true">
          <button class="icon-btn settings-modal-close" type="button" @click="showAlarmSettings = false">×</button>
          <AlertsManager
            :alerts="activeAlerts"
            @remove="removeAlert"
          />
        </section>
      </div>
    </Teleport>
  </div>
</template>
