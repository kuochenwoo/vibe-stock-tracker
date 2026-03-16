<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";
const WS_BASE = API_BASE.replace(/^http/, "ws");
const STORAGE_KEY = "market-alerts.rules.v1";

const marketOrder = ["CL", "XAUUSD"];
const marketMeta = {
  CL: {
    title: "Crude Oil Futures",
    subtitle: "Front month WTI",
    code: "CL",
  },
  XAUUSD: {
    title: "XAUUSD",
    subtitle: "Gold spot in USD",
    code: "XAUUSD",
  },
};

const snapshot = ref({
  updated_at: null,
  markets: {},
  errors: [],
});

const connectionState = ref("connecting");
const notificationPermission = ref(
  typeof Notification === "undefined" ? "unsupported" : Notification.permission,
);

const alertForm = reactive({
  market: "CL",
  direction: "above",
  value: "",
});

const alertRules = ref(loadRules());
const triggeredKeys = ref(new Set());
let socket;
let reconnectTimer;
let shouldReconnect = true;

const cards = computed(() =>
  marketOrder.map((code) => ({
    ...marketMeta[code],
    data: snapshot.value.markets[code] ?? null,
  })),
);

const activeAlerts = computed(() =>
  alertRules.value.map((rule) => ({
    ...rule,
    marketTitle: marketMeta[rule.market]?.title ?? rule.market,
  })),
);

watch(
  alertRules,
  (rules) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(rules));
  },
  { deep: true },
);

watch(
  snapshot,
  (value) => {
    evaluateAlerts(value.markets);
  },
  { deep: true },
);

function loadRules() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved ? JSON.parse(saved) : [];
  } catch {
    return [];
  }
}

async function requestNotificationPermission() {
  if (typeof Notification === "undefined") return;
  notificationPermission.value = await Notification.requestPermission();
}

function connect() {
  socket = new WebSocket(`${WS_BASE}/ws/markets`);

  socket.addEventListener("open", () => {
    connectionState.value = "live";
  });

  socket.addEventListener("message", (event) => {
    snapshot.value = JSON.parse(event.data);
  });

  socket.addEventListener("close", () => {
    if (!shouldReconnect) return;
    connectionState.value = "reconnecting";
    reconnectTimer = window.setTimeout(connect, 2000);
  });

  socket.addEventListener("error", () => {
    connectionState.value = "error";
    socket.close();
  });
}

function addAlert() {
  const value = Number(alertForm.value);
  if (!Number.isFinite(value)) return;

  alertRules.value.unshift({
    id: crypto.randomUUID(),
    market: alertForm.market,
    direction: alertForm.direction,
    value,
    triggered: false,
    created_at: new Date().toISOString(),
  });

  alertForm.value = "";
}

function removeAlert(id) {
  alertRules.value = alertRules.value.filter((rule) => rule.id !== id);
  triggeredKeys.value.delete(id);
}

function evaluateAlerts(markets) {
  for (const rule of alertRules.value) {
    const current = markets[rule.market]?.price;
    if (typeof current !== "number") continue;

    const hit =
      rule.direction === "above" ? current >= rule.value : current <= rule.value;

    if (!hit) {
      triggeredKeys.value.delete(rule.id);
      rule.triggered = false;
      continue;
    }

    if (triggeredKeys.value.has(rule.id)) continue;

    triggeredKeys.value.add(rule.id);
    rule.triggered = true;
    sendNotification(rule, current);
  }
}

function sendNotification(rule, price) {
  const title = `${marketMeta[rule.market]?.title ?? rule.market} alert`;
  const body = `Price is ${price.toFixed(2)} and moved ${rule.direction} ${rule.value}.`;

  if (notificationPermission.value === "granted") {
    new Notification(title, { body });
  }
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

function formatTime(value) {
  if (!value) return "--";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(new Date(value));
}

onMounted(() => {
  connect();
});

onBeforeUnmount(() => {
  shouldReconnect = false;
  if (socket) socket.close();
  if (reconnectTimer) clearTimeout(reconnectTimer);
});
</script>

<template>
  <div class="page">
    <header class="hero">
      <div class="hero-copy">
        <p class="eyebrow">Realtime Dashboard</p>
        <h1>Track CL futures and XAUUSD with browser alerts.</h1>
        <p class="lede">
          The backend polls market quotes and pushes updates over a websocket.
          The frontend stores your alarm rules locally and triggers notifications
          when price crosses your threshold.
        </p>
      </div>

      <section class="status-panel">
        <div class="status-row">
          <span>Connection</span>
          <strong :class="`status-${connectionState}`">{{ connectionState }}</strong>
        </div>
        <div class="status-row">
          <span>Last Update</span>
          <strong>{{ formatTime(snapshot.updated_at) }}</strong>
        </div>
        <div class="status-row">
          <span>Notifications</span>
          <strong>{{ notificationPermission }}</strong>
        </div>
        <button class="primary-btn" @click="requestNotificationPermission">
          Enable notifications
        </button>
      </section>
    </header>

    <main class="layout">
      <section class="cards">
        <article v-for="card in cards" :key="card.code" class="market-card">
          <div class="card-head">
            <div>
              <p class="label">{{ card.subtitle }}</p>
              <h2>{{ card.title }}</h2>
            </div>
            <span class="badge">{{ card.code }}</span>
          </div>

          <p class="price">{{ formatPrice(card.data?.price) }}</p>

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
          </div>
        </article>
      </section>

      <section class="alerts-panel">
        <div class="panel-head">
          <div>
            <p class="label">Alarm Rules</p>
            <h2>Set notification thresholds</h2>
          </div>
        </div>

        <form class="alert-form" @submit.prevent="addAlert">
          <label>
            <span>Market</span>
            <select v-model="alertForm.market">
              <option value="CL">CL</option>
              <option value="XAUUSD">XAUUSD</option>
            </select>
          </label>

          <label>
            <span>Condition</span>
            <select v-model="alertForm.direction">
              <option value="above">Above</option>
              <option value="below">Below</option>
            </select>
          </label>

          <label>
            <span>Alarm price</span>
            <input v-model="alertForm.value" type="number" step="0.01" placeholder="Enter value" />
          </label>

          <button class="primary-btn" type="submit">Add alert</button>
        </form>

        <div v-if="activeAlerts.length" class="alerts-list">
          <article
            v-for="rule in activeAlerts"
            :key="rule.id"
            class="alert-item"
            :class="{ triggered: rule.triggered }"
          >
            <div>
              <p class="alert-title">{{ rule.marketTitle }}</p>
              <p class="alert-copy">
                Notify when price moves {{ rule.direction }} {{ formatPrice(rule.value) }}
              </p>
            </div>
            <button class="ghost-btn" @click="removeAlert(rule.id)">Delete</button>
          </article>
        </div>
        <p v-else class="empty-state">No alerts yet.</p>
      </section>

      <section v-if="snapshot.errors?.length" class="errors-panel">
        <p class="label">Feed Errors</p>
        <ul>
          <li v-for="error in snapshot.errors" :key="error">{{ error }}</li>
        </ul>
      </section>
    </main>
  </div>
</template>
