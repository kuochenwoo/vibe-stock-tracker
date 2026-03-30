<script setup>
import AlertRuleForm from "./components/AlertRuleForm.vue";
import AlertRuleList from "./components/AlertRuleList.vue";
import ErrorPanel from "./components/ErrorPanel.vue";
import MarketCard from "./components/MarketCard.vue";
import NotificationPopup from "./components/NotificationPopup.vue";
import TickerManager from "./components/TickerManager.vue";
import { useAlerts } from "./composables/useAlerts";
import { useMarketStream } from "./composables/useMarketStream";

const {
  cards,
  connectionState,
  createTicker,
  deleteTicker,
  snapshot,
  trackedTickers,
} = useMarketStream();
const {
  activeAlerts,
  alertForm,
  addAlert,
  dismissPopup,
  popupNotice,
  removeAlert,
} = useAlerts(snapshot, trackedTickers);

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
      <section class="cards">
        <MarketCard v-for="card in cards" :key="card.code" :card="card" />
      </section>

      <section class="sidebar">
        <TickerManager
          :tickers="trackedTickers"
          :on-add="createTicker"
          :on-remove="deleteTicker"
        />

        <section class="news-panel">
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

        <section class="alerts-panel">
          <div class="panel-head">
            <div>
              <p class="label">Alarm Rules</p>
              <h2>Set notification thresholds</h2>
            </div>
          </div>

          <AlertRuleForm :alert-form="alertForm" :tickers="trackedTickers" @submit="addAlert" />
          <AlertRuleList :alerts="activeAlerts" @remove="removeAlert" />
        </section>
      </section>

      <ErrorPanel :errors="snapshot.errors ?? []" />
    </main>

    <NotificationPopup :notice="popupNotice" @dismiss="dismissPopup" />
  </div>
</template>
