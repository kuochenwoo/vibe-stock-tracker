<script setup>
import AlertRuleForm from "./components/AlertRuleForm.vue";
import AlertRuleList from "./components/AlertRuleList.vue";
import ErrorPanel from "./components/ErrorPanel.vue";
import MarketCard from "./components/MarketCard.vue";
import StatusPanel from "./components/StatusPanel.vue";
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
  notificationPermission,
  addAlert,
  removeAlert,
  requestNotificationPermission,
} = useAlerts(snapshot, trackedTickers);
</script>

<template>
  <div class="page">
    <header class="hero">
      <div class="hero-copy">
        <p class="eyebrow">Realtime Dashboard</p>
        <h1>Track CL futures and GC=F with browser alerts.</h1>
        <p class="lede">
          The backend polls market quotes and pushes updates over a websocket.
          The frontend stores your alarm rules locally and triggers notifications
          when price crosses your threshold.
        </p>
      </div>

      <StatusPanel
        :connection-state="connectionState"
        :updated-at="snapshot.updated_at"
        :notification-permission="notificationPermission"
        @enable-notifications="requestNotificationPermission"
      />
    </header>

    <main class="layout">
      <section class="cards">
        <MarketCard v-for="card in cards" :key="card.code" :card="card" />
      </section>

      <TickerManager
        :tickers="trackedTickers"
        :on-add="createTicker"
        :on-remove="deleteTicker"
      />

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

      <ErrorPanel :errors="snapshot.errors ?? []" />
    </main>
  </div>
</template>
