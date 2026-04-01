<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import draggable from "vuedraggable";
import AlertHistoryList from "./components/AlertHistoryList.vue";
import AlertsManager from "./components/AlertsManager.vue";
import ErrorPanel from "./components/ErrorPanel.vue";
import FearGreedGauge from "./components/FearGreedGauge.vue";
import MacroPanel from "./components/MacroPanel.vue";
import MarketCard from "./components/MarketCard.vue";
import NewsFeedPanel from "./components/NewsFeedPanel.vue";
import NotificationPopup from "./components/NotificationPopup.vue";
import TickerAlarmDrawer from "./components/TickerAlarmDrawer.vue";
import TickerManager from "./components/TickerManager.vue";
import TruthSocialPanel from "./components/TruthSocialPanel.vue";
import { useAlerts } from "./composables/useAlerts";
import { useMarketStream } from "./composables/useMarketStream";
import { useSentiment } from "./composables/useSentiment";
import { useTruthSocial } from "./composables/useTruthSocial";
import { useWireNews } from "./composables/useWireNews";

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
  error: truthSocialError,
  loading: truthSocialLoading,
  items: truthSocialItems,
  popupNotice: truthSocialPopupNotice,
  dismissPopup: dismissTruthSocialPopup,
} = useTruthSocial();
const {
  error: wireNewsError,
  loading: wireNewsLoading,
  items: wireNewsItems,
} = useWireNews();
const {
  activeAlerts,
  alertHistory,
  hasUnreadHistory,
  addAlert,
  dismissPopup,
  markHistoryRead,
  popupNotice,
  removeAlert,
} = useAlerts(snapshot, trackedTickers);
const showTickerSettings = ref(false);
const showAlarmSettings = ref(false);
const showAlarmHistory = ref(false);

function handleOpenHistory() {
  showAlarmHistory.value = true;
  markHistoryRead();
}
const alarmDrawerTicker = ref(null);
const displayCards = ref([]);
const localClock = ref(new Date());
const layoutVersion = ref(0);
const fearGreedCollapsed = ref(true);
const macroCollapsed = ref(false);
const wireNewsCollapsed = ref(false);
const truthSocialCollapsed = ref(false);
const showTopRightClock = ref(true);
const removingTickerCodes = ref([]);
const expandedTickerCode = ref(null);

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
        change: quote?.change ?? null,
        change_percent: quote?.change_percent ?? null,
        previous_close: quote?.previous_close ?? null,
      };
    })
    .filter((item) => item.price != null || item.change_percent != null),
);
const footerHeadlineItems = computed(() =>
  wireNewsItems.value.map((item) => ({
    id: item.id,
    source: item.source,
    title: item.title,
    url: item.url ?? null,
  })),
);
const activePopupNotice = computed(() => truthSocialPopupNotice.value ?? popupNotice.value);

function dismissActivePopup() {
  if (truthSocialPopupNotice.value) {
    dismissTruthSocialPopup();
    return;
  }
  dismissPopup();
}

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

async function handleCloseAlarmDrawer() {
  alarmDrawerTicker.value = null;
  expandedTickerCode.value = null;
  await nextTick();
  layoutVersion.value += 1;
  window.requestAnimationFrame(() => {
    window.dispatchEvent(new Event("resize"));
  });
}

function handleExpandedChange(payload) {
  expandedTickerCode.value = payload.expanded ? payload.code : null;
}

function handleOpenAlarm(ticker) {
  expandedTickerCode.value = ticker.code;
  alarmDrawerTicker.value = ticker;
}

async function handleDeleteTicker(code) {
  const previousCards = [...displayCards.value];
  removingTickerCodes.value = [...new Set([...removingTickerCodes.value, code])];
  if (alarmDrawerTicker.value?.code === code) {
    handleCloseAlarmDrawer();
  }
  if (expandedTickerCode.value === code) {
    expandedTickerCode.value = null;
  }
  try {
    await nextTick();
    displayCards.value = displayCards.value.filter((card) => card.code !== code);
    await deleteTicker(code);
  } catch (error) {
    displayCards.value = previousCards;
    removingTickerCodes.value = removingTickerCodes.value.filter((item) => item !== code);
    throw error;
  }
  removingTickerCodes.value = removingTickerCodes.value.filter((item) => item !== code);
}

watch(
  cards,
  (nextCards) => {
    displayCards.value = nextCards
      .filter((card) => !removingTickerCodes.value.includes(card.code))
      .map((card) => ({ ...card }));
    if (expandedTickerCode.value && !nextCards.some((card) => card.code === expandedTickerCode.value)) {
      expandedTickerCode.value = null;
    }
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
        <button
          class="header-item header-btn history-bell-btn"
          :class="{ 'has-unread': hasUnreadHistory }"
          type="button"
          title="Alarm History"
          @click="handleOpenHistory"
        >
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
            <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
          </svg>
          <span v-if="hasUnreadHistory" class="unread-dot"></span>
        </button>
      </div>
    </header>

    <main class="layout">
      <div class="workspace" :class="{ 'workspace-drawer-open': !!alarmDrawerTicker }">
        <div class="workspace-main">
          <div class="main-column">
            <MacroPanel
              v-if="macroItems.length"
              :items="macroItems"
              :collapsed="macroCollapsed"
              @update:collapsed="macroCollapsed = $event"
            />

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
                  :is-expanded="expandedTickerCode === element.code"
                  :on-delete="handleDeleteTicker"
                  :is-deleting="removingTickerCodes.includes(element.code)"
                  :has-active-alarm="marketsWithAlerts.has(element.code)"
                  :alert-summary="alertSummaryByMarket.get(element.code) ?? { count: 0, alerts: [] }"
                  :layout-version="layoutVersion"
                  @expanded-change="handleExpandedChange"
                  @open-alarm="handleOpenAlarm"
                />
              </template>
            </draggable>
          </div>

          <section v-if="!alarmDrawerTicker" class="sidebar">
            <template v-if="!expandedTickerCode">
              <FearGreedGauge
                :snapshot="fearGreedSnapshot"
                :loading="fearGreedLoading"
                :error="fearGreedError"
                :collapsed="fearGreedCollapsed"
                @update:collapsed="fearGreedCollapsed = $event"
              />

              <TruthSocialPanel
                :items="truthSocialItems"
                :loading="truthSocialLoading"
                :error="truthSocialError"
                :collapsed="truthSocialCollapsed"
                @update:collapsed="truthSocialCollapsed = $event"
              />

              <NewsFeedPanel
                :items="wireNewsItems"
                :loading="wireNewsLoading"
                :error="wireNewsError"
                eyebrow="Realtime News"
                title="Wire"
                :collapsed="wireNewsCollapsed"
                @update:collapsed="wireNewsCollapsed = $event"
              />
            </template>

            <TruthSocialPanel
              v-else
              :items="truthSocialItems"
              :loading="truthSocialLoading"
              :error="truthSocialError"
              :collapsed="truthSocialCollapsed"
              @update:collapsed="truthSocialCollapsed = $event"
            />
          </section>

          <ErrorPanel :errors="snapshot.errors ?? []" />
        </div>

        <TickerAlarmDrawer
          v-if="alarmDrawerTicker"
          :ticker="alarmDrawerTicker"
          :alerts="drawerAlerts"
          :history="alertHistory"
          @close="handleCloseAlarmDrawer"
          @add-alert="addAlert"
          @remove-alert="removeAlert"
        />
      </div>
    </main>

    <footer class="headline-ribbon" aria-label="News headline ribbon">
      <div class="headline-ribbon-track">
        <a
          v-for="item in [...footerHeadlineItems, ...footerHeadlineItems]"
          :key="`${item.id}-${item.source}-${item.title}`"
          class="headline-ribbon-item"
          :href="item.url || undefined"
          target="_blank"
          rel="noreferrer"
        >
          <span class="headline-ribbon-source">{{ item.source }}</span>
          <span>{{ item.title }}</span>
        </a>
      </div>
    </footer>

    <NotificationPopup
      :notice="activePopupNotice"
      @dismiss="dismissActivePopup"
    />

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
            @view-history="showAlarmSettings = false; handleOpenHistory()"
          />
        </section>
      </div>
    </Teleport>

    <Teleport to="body">
      <div
        v-if="showAlarmHistory"
        class="settings-modal-backdrop"
        @click.self="showAlarmHistory = false"
      >
        <section class="settings-modal" role="dialog" aria-modal="true">
          <button class="icon-btn settings-modal-close" type="button" @click="showAlarmHistory = false">×</button>
          <section class="ticker-manager">
            <p class="ticker-manager-title">ALARM HISTORY</p>
            <AlertHistoryList
                :history="alertHistory"
                :tracked-tickers="trackedTickers"
            />
          </section>
        </section>
      </div>
    </Teleport>
  </div>
</template>
