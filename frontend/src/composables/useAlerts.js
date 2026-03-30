import { computed, onMounted, ref, watch } from "vue";

const DEFAULT_API_BASE =
  typeof window === "undefined"
    ? "http://127.0.0.1:8000"
    : `${window.location.protocol}//${window.location.hostname}:8000`;
const API_BASE = import.meta.env.VITE_API_BASE ?? DEFAULT_API_BASE;
const NOTIFICATION_TAG_PREFIX = "market-alert";
const POPUP_DURATION_MS = 7000;

export function useAlerts(snapshot, trackedTickers) {
  const notificationPermission = ref(
    typeof Notification === "undefined" ? "unsupported" : Notification.permission,
  );
  const alertRules = ref([]);
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
    snapshot,
    (value) => {
      evaluateAlerts(value.markets);
    },
    { deep: true },
  );

  onMounted(() => {
    loadAlerts();
  });

  async function requestNotificationPermission() {
    if (typeof Notification === "undefined") return;
    notificationPermission.value = await Notification.requestPermission();
  }

  async function loadAlerts() {
    try {
      const response = await fetch(`${API_BASE}/api/alerts`);
      if (!response.ok) {
        throw new Error("Failed to load alerts.");
      }

      alertRules.value = await response.json();
    } catch {
      alertRules.value = [];
    }
  }

  async function addAlert(payload) {
    const value = Number(payload?.value);
    if (!Number.isFinite(value) || !payload?.market) return;

    const response = await fetch(`${API_BASE}/api/alerts`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        market: payload.market,
        direction: payload.direction,
        value,
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail ?? "Failed to add alert.");
    }

    alertRules.value = await response.json();
  }

  async function removeAlert(id) {
    const response = await fetch(`${API_BASE}/api/alerts/${id}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail ?? "Failed to remove alert.");
    }

    alertRules.value = await response.json();
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
