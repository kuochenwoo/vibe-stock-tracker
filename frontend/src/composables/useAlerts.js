import { computed, reactive, ref, watch } from "vue";

const STORAGE_KEY = "market-alerts.rules.v1";
const NOTIFICATION_TAG_PREFIX = "market-alert";

export function useAlerts(snapshot, trackedTickers) {
  const notificationPermission = ref(
    typeof Notification === "undefined" ? "unsupported" : Notification.permission,
  );

  const alertForm = reactive({
    market: "",
    direction: "above",
    value: "",
  });

  const alertRules = ref(loadRules());
  const triggeredKeys = ref(new Set());

  const activeAlerts = computed(() =>
    alertRules.value.map((rule) => ({
      ...rule,
      marketTitle:
        trackedTickers.value.find((ticker) => ticker.code === rule.market)?.name ??
        rule.market,
    })),
  );

  watch(
    trackedTickers,
    (tickers) => {
      if (!tickers.length) {
        alertForm.market = "";
        alertRules.value = [];
        return;
      }
      if (!tickers.some((ticker) => ticker.code === alertForm.market)) {
        alertForm.market = tickers[0].code;
      }
      alertRules.value = alertRules.value.filter((rule) =>
        tickers.some((ticker) => ticker.code === rule.market),
      );
    },
    { immediate: true },
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

  async function addAlert() {
    const value = Number(alertForm.value);
    if (!Number.isFinite(value) || !alertForm.market) return;

    if (notificationPermission.value === "default") {
      await requestNotificationPermission();
    }

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
    const title = `${
      trackedTickers.value.find((ticker) => ticker.code === rule.market)?.name ??
      rule.market
    } alert`;
    const body = `Price is ${price.toFixed(2)} and moved ${rule.direction} ${rule.value}.`;

    if (notificationPermission.value === "granted") {
      new Notification(title, {
        body,
        tag: `${NOTIFICATION_TAG_PREFIX}-${rule.id}`,
        requireInteraction: true,
        renotify: true,
      });
    }

    if (typeof window !== "undefined") {
      window.focus();
      window.alert(`${title}\n\n${body}`);
    }
  }

  return {
    activeAlerts,
    alertForm,
    notificationPermission,
    addAlert,
    removeAlert,
    requestNotificationPermission,
  };
}
