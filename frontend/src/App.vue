<script setup>
import { computed, ref } from "vue";
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
const alarmDrawerTicker = ref(null);

const drawerAlerts = computed(() =>
  alarmDrawerTicker.value
    ? activeAlerts.value.filter((rule) => rule.market === alarmDrawerTicker.value.code)
    : [],
);

function formatTime(value) {
  if (!value) return "--";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(new Date(value));
}
</script>

<template>
  <div class="page">
    <aside class="settings-nav">
      <button class="settings-trigger" type="button">Settings</button>
      <div class="settings-menu">
        <button class="settings-menu-item" type="button" @click="showTickerSettings = true">
          Tracked Tickers
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
          <section class="cards">
            <MarketCard
              v-for="card in cards"
              :key="card.code"
              :card="card"
              @open-alarm="alarmDrawerTicker = $event"
            />
          </section>

          <section class="sidebar">
            <FearGreedGauge
              v-if="!alarmDrawerTicker"
              :snapshot="fearGreedSnapshot"
              :loading="fearGreedLoading"
              :error="fearGreedError"
            />

            <section v-if="!alarmDrawerTicker" class="news-panel">
              <div class="panel-head">
                <div>
                  <p class="label">Realtime News</p>
                  <h2>Feed placeholder</h2>
                </div>
              </div>
              <p class="news-copy">
                Reserved for live news modules. We can add Truth Social feeds here
                later without reshaping the rest of the page.
              </p>
            </section>
          </section>

          <ErrorPanel :errors="snapshot.errors ?? []" />
        </div>

        <TickerAlarmDrawer
          v-if="alarmDrawerTicker"
          :ticker="alarmDrawerTicker"
          :alerts="drawerAlerts"
          @close="alarmDrawerTicker = null"
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
          <div class="panel-head">
            <div></div>
            <button class="icon-btn" type="button" @click="showTickerSettings = false">×</button>
          </div>
          <TickerManager
            :tickers="trackedTickers"
            :on-add="createTicker"
            :on-remove="deleteTicker"
          />
        </section>
      </div>
    </Teleport>
  </div>
</template>
