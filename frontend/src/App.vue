<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import draggable from "vuedraggable";
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
const mockWireNewsItems = [
  {
    id: "bloomberg-fed",
    source: "Bloomberg",
    publishedAt: "2026-03-30T09:18:00+09:00",
    title: "Treasuries Edge Higher as Traders Reprice Fed Path Into Quarter-End",
    summary:
      "Rates desks are leaning defensive into month-end flows, with front-end yields slipping as traders wait for the next inflation impulse.",
    tags: ["Rates", "Fed", "Macro"],
  },
  {
    id: "bloomberg-tech",
    source: "Bloomberg",
    publishedAt: "2026-03-30T08:56:00+09:00",
    title: "Chip Complex Holds Bid With AI Spend Still Driving Index Leadership",
    summary:
      "Semiconductor names remain central to index direction, with traders watching whether leadership broadens beyond the largest AI beneficiaries.",
    tags: ["Semis", "AI", "Equities"],
  },
  {
    id: "bloomberg-oil",
    source: "Bloomberg",
    publishedAt: "2026-03-30T08:49:00+09:00",
    title: "Oil Holds Overnight Gains as Supply Risk Premium Rebuilds",
    summary:
      "Crude keeps a firmer tone after an overnight bid, with traders watching shipping and refinery headlines for follow-through.",
    tags: ["Oil", "Energy", "Supply"],
  },
  {
    id: "bloomberg-gold",
    source: "Bloomberg",
    publishedAt: "2026-03-30T08:37:00+09:00",
    title: "Gold Traders Watch Dollar Drift and Real Yields for Next Break",
    summary:
      "Bullion remains sensitive to the interplay between the dollar, front-end yields, and haven demand into the New York handoff.",
    tags: ["Gold", "USD", "Rates"],
  },
  {
    id: "bloomberg-nq",
    source: "Bloomberg",
    publishedAt: "2026-03-30T08:21:00+09:00",
    title: "Nasdaq Futures Grind Higher as Mega-Caps Continue to Lead",
    summary:
      "Index traders are still leaning on the same leadership cluster, though breadth remains narrower than headline futures strength suggests.",
    tags: ["Nasdaq", "Futures", "Mega-cap"],
  },
  {
    id: "bloomberg-es",
    source: "Bloomberg",
    publishedAt: "2026-03-30T08:08:00+09:00",
    title: "S&P Futures Stay Rangebound Ahead of US Data Calendar",
    summary:
      "Macro desks are holding a tighter range in index futures while waiting for the next round of scheduled US economic releases.",
    tags: ["S&P 500", "Macro", "Data"],
  },
  {
    id: "bloomberg-vix",
    source: "Bloomberg",
    publishedAt: "2026-03-30T07:54:00+09:00",
    title: "VIX Slips but Dealers Flag Headline Sensitivity Into Open",
    summary:
      "Volatility remains contained on the surface, though derivatives desks are still pricing event risk around the edges.",
    tags: ["VIX", "Volatility", "Derivatives"],
  },
  {
    id: "bloomberg-dollar",
    source: "Bloomberg",
    publishedAt: "2026-03-30T07:42:00+09:00",
    title: "Dollar Index Pauses After Three Sessions of Firm Buying",
    summary:
      "FX traders are reassessing whether the move was a positioning squeeze or the start of a broader macro repricing.",
    tags: ["Dollar", "FX", "Macro"],
  },
  {
    id: "bloomberg-bonds",
    source: "Bloomberg",
    publishedAt: "2026-03-30T07:29:00+09:00",
    title: "Bond Futures Edge Up as Front-End Traders Price Softer Path",
    summary:
      "Treasury futures retain a mild bid with the short end doing most of the work as inflation expectations settle.",
    tags: ["Bonds", "Treasuries", "Rates"],
  },
  {
    id: "bloomberg-copper",
    source: "Bloomberg",
    publishedAt: "2026-03-30T07:15:00+09:00",
    title: "Copper Nears Resistance as China Demand Narrative Firms Again",
    summary:
      "Industrial metals are back in focus with cyclical traders watching whether macro optimism can survive into US hours.",
    tags: ["Copper", "China", "Metals"],
  },
  {
    id: "bloomberg-bitcoin",
    source: "Bloomberg",
    publishedAt: "2026-03-30T07:03:00+09:00",
    title: "Bitcoin Range Tightens as ETF Flows Offset Leverage Fatigue",
    summary:
      "Crypto desks are balancing resilient spot demand against a cooling leveraged positioning backdrop in derivatives.",
    tags: ["Bitcoin", "Crypto", "ETF"],
  },
  {
    id: "bloomberg-yen",
    source: "Bloomberg",
    publishedAt: "2026-03-30T06:52:00+09:00",
    title: "Yen Traders Stay Alert for Policy Tone as Tokyo Session Ends",
    summary:
      "The currency remains highly sensitive to any signal around official discomfort with renewed dollar-yen pressure.",
    tags: ["JPY", "BoJ", "FX"],
  },
  {
    id: "bloomberg-credit",
    source: "Bloomberg",
    publishedAt: "2026-03-30T06:38:00+09:00",
    title: "Credit Spreads Hold Tight Even as Equity Positioning Looks Crowded",
    summary:
      "Cross-asset desks are watching for any sign that calm credit conditions stop validating the equity bid.",
    tags: ["Credit", "Spreads", "Cross-asset"],
  },
];
const mockTruthSocialItems = [
  {
    id: "truth-energy",
    source: "Truth Social",
    publishedAt: "2026-03-30T09:11:00+09:00",
    title: "Energy and dollar chatter picks up ahead of the US handoff",
    summary:
      "A fast social pulse update on crude, the dollar, and risk appetite as Asia closes and Europe settles in.",
    tags: ["Energy", "USD", "Flow"],
  },
  {
    id: "truth-vol",
    source: "Truth Social",
    publishedAt: "2026-03-30T08:42:00+09:00",
    title: "Volatility posts turn defensive as futures flatten before New York",
    summary:
      "Social commentary is leaning toward hedging and headline sensitivity rather than trend continuation into the next session.",
    tags: ["Vol", "Futures", "Sentiment"],
  },
];
const footerHeadlineItems = computed(() =>
  mockWireNewsItems.map((item) => ({ id: item.id, source: item.source, title: item.title })),
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
                :items="mockTruthSocialItems"
                :collapsed="truthSocialCollapsed"
                @update:collapsed="truthSocialCollapsed = $event"
              />

              <NewsFeedPanel
                :items="mockWireNewsItems"
                eyebrow="Realtime News"
                title="Wire"
                :collapsed="wireNewsCollapsed"
                @update:collapsed="wireNewsCollapsed = $event"
              />
            </template>

            <TruthSocialPanel
              v-else
              :items="mockTruthSocialItems"
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
          @close="handleCloseAlarmDrawer"
          @add-alert="addAlert"
          @remove-alert="removeAlert"
        />
      </div>
    </main>

    <footer class="headline-ribbon" aria-label="News headline ribbon">
      <div class="headline-ribbon-track">
        <span
          v-for="item in [...footerHeadlineItems, ...footerHeadlineItems]"
          :key="`${item.id}-${item.source}-${item.title}`"
          class="headline-ribbon-item"
        >
          <span class="headline-ribbon-source">{{ item.source }}</span>
          <span>{{ item.title }}</span>
        </span>
      </div>
    </footer>

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
