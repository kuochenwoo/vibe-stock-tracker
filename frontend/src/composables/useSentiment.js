import { onBeforeUnmount, onMounted, ref } from "vue";

const DEFAULT_API_BASE =
  typeof window === "undefined"
    ? "http://127.0.0.1:8000"
    : `${window.location.protocol}//${window.location.hostname}:8000`;
const API_BASE = import.meta.env.VITE_API_BASE ?? DEFAULT_API_BASE;
const REFRESH_INTERVAL_MS = 15 * 60 * 1000;

export function useSentiment() {
  const snapshot = ref(null);
  const loading = ref(true);
  const error = ref("");

  let refreshTimer;

  async function fetchFearGreed() {
    try {
      const response = await fetch(`${API_BASE}/api/sentiment/fear-greed`);
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail ?? "Failed to load fear and greed index.");
      }

      snapshot.value = await response.json();
      error.value = "";
    } catch (fetchError) {
      error.value =
        fetchError instanceof Error
          ? fetchError.message
          : "Failed to load fear and greed index.";
    } finally {
      loading.value = false;
    }
  }

  onMounted(() => {
    fetchFearGreed();
    refreshTimer = window.setInterval(fetchFearGreed, REFRESH_INTERVAL_MS);
  });

  onBeforeUnmount(() => {
    if (refreshTimer) window.clearInterval(refreshTimer);
  });

  return {
    error,
    loading,
    snapshot,
  };
}
