import { onBeforeUnmount, onMounted, ref } from "vue";

const DEFAULT_API_BASE =
  typeof window === "undefined"
    ? "http://127.0.0.1:8000"
    : `${window.location.protocol}//${window.location.hostname}:8000`;
const API_BASE = import.meta.env.VITE_API_BASE ?? DEFAULT_API_BASE;
const REFRESH_INTERVAL_MS = 10 * 60 * 1000;

export function useWireNews() {
  const items = ref([]);
  const loading = ref(true);
  const error = ref("");

  let refreshTimer;

  async function fetchWireNews() {
    try {
      const response = await fetch(`${API_BASE}/api/news/wire?limit=10`);
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail ?? "Failed to load wire news.");
      }

      const payload = await response.json();
      items.value = Array.isArray(payload?.items)
        ? payload.items.map((item) => ({
            id: item.id,
            source: item.source ?? "Bloomberg",
            publishedAt: item.published_at,
            title: item.title,
            summary: item.summary,
            tags: Array.isArray(item.tags) ? item.tags : [],
            url: item.url ?? null,
          }))
        : [];
      error.value = "";
    } catch (fetchError) {
      error.value =
        fetchError instanceof Error
          ? fetchError.message
          : "Failed to load wire news.";
    } finally {
      loading.value = false;
    }
  }

  onMounted(() => {
    fetchWireNews();
    refreshTimer = window.setInterval(fetchWireNews, REFRESH_INTERVAL_MS);
  });

  onBeforeUnmount(() => {
    if (refreshTimer) window.clearInterval(refreshTimer);
  });

  return {
    items,
    loading,
    error,
  };
}
