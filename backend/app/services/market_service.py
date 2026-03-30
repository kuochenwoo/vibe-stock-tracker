from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.core.constants import (
    ASSET_TYPE_CRYPTO,
    CRYPTO_SYMBOL_SUFFIXES,
    DAILY_BAR_REFRESH_LAG_DAYS,
    DEFAULT_SESSION_START_BY_ASSET,
    DEFAULT_SESSION_TIMEZONE_BY_ASSET,
    FUTURES_SYMBOL_SUFFIX,
    MARKET_HISTORY_DEFAULT_RANGE,
    MARKET_HISTORY_INTRADAY_FRESH_MINUTES,
    MARKET_HISTORY_INTRADAY_INTERVAL,
    MARKET_HISTORY_INTRADAY_PERIOD,
    MARKET_HISTORY_YEAR_BAR_LIMIT,
    MARKET_HISTORY_YEAR_FRESH_DAYS,
    MARKET_HISTORY_YEAR_RANGE,
    MARKET_HISTORY_YEAR_REFRESH_PERIOD,
    MARKET_HISTORY_YEAR_SEED_PERIOD,
)
from app.models.market import MarketHistoryPoint, MarketHistoryResponse, MarketSnapshot, TrackedTicker
from app.providers.base import MarketDataProvider
from app.core.cache import RedisMarketCache
from app.repositories.daily_bar_repository import DailyBarRepository
from app.services.market_state import MarketStateStore
from app.services.ticker_service import TickerService


class MarketService:
    def __init__(
        self,
        provider: MarketDataProvider,
        state_store: MarketStateStore,
        ticker_service: TickerService,
        cache: RedisMarketCache,
        daily_bar_repository: DailyBarRepository,
        macro_tickers: list[TrackedTicker] | None = None,
    ) -> None:
        self.provider = provider
        self.state_store = state_store
        self.ticker_service = ticker_service
        self.cache = cache
        self.daily_bar_repository = daily_bar_repository
        self.macro_tickers = macro_tickers or []

    async def refresh_snapshot(self) -> MarketSnapshot:
        requested_tickers = _merge_tickers(self.ticker_service.list_tickers(), self.macro_tickers)
        try:
            provider_snapshot = await self.provider.fetch_snapshot(requested_tickers)
            current_tickers = self.ticker_service.list_tickers()
            allowed_codes = {ticker.code for ticker in current_tickers}
            allowed_codes.update(ticker.code for ticker in self.macro_tickers)
            snapshot = MarketSnapshot(
                updated_at=provider_snapshot.updated_at,
                tracked_tickers=current_tickers,
                macro_tickers=self.macro_tickers,
                markets={
                    code: quote
                    for code, quote in provider_snapshot.markets.items()
                    if code in allowed_codes
                },
                errors=provider_snapshot.errors,
            )
        except Exception as exc:  # noqa: BLE001
            previous = await self.state_store.get_snapshot()
            current_tickers = self.ticker_service.list_tickers()
            allowed_codes = {ticker.code for ticker in current_tickers}
            allowed_codes.update(ticker.code for ticker in self.macro_tickers)
            snapshot = MarketSnapshot(
                updated_at=datetime.now(timezone.utc),
                tracked_tickers=current_tickers,
                macro_tickers=self.macro_tickers,
                markets={
                    code: quote
                    for code, quote in previous.markets.items()
                    if code in allowed_codes
                },
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

    async def get_history(self, code: str, *, range_value: str = MARKET_HISTORY_DEFAULT_RANGE) -> MarketHistoryResponse:
        ticker = self._get_tracked_ticker(code)
        range_key = range_value.strip().lower()
        cached = await self.cache.get_chart_history(f"{ticker.code}:{range_key}")
        if cached and _history_is_fresh(cached):
            return cached

        if range_key == MARKET_HISTORY_YEAR_RANGE:
            history = await self._build_year_history(ticker)
        else:
            raw_points = await self.provider.fetch_history(
                ticker,
                period=MARKET_HISTORY_INTRADAY_PERIOD,
                interval=MARKET_HISTORY_INTRADAY_INTERVAL,
            )
            history = self._normalize_intraday_history(ticker, raw_points)

        await self.cache.set_chart_history(f"{ticker.code}:{range_key}", history)
        return history

    def _get_tracked_ticker(self, code: str) -> TrackedTicker:
        lookup = code.strip().upper()
        for ticker in self.ticker_service.list_tickers():
            if ticker.code == lookup:
                return ticker
        raise ValueError(f"Ticker code '{lookup}' was not found.")

    async def _build_year_history(self, ticker: TrackedTicker) -> MarketHistoryResponse:
        stored_bars = list(
            reversed(self.daily_bar_repository.list_recent_bars(ticker.code, MARKET_HISTORY_YEAR_BAR_LIMIT))
        )
        latest_trading_date = self.daily_bar_repository.get_latest_trading_date(ticker.code)

        if len(stored_bars) < MARKET_HISTORY_YEAR_BAR_LIMIT or latest_trading_date is None:
            fetched_bars = await self.provider.fetch_daily_bars(ticker, period=MARKET_HISTORY_YEAR_SEED_PERIOD)
            self.daily_bar_repository.upsert_bars(ticker.code, fetched_bars)
        elif _daily_bars_need_refresh(latest_trading_date):
            recent_bars = await self.provider.fetch_daily_bars(ticker, period=MARKET_HISTORY_YEAR_REFRESH_PERIOD)
            self.daily_bar_repository.upsert_bars(ticker.code, recent_bars)

        bars = list(
            reversed(self.daily_bar_repository.list_recent_bars(ticker.code, MARKET_HISTORY_YEAR_BAR_LIMIT))
        )
        points = [
            MarketHistoryPoint(
                timestamp=datetime.combine(bar.trading_date, time.min, tzinfo=timezone.utc),
                price=bar.close,
            )
            for bar in bars[-MARKET_HISTORY_YEAR_BAR_LIMIT :]
        ]
        prices = [point.price for point in points]
        config = _resolve_session_config(ticker)
        return MarketHistoryResponse(
            code=ticker.code,
            symbol=ticker.symbol,
            name=ticker.name,
            range=MARKET_HISTORY_YEAR_RANGE,
            interval="1d",
            asset_type=config["asset_type"],
            session_timezone=config["session_timezone"],
            session_start=config["session_start"],
            points=points,
            high=max(prices) if prices else None,
            low=min(prices) if prices else None,
            current=prices[-1] if prices else None,
            started_at=points[0].timestamp if points else None,
            ended_at=points[-1].timestamp if points else None,
        )

    def _normalize_intraday_history(
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
            range=MARKET_HISTORY_DEFAULT_RANGE,
            interval=MARKET_HISTORY_INTRADAY_INTERVAL,
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
    if normalized.endswith(FUTURES_SYMBOL_SUFFIX):
        return "futures"
    if normalized.endswith(CRYPTO_SYMBOL_SUFFIXES):
        return ASSET_TYPE_CRYPTO
    return "stock"


def _default_timezone(asset_type: str) -> str:
    return DEFAULT_SESSION_TIMEZONE_BY_ASSET.get(asset_type, "America/New_York")


def _default_session_start(asset_type: str) -> str:
    return DEFAULT_SESSION_START_BY_ASSET.get(asset_type, "04:00")


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
    if history.range == MARKET_HISTORY_YEAR_RANGE:
        return history.ended_at.date() >= (
            datetime.now(timezone.utc).date() - timedelta(days=MARKET_HISTORY_YEAR_FRESH_DAYS)
        )
    return datetime.now(timezone.utc) - history.ended_at <= timedelta(
        minutes=MARKET_HISTORY_INTRADAY_FRESH_MINUTES
    )


def _daily_bars_need_refresh(latest_trading_date) -> bool:
    return latest_trading_date < (
        datetime.now(timezone.utc).date() - timedelta(days=DAILY_BAR_REFRESH_LAG_DAYS)
    )


def _merge_tickers(primary: list[TrackedTicker], secondary: list[TrackedTicker]) -> list[TrackedTicker]:
    merged: dict[str, TrackedTicker] = {ticker.code: ticker for ticker in primary}
    for ticker in secondary:
        merged.setdefault(ticker.code, ticker)
    return list(merged.values())
