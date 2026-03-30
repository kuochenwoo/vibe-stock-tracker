import { onBeforeUnmount, onMounted, ref } from "vue";

const DEFAULT_API_BASE =
  typeof window === "undefined"
    ? "http://127.0.0.1:8000"
    : `${window.location.protocol}//${window.location.hostname}:8000`;
const API_BASE = import.meta.env.VITE_API_BASE ?? DEFAULT_API_BASE;
export function useTruthSocial() {
  const items = ref([]);
  const loading = ref(true);
  const error = ref("");
  const popupNotice = ref(null);

  let refreshTimer;
  let popupTimer;
  let hasHydrated = false;
  const seenIds = new Set();

  async function fetchTruthSocial() {
    try {
      const response = await fetch(`${API_BASE}/api/social/truth?limit=10`);
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail ?? "Failed to load Truth Social feed.");
      }

      const payload = await response.json();
      const nextItems = Array.isArray(payload?.items)
        ? payload.items.map((item) => ({
            id: item.id,
            source: item.source ?? "Truth Social",
            publishedAt: item.published_at,
            title: item.title,
            summary: item.summary,
            tags: Array.isArray(item.tags) ? item.tags : [],
            url: item.url ?? null,
            author: item.author ?? null,
          }))
        : [];
      items.value = nextItems;
      handleNewPosts(nextItems);
      error.value = "";
    } catch (fetchError) {
      error.value =
        fetchError instanceof Error
          ? fetchError.message
          : "Failed to load Truth Social feed.";
    } finally {
      loading.value = false;
    }
  }

  onMounted(() => {
    fetchTruthSocial();
    scheduleNextRefresh();
  });

  onBeforeUnmount(() => {
    if (refreshTimer) window.clearInterval(refreshTimer);
    if (popupTimer) window.clearTimeout(popupTimer);
  });

  return {
    items,
    loading,
    error,
    popupNotice,
    dismissPopup,
  };

  function scheduleNextRefresh() {
    if (refreshTimer) {
      window.clearTimeout(refreshTimer);
    }

    refreshTimer = window.setTimeout(() => {
      fetchTruthSocial();
      scheduleNextRefresh();
    }, getRefreshIntervalMs());
  }

  function handleNewPosts(nextItems) {
    if (!hasHydrated) {
      nextItems.forEach((item) => seenIds.add(item.id));
      hasHydrated = true;
      return;
    }

    const freshItems = nextItems.filter((item) => !seenIds.has(item.id));
    nextItems.forEach((item) => seenIds.add(item.id));
    if (!freshItems.length) return;

    notifyNewPost(freshItems[0]);
  }

  function notifyNewPost(item) {
    const title = "Trump posted on Truth Social";
    const body = item.title;

    if (typeof Notification !== "undefined") {
      if (Notification.permission === "granted") {
        new Notification(title, {
          body,
          tag: `truth-social-${item.id}`,
          requireInteraction: true,
          renotify: true,
        });
      } else if (Notification.permission === "default") {
        Notification.requestPermission().catch(() => {});
      }
    }

    popupNotice.value = {
      id: item.id,
      label: "Truth Social",
      title,
      body,
      metaPrimary: item.author ?? "@realDonaldTrump",
      metaSecondary: new Intl.DateTimeFormat(undefined, {
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
    }, 8000);
  }

  function dismissPopup() {
    popupNotice.value = null;
    if (popupTimer) {
      window.clearTimeout(popupTimer);
      popupTimer = undefined;
    }
  }
}

function getRefreshIntervalMs() {
  const now = new Date();
  const ny = getNewYorkParts(now);
  const weekdayMap = {
    Sun: 0,
    Mon: 1,
    Tue: 2,
    Wed: 3,
    Thu: 4,
    Fri: 5,
    Sat: 6,
  };
  const weekday = weekdayMap[ny.weekday] ?? 0;
  const isWeekday = weekday >= 1 && weekday <= 5;
  const totalMinutes = ny.hour * 60 + ny.minute;
  const isPreOrIntraday = totalMinutes >= 4 * 60 && totalMinutes <= 16 * 60;

  return isWeekday && isPreOrIntraday ? 60 * 1000 : 10 * 60 * 1000;
}

function getNewYorkParts(date) {
  const formatter = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  const parts = Object.fromEntries(
    formatter
      .formatToParts(date)
      .filter((part) => part.type !== "literal")
      .map((part) => [part.type, part.value]),
  );
  return {
    weekday: parts.weekday,
    hour: Number(parts.hour),
    minute: Number(parts.minute),
  };
}
