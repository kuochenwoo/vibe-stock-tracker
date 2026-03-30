<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import draggable from "vuedraggable";
import AlertsManager from "./components/AlertsManager.vue";
import ErrorPanel from "./components/ErrorPanel.vue";
import FearGreedGauge from "./components/FearGreedGauge.vue";
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

let localClockTimer;

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
  }, 60 * 1000);
});

onBeforeUnmount(() => {
  if (localClockTimer) {
    window.clearInterval(localClockTimer);
  }
});
</script>

<template>
  <div class="page">
    <div class="localtime-indicator" :title="`Local time: ${daypart.label}`" aria-label="Local time daypart">
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
