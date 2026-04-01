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
  const alertHistory = ref([]);
  const hasUnreadHistory = ref(false);
  const lastReadTriggeredAt = ref(null);

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
      const [alertsRes, historyRes, readRes] = await Promise.all([
        fetch(`${API_BASE}/api/alerts`),
        fetch(`${API_BASE}/api/alerts/history`),
        fetch(`${API_BASE}/api/preferences/alert-history-read`),
      ]);

      if (alertsRes.ok) {
        alertRules.value = await alertsRes.json();
      }
      if (historyRes.ok) {
        alertHistory.value = await historyRes.json();
      }
      if (readRes.ok) {
        const payload = await readRes.json();
        lastReadTriggeredAt.value = payload?.last_read_triggered_at ?? null;
      }
      syncUnreadState();
    } catch {
      alertRules.value = [];
    }
  }

  async function fetchHistory() {
    try {
      const response = await fetch(`${API_BASE}/api/alerts/history`);
      if (response.ok) {
        alertHistory.value = await response.json();
        syncUnreadState();
      }
    } catch (error) {
      console.error("Failed to fetch alert history:", error);
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

  async function markHistoryRead() {
    const latestTriggeredAt = alertHistory.value[0]?.triggered_at;
    if (!latestTriggeredAt) {
      hasUnreadHistory.value = false;
      return;
    }

    lastReadTriggeredAt.value = latestTriggeredAt;
    hasUnreadHistory.value = false;
    try {
      await fetch(`${API_BASE}/api/preferences/alert-history-read`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          last_read_triggered_at: latestTriggeredAt,
        }),
      });
    } catch (error) {
      console.error("Failed to persist alert history read marker:", error);
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

    // Record history
    fetch(`${API_BASE}/api/alerts/history`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        alert_rule_id: rule.id,
        market: rule.market,
        direction: rule.direction,
        threshold: rule.value,
        price: price,
      }),
    })
      .then((res) => {
        if (res.ok) {
          fetchHistory();
        }
      })
      .catch((err) => console.error("Failed to record alert history:", err));

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
    alertHistory,
    hasUnreadHistory,
    notificationPermission,
    popupNotice,
    addAlert,
    dismissPopup,
    fetchHistory,
    markHistoryRead,
    removeAlert,
    requestNotificationPermission,
  };

  function syncUnreadState() {
    const latestTriggeredAt = alertHistory.value[0]?.triggered_at;
    if (!latestTriggeredAt) {
      hasUnreadHistory.value = false;
      return;
    }
    if (!lastReadTriggeredAt.value) {
      hasUnreadHistory.value = true;
      return;
    }
    hasUnreadHistory.value =
      new Date(latestTriggeredAt).getTime() > new Date(lastReadTriggeredAt.value).getTime();
  }
}
