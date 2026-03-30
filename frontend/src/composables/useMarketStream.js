import { computed, onBeforeUnmount, onMounted, ref } from "vue";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";
const WS_BASE = API_BASE.replace(/^http/, "ws");

export function useMarketStream() {
  const snapshot = ref({
    updated_at: null,
    tracked_tickers: [],
    markets: {},
    errors: [],
  });
  const connectionState = ref("connecting");

  let socket;
  let reconnectTimer;
  let shouldReconnect = true;

  const cards = computed(() =>
    snapshot.value.tracked_tickers.map((ticker) => ({
      code: ticker.code,
      title: ticker.name,
      subtitle: ticker.symbol,
      data: snapshot.value.markets[ticker.code] ?? null,
    })),
  );

  const trackedTickers = computed(() => snapshot.value.tracked_tickers ?? []);

  async function createTicker(payload) {
    const response = await fetch(`${API_BASE}/api/tickers`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail ?? "Failed to add ticker.");
    }
  }

  async function deleteTicker(code) {
    const response = await fetch(`${API_BASE}/api/tickers/${code}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail ?? "Failed to delete ticker.");
    }
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

  onMounted(() => {
    connect();
  });

  onBeforeUnmount(() => {
    shouldReconnect = false;
    if (socket) socket.close();
    if (reconnectTimer) clearTimeout(reconnectTimer);
  });

  return {
    cards,
    connectionState,
    createTicker,
    deleteTicker,
    snapshot,
    trackedTickers,
  };
}
