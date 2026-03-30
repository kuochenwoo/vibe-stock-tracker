from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.models.market import MarketHistoryPoint, MarketHistoryResponse, MarketSnapshot, TrackedTicker
from app.providers.base import MarketDataProvider
from app.core.cache import RedisMarketCache
from app.services.market_state import MarketStateStore
from app.services.ticker_service import TickerService


class MarketService:
    def __init__(
        self,
        provider: MarketDataProvider,
        state_store: MarketStateStore,
        ticker_service: TickerService,
        cache: RedisMarketCache,
        macro_tickers: list[TrackedTicker] | None = None,
    ) -> None:
        self.provider = provider
        self.state_store = state_store
        self.ticker_service = ticker_service
        self.cache = cache
        self.macro_tickers = macro_tickers or []

    async def refresh_snapshot(self) -> MarketSnapshot:
        tickers = self.ticker_service.list_tickers()
        requested_tickers = _merge_tickers(tickers, self.macro_tickers)
        try:
            provider_snapshot = await self.provider.fetch_snapshot(requested_tickers)
            snapshot = MarketSnapshot(
                updated_at=provider_snapshot.updated_at,
                tracked_tickers=tickers,
                macro_tickers=self.macro_tickers,
                markets=provider_snapshot.markets,
                errors=provider_snapshot.errors,
            )
        except Exception as exc:  # noqa: BLE001
            previous = await self.state_store.get_snapshot()
            snapshot = MarketSnapshot(
                updated_at=datetime.now(timezone.utc),
                tracked_tickers=tickers,
                macro_tickers=self.macro_tickers,
                markets=previous.markets,
                errors=[f"{type(exc).__name__}: {exc}"],
            )

        await self.state_store.set_snapshot(snapshot)
        for quote in snapshot.markets.values():
            await self.cache.set_latest_quote(quote)
            await self.cache.set_prev_5m_close(quote)
        await self.state_store.broadcast(snapshot)
        return snapshot

    async def publish_tracked_tickers(self, tickers: list[TrackedTicker]) -> MarketSnapshot:
        previous = await self.state_store.get_snapshot()
        allowed_codes = {ticker.code for ticker in tickers}
        allowed_codes.update(ticker.code for ticker in self.macro_tickers)
        snapshot = MarketSnapshot(
            updated_at=previous.updated_at,
            tracked_tickers=tickers,
            macro_tickers=self.macro_tickers,
            markets={
                code: quote
                for code, quote in previous.markets.items()
                if code in allowed_codes
            },
            errors=previous.errors,
        )
        await self.state_store.set_snapshot(snapshot)
        await self.state_store.broadcast(snapshot)
        return snapshot

    async def warm_ticker_data(self, code: str) -> None:
        await self.refresh_snapshot()
        try:
            await self.get_history(code)
        except ValueError:
            return

    async def get_snapshot(self) -> MarketSnapshot:
        return await self.state_store.get_snapshot()

    async def get_history(self, code: str) -> MarketHistoryResponse:
        ticker = self._get_tracked_ticker(code)
        cached = await self.cache.get_chart_history(ticker.code)
        if cached and _history_is_fresh(cached):
            return cached

        raw_points = await self.provider.fetch_history(
            ticker,
            period="5d",
            interval="5m",
        )
        history = self._normalize_history(ticker, raw_points)
        await self.cache.set_chart_history(history)
        return history

    def _get_tracked_ticker(self, code: str) -> TrackedTicker:
        lookup = code.strip().upper()
        for ticker in self.ticker_service.list_tickers():
            if ticker.code == lookup:
                return ticker
        raise ValueError(f"Ticker code '{lookup}' was not found.")

    def _normalize_history(
        self,
        ticker: TrackedTicker,
        points: list[MarketHistoryPoint],
    ) -> MarketHistoryResponse:
        config = _resolve_session_config(ticker)
        timezone_name = config["session_timezone"]
        zone = ZoneInfo(timezone_name)
        start_time = _parse_session_start(config["session_start"])
        anchor_timestamp = points[-1].timestamp.astimezone(zone) if points else datetime.now(zone)
        session_started_at = _latest_session_start(anchor_timestamp, start_time)
        session_started_utc = session_started_at.astimezone(timezone.utc)

        visible_points = [point for point in points if point.timestamp >= session_started_utc]
        if not visible_points:
            visible_points = points[-1:] if points else []

        prices = [point.price for point in visible_points]
        return MarketHistoryResponse(
            code=ticker.code,
            symbol=ticker.symbol,
            name=ticker.name,
            asset_type=config["asset_type"],
            session_timezone=timezone_name,
            session_start=config["session_start"],
            points=visible_points,
            high=max(prices) if prices else None,
            low=min(prices) if prices else None,
            current=prices[-1] if prices else None,
            started_at=session_started_utc,
            ended_at=visible_points[-1].timestamp if visible_points else None,
        )


def _resolve_session_config(ticker: TrackedTicker) -> dict[str, str]:
    metadata = ticker.metadata or {}
    asset_type = str(metadata.get("asset_type") or _infer_asset_type(ticker.symbol)).lower()
    timezone_name = str(metadata.get("session_timezone") or _default_timezone(asset_type))
    session_start = str(metadata.get("session_start") or _default_session_start(asset_type))

    return {
        "asset_type": asset_type,
        "session_timezone": timezone_name,
        "session_start": session_start,
    }


def _infer_asset_type(symbol: str) -> str:
    normalized = symbol.upper()
    if normalized.endswith("=F"):
        return "futures"
    if normalized.endswith("-USD") or normalized.endswith("-USDT"):
        return "crypto"
    return "stock"


def _default_timezone(asset_type: str) -> str:
    if asset_type == "crypto":
        return "UTC"
    return "America/New_York"


def _default_session_start(asset_type: str) -> str:
    if asset_type == "futures":
        return "18:00"
    if asset_type == "crypto":
        return "00:00"
    return "04:00"


def _parse_session_start(value: str) -> time:
    hour_text, minute_text = value.split(":", maxsplit=1)
    return time(hour=int(hour_text), minute=int(minute_text))


def _latest_session_start(current: datetime, session_start: time) -> datetime:
    anchored = current.replace(
        hour=session_start.hour,
        minute=session_start.minute,
        second=0,
        microsecond=0,
    )
    if current < anchored:
        anchored -= timedelta(days=1)
    return anchored


def _history_is_fresh(history: MarketHistoryResponse) -> bool:
    if history.ended_at is None:
        return False
    return datetime.now(timezone.utc) - history.ended_at <= timedelta(minutes=5)


def _merge_tickers(primary: list[TrackedTicker], secondary: list[TrackedTicker]) -> list[TrackedTicker]:
    merged: dict[str, TrackedTicker] = {ticker.code: ticker for ticker in primary}
    for ticker in secondary:
        merged.setdefault(ticker.code, ticker)
    return list(merged.values())
