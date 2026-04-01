<script setup>
import { computed, reactive, watch } from "vue";
import AlertRuleList from "./AlertRuleList.vue";
import AlertHistoryList from "./AlertHistoryList.vue";

const props = defineProps({
  ticker: {
    type: Object,
    required: true,
  },
  alerts: {
    type: Array,
    required: true,
  },
  history: {
    type: Array,
    required: true,
  },
});

const emit = defineEmits(["close", "add-alert", "remove-alert"]);

const form = reactive({
  direction: "above",
  value: "",
});

const activeAlarmCount = computed(() => props.alerts.length);
const tickerHistory = computed(() =>
  props.history.filter((item) => item.market === props.ticker.code)
);

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

watch(
  () => props.ticker?.code,
  () => {
    form.direction = "above";
    form.value = "";
  },
  { immediate: true },
);

function submit() {
  emit("add-alert", {
    market: props.ticker.code,
    direction: form.direction,
    value: form.value,
  });
  form.value = "";
}
</script>

<template>
  <aside class="alarm-drawer">
    <div class="panel-head">
      <div>
        <p class="label">{{ ticker.symbol }}</p>
        <h2>{{ ticker.name }}</h2>
      </div>
      <button class="icon-btn" type="button" @click="emit('close')">×</button>
    </div>

    <div class="alarm-drawer-hero">
      <div>
        <span class="alarm-drawer-kicker">Current Price</span>
        <strong>{{ formatPrice(ticker.price) }}</strong>
      </div>
      <div>
        <span class="alarm-drawer-kicker">Session Move</span>
        <strong>{{ formatDelta(ticker.change) }}</strong>
      </div>
      <div>
        <span class="alarm-drawer-kicker">Active Alarms</span>
        <strong>{{ activeAlarmCount }}</strong>
      </div>
    </div>

    <form class="alert-form" @submit.prevent="submit">
      <label>
        <span>Condition</span>
        <select v-model="form.direction">
          <option value="above">Above</option>
          <option value="below">Below</option>
        </select>
      </label>

      <label>
        <span>Alarm price</span>
        <input v-model="form.value" type="number" step="0.01" placeholder="Enter value" />
      </label>

      <button class="primary-btn" type="submit">Add alert</button>
    </form>

    <AlertRuleList :alerts="alerts" @remove="emit('remove-alert', $event)" />

    <section v-if="tickerHistory.length" class="ticker-manager" style="margin-top: 24px; border-top: 1px solid rgba(88, 98, 116, 0.08); padding-top: 24px;">
      <p class="ticker-manager-title">TRIGGER HISTORY</p>
      <AlertHistoryList
          :history="tickerHistory"
          :tracked-tickers="[ticker]"
      />
    </section>
  </aside>
</template>
