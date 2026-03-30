import { computed, ref, watch } from "vue";

const STORAGE_KEY = "market-alerts.rules.v1";
const NOTIFICATION_TAG_PREFIX = "market-alert";
const POPUP_DURATION_MS = 7000;

function createRuleId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }

  return `rule-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

export function useAlerts(snapshot, trackedTickers) {
  const notificationPermission = ref(
    typeof Notification === "undefined" ? "unsupported" : Notification.permission,
  );
  const alertRules = ref(loadRules());
  const triggeredKeys = ref(new Set());
  const popupNotice = ref(null);

  let popupTimer;

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
        alertRules.value = [];
        return;
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

  async function addAlert(payload) {
    const value = Number(payload?.value);
    if (!Number.isFinite(value) || !payload?.market) return;

    alertRules.value.unshift({
      id: createRuleId(),
      market: payload.market,
      direction: payload.direction,
      value,
      triggered: false,
      created_at: new Date().toISOString(),
    });
  }

  function removeAlert(id) {
    alertRules.value = alertRules.value.filter((rule) => rule.id !== id);
    triggeredKeys.value.delete(id);
  }

  function dismissPopup() {
    popupNotice.value = null;
    if (popupTimer) {
      window.clearTimeout(popupTimer);
      popupTimer = undefined;
    }
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
    const marketTitle =
      trackedTickers.value.find((ticker) => ticker.code === rule.market)?.name ??
      rule.market;
    const title = `${marketTitle} alert`;
    const body = `Price moved ${rule.direction} ${rule.value.toFixed(2)} and is now ${price.toFixed(2)}.`;

    if (notificationPermission.value === "granted") {
      new Notification(title, {
        body,
        tag: `${NOTIFICATION_TAG_PREFIX}-${rule.id}`,
        requireInteraction: true,
        renotify: true,
      });
    }

    if (typeof window !== "undefined") {
      popupNotice.value = {
        id: rule.id,
        title,
        body,
        price: price.toFixed(2),
        time: new Intl.DateTimeFormat(undefined, {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        }).format(new Date()),
      };

      if (popupTimer) {
        window.clearTimeout(popupTimer);
      }

      popupTimer = window.setTimeout(() => {
        popupNotice.value = null;
        popupTimer = undefined;
      }, POPUP_DURATION_MS);
    }
  }

  return {
    activeAlerts,
    notificationPermission,
    popupNotice,
    addAlert,
    dismissPopup,
    removeAlert,
    requestNotificationPermission,
  };
}
