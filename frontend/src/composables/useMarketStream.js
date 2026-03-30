import { computed, onBeforeUnmount, onMounted, ref } from "vue";

const DEFAULT_API_BASE =
  typeof window === "undefined"
    ? "http://127.0.0.1:8000"
    : `${window.location.protocol}//${window.location.hostname}:8000`;
const API_BASE = import.meta.env.VITE_API_BASE ?? DEFAULT_API_BASE;
const WS_BASE = API_BASE.replace(/^http/, "ws");
const HISTORY_POINT_LIMIT = 288;
const ORDER_STORAGE_KEY = "market-alerts:ticker-order";
const ORDER_SYNC_INTERVAL_MS = 60 * 60 * 1000;

export function useMarketStream() {
  const snapshot = ref({
    updated_at: null,
    tracked_tickers: [],
    markets: {},
    errors: [],
  });
  const connectionState = ref("connecting");
  const priceHistory = ref({});
  const tickerOrder = ref(loadTickerOrder());
  const hasLocalTickerOrder = ref(tickerOrder.value.length > 0);
  const panelOrderDirty = ref(false);

  let socket;
  let reconnectTimer;
  let panelOrderSyncTimer;
  let shouldReconnect = true;

  const orderedTickers = computed(() => {
    const tickers = [...(snapshot.value.tracked_tickers ?? [])];
    const rank = new Map(tickerOrder.value.map((code, index) => [code, index]));

    tickers.sort((left, right) => {
      const leftRank = rank.get(left.code);
      const rightRank = rank.get(right.code);

      if (leftRank == null && rightRank == null) return 0;
      if (leftRank == null) return 1;
      if (rightRank == null) return -1;
      return leftRank - rightRank;
    });

    return tickers;
  });

  const cards = computed(() =>
    orderedTickers.value.map((ticker) => ({
      code: ticker.code,
      title: ticker.name,
      subtitle: ticker.symbol,
      data: snapshot.value.markets[ticker.code] ?? null,
      history: priceHistory.value[ticker.code]?.points ?? [],
      historyStartedAt: priceHistory.value[ticker.code]?.startedAt ?? null,
    })),
  );

  const trackedTickers = computed(() => orderedTickers.value);

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

    const createdCode = payload.code?.trim().toUpperCase();
    if (createdCode) {
      tickerOrder.value = [...tickerOrder.value.filter((code) => code !== createdCode), createdCode];
      persistTickerOrder(tickerOrder.value);
      hasLocalTickerOrder.value = tickerOrder.value.length > 0;
      panelOrderDirty.value = true;
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

    tickerOrder.value = tickerOrder.value.filter((item) => item !== code);
    persistTickerOrder(tickerOrder.value);
    hasLocalTickerOrder.value = tickerOrder.value.length > 0;
    panelOrderDirty.value = true;

    snapshot.value = {
      ...snapshot.value,
      tracked_tickers: (snapshot.value.tracked_tickers ?? []).filter((ticker) => ticker.code !== code),
      markets: Object.fromEntries(
        Object.entries(snapshot.value.markets ?? {}).filter(([marketCode]) => marketCode !== code),
      ),
    };

    const nextHistory = { ...priceHistory.value };
    delete nextHistory[code];
    priceHistory.value = nextHistory;
  }

  function setTickerOrder(codes) {
    tickerOrder.value = [...codes];
    persistTickerOrder(tickerOrder.value);
    hasLocalTickerOrder.value = tickerOrder.value.length > 0;
    panelOrderDirty.value = true;
  }

  function connect() {
    socket = new WebSocket(`${WS_BASE}/ws/markets`);

    socket.addEventListener("open", () => {
      connectionState.value = "live";
    });

    socket.addEventListener("message", (event) => {
      const nextSnapshot = JSON.parse(event.data);
      snapshot.value = nextSnapshot;
      syncTickerOrder(nextSnapshot.tracked_tickers ?? []);
      ensureChartHistory(nextSnapshot.tracked_tickers ?? []);
      updateHistory(nextSnapshot);
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

  function updateHistory(nextSnapshot) {
    const nextHistory = { ...priceHistory.value };

    for (const ticker of nextSnapshot.tracked_tickers ?? []) {
      const price = nextSnapshot.markets?.[ticker.code]?.price;
      if (typeof price !== "number") continue;
      const pointTimestamp =
        nextSnapshot.markets?.[ticker.code]?.metadata?.last_bar_time ?? nextSnapshot.updated_at;
      nextHistory[ticker.code] = mergeLivePoint(
        nextHistory[ticker.code] ?? { points: [] },
        {
          timestamp: pointTimestamp,
          price,
        },
      );
    }

    for (const code of Object.keys(nextHistory)) {
      if (!(nextSnapshot.markets && code in nextSnapshot.markets)) {
        delete nextHistory[code];
      }
    }

    priceHistory.value = nextHistory;
  }

  onMounted(() => {
    hydrateTickerOrderFromDb();
    connect();
    panelOrderSyncTimer = window.setInterval(syncTickerOrderToDb, ORDER_SYNC_INTERVAL_MS);
  });

  onBeforeUnmount(() => {
    shouldReconnect = false;
    if (socket) socket.close();
    if (reconnectTimer) clearTimeout(reconnectTimer);
    if (panelOrderSyncTimer) clearInterval(panelOrderSyncTimer);
  });

  return {
    cards,
    connectionState,
    createTicker,
    deleteTicker,
    setTickerOrder,
    snapshot,
    trackedTickers,
  };

  function syncTickerOrder(tickers) {
    const activeCodes = new Set(tickers.map((ticker) => ticker.code));
    const merged = tickerOrder.value.filter((code) => activeCodes.has(code));

    for (const ticker of tickers) {
      if (!merged.includes(ticker.code)) {
        merged.push(ticker.code);
      }
    }

    if (JSON.stringify(merged) !== JSON.stringify(tickerOrder.value)) {
      tickerOrder.value = merged;
      persistTickerOrder(merged);
      hasLocalTickerOrder.value = merged.length > 0;
    }
  }

  async function hydrateTickerOrderFromDb() {
    if (typeof window === "undefined" || hasLocalTickerOrder.value) return;

    try {
      const response = await fetch(`${API_BASE}/api/preferences/panel-order`);
      if (!response.ok) return;

      const payload = await response.json();
      const codes = Array.isArray(payload?.codes)
        ? payload.codes.map((code) => `${code}`.trim().toUpperCase()).filter(Boolean)
        : [];

      if (codes.length === 0) return;

      tickerOrder.value = codes;
      persistTickerOrder(codes);
      hasLocalTickerOrder.value = true;
      panelOrderDirty.value = false;
    } catch {
      // Keep local-only behavior if the preference API is unavailable.
    }
  }

  async function syncTickerOrderToDb() {
    if (!panelOrderDirty.value || tickerOrder.value.length === 0) return;

    try {
      const response = await fetch(`${API_BASE}/api/preferences/panel-order`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ codes: tickerOrder.value }),
      });

      if (!response.ok) return;

      const payload = await response.json();
      if (Array.isArray(payload?.codes) && payload.codes.length > 0) {
        tickerOrder.value = payload.codes.map((code) => `${code}`.trim().toUpperCase()).filter(Boolean);
        persistTickerOrder(tickerOrder.value);
        hasLocalTickerOrder.value = true;
      }
      panelOrderDirty.value = false;
    } catch {
      // Leave dirty state intact so the next hourly attempt can retry.
    }
  }

  async function ensureChartHistory(tickers) {
    const missingCodes = tickers
      .map((ticker) => ticker.code)
      .filter((code) => !priceHistory.value[code]);

    if (!missingCodes.length) return;

    const histories = await Promise.all(
      missingCodes.map(async (code) => {
        try {
          const response = await fetch(`${API_BASE}/api/markets/${code}/history`);
          if (!response.ok) return null;
          return await response.json();
        } catch {
          return null;
        }
      }),
    );

    const nextHistory = { ...priceHistory.value };
    for (const history of histories) {
      if (!history?.code || !Array.isArray(history.points)) continue;
      nextHistory[history.code] = {
        points: history.points.map((point) => ({
          timestamp: point.timestamp,
          price: Number(point.price),
        })),
        startedAt: history.started_at ?? history.points[0]?.timestamp ?? null,
      };
    }
    priceHistory.value = nextHistory;
  }
}

function loadTickerOrder() {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(ORDER_STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function persistTickerOrder(order) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(ORDER_STORAGE_KEY, JSON.stringify(order));
}

function mergeLivePoint(history, point) {
  const timestamp = new Date(point.timestamp);
  if (Number.isNaN(timestamp.getTime())) {
    return history;
  }

  const nextPoint = {
    timestamp: timestamp.toISOString(),
    price: Number(point.price),
  };
  const bucket = floorToFiveMinuteBucket(timestamp);
  const points = [...(history.points ?? [])];
  const lastPoint = points.at(-1);

  if (lastPoint) {
    const lastBucket = floorToFiveMinuteBucket(new Date(lastPoint.timestamp));
    if (lastBucket === bucket) {
      points[points.length - 1] = nextPoint;
    } else if (bucket > lastBucket) {
      points.push(nextPoint);
    }
  } else {
    points.push(nextPoint);
  }

  return {
    points: points.slice(-HISTORY_POINT_LIMIT),
    startedAt: history.startedAt ?? points[0]?.timestamp ?? null,
  };
}

function floorToFiveMinuteBucket(date) {
  const bucket = new Date(date);
  bucket.setUTCSeconds(0, 0);
  bucket.setUTCMinutes(Math.floor(bucket.getUTCMinutes() / 5) * 5);
  return bucket.getTime();
}
