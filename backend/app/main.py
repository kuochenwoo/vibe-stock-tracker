import asyncio
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

POLL_INTERVAL_SECONDS = 5
YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"
SYMBOL_MAP = {
    "CL": {"query": "CL=F", "label": "Crude Oil Futures"},
    "XAUUSD": {"query": "XAUUSD=X", "label": "Gold Spot"},
}


class MarketState:
    def __init__(self) -> None:
        self.snapshot: dict[str, Any] = {
            "updated_at": None,
            "markets": {},
            "errors": [],
        }
        self.connections: set[WebSocket] = set()
        self.lock = asyncio.Lock()

    async def set_snapshot(self, snapshot: dict[str, Any]) -> None:
        async with self.lock:
            self.snapshot = snapshot

    async def get_snapshot(self) -> dict[str, Any]:
        async with self.lock:
            return self.snapshot

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.connections.discard(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        stale_connections: list[WebSocket] = []
        for connection in self.connections:
            try:
                await connection.send_json(message)
            except RuntimeError:
                stale_connections.append(connection)
        for connection in stale_connections:
            self.disconnect(connection)


state = MarketState()


def build_market_payload(result: dict[str, Any], code: str) -> dict[str, Any]:
    previous_close = result.get("regularMarketPreviousClose") or 0
    price = result.get("regularMarketPrice")
    change = result.get("regularMarketChange")
    change_percent = result.get("regularMarketChangePercent")

    return {
        "code": code,
        "symbol": SYMBOL_MAP[code]["query"],
        "name": SYMBOL_MAP[code]["label"],
        "price": price,
        "currency": result.get("currency") or "USD",
        "change": change,
        "change_percent": change_percent,
        "previous_close": previous_close,
        "market_state": result.get("marketState") or "UNKNOWN",
    }


async def fetch_snapshot() -> dict[str, Any]:
    params = {"symbols": ",".join(item["query"] for item in SYMBOL_MAP.values())}
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(YAHOO_QUOTE_URL, params=params, headers=headers)
        response.raise_for_status()
        payload = response.json()

    results = payload.get("quoteResponse", {}).get("result", [])
    markets: dict[str, Any] = {}
    errors: list[str] = []

    for code, config in SYMBOL_MAP.items():
        quote = next((item for item in results if item.get("symbol") == config["query"]), None)
        if quote is None:
            errors.append(f"Missing quote for {config['query']}")
            continue
        markets[code] = build_market_payload(quote, code)

    return {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "markets": markets,
        "errors": errors,
    }


async def poll_markets() -> None:
    while True:
        try:
            snapshot = await fetch_snapshot()
            await state.set_snapshot(snapshot)
            await state.broadcast(snapshot)
        except Exception as exc:  # noqa: BLE001
            previous = await state.get_snapshot()
            snapshot = {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "markets": previous.get("markets", {}),
                "errors": [f"{type(exc).__name__}: {exc}"],
            }
            await state.set_snapshot(snapshot)
            await state.broadcast(snapshot)

        await asyncio.sleep(POLL_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(poll_markets())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="Market Alerts API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/markets")
async def get_markets() -> dict[str, Any]:
    return await state.get_snapshot()


@app.websocket("/ws/markets")
async def markets_ws(websocket: WebSocket) -> None:
    await state.connect(websocket)
    try:
        await websocket.send_json(await state.get_snapshot())
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        state.disconnect(websocket)
