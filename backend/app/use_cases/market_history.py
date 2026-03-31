from __future__ import annotations

from datetime import datetime, time, timezone

from app.core.cache import RedisMarketCache
from app.core.constants import (
    MARKET_HISTORY_DEFAULT_RANGE,
    MARKET_HISTORY_INTRADAY_INTERVAL,
    MARKET_HISTORY_INTRADAY_PERIOD,
    MARKET_HISTORY_YEAR_BAR_LIMIT,
    MARKET_HISTORY_YEAR_RANGE,
    MARKET_HISTORY_YEAR_REFRESH_PERIOD,
    MARKET_HISTORY_YEAR_SEED_PERIOD,
)
from app.domain.market_rules import history_is_fresh, resolve_session_profile, session_started_utc
from app.models.market import MarketHistoryPoint, MarketHistoryResponse
from app.providers.base import MarketDataProvider
from app.repositories.protocols import DailyBarRepositoryProtocol, TickerRepositoryProtocol


class GetMarketHistoryUseCase:
    def __init__(
        self,
        *,
        provider: MarketDataProvider,
        cache: RedisMarketCache,
        ticker_repository: TickerRepositoryProtocol,
        daily_bar_repository: DailyBarRepositoryProtocol,
    ) -> None:
        self.provider = provider
        self.cache = cache
        self.ticker_repository = ticker_repository
        self.daily_bar_repository = daily_bar_repository

    async def execute(self, code: str, *, range_value: str = MARKET_HISTORY_DEFAULT_RANGE) -> MarketHistoryResponse:
        ticker = self._get_ticker(code)
        range_key = range_value.strip().lower()
        cached = await self.cache.get_chart_history(f"{ticker.code}:{range_key}")
        if cached and history_is_fresh(cached):
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

    def _get_ticker(self, code: str):
        lookup = code.strip().upper()
        for ticker in self.ticker_repository.list_all():
            if ticker.code == lookup:
                return ticker
        raise ValueError(f"Ticker code '{lookup}' was not found.")

    async def _build_year_history(self, ticker) -> MarketHistoryResponse:
        stored_bars = list(
            reversed(self.daily_bar_repository.list_recent_bars(ticker.code, MARKET_HISTORY_YEAR_BAR_LIMIT))
        )
        latest_trading_date = self.daily_bar_repository.get_latest_trading_date(ticker.code)

        if len(stored_bars) < MARKET_HISTORY_YEAR_BAR_LIMIT or latest_trading_date is None:
            fetched_bars = await self.provider.fetch_daily_bars(ticker, period=MARKET_HISTORY_YEAR_SEED_PERIOD)
            self.daily_bar_repository.upsert_bars(ticker.code, fetched_bars)
        elif self._daily_bars_need_refresh(latest_trading_date):
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
        profile = resolve_session_profile(ticker)
        return MarketHistoryResponse(
            code=ticker.code,
            symbol=ticker.symbol,
            name=ticker.name,
            range=MARKET_HISTORY_YEAR_RANGE,
            interval="1d",
            asset_type=profile.asset_type,
            session_timezone=profile.session_timezone,
            session_start=profile.session_start,
            points=points,
            high=max(prices) if prices else None,
            low=min(prices) if prices else None,
            current=prices[-1] if prices else None,
            started_at=points[0].timestamp if points else None,
            ended_at=points[-1].timestamp if points else None,
        )

    def _normalize_intraday_history(self, ticker, points: list[MarketHistoryPoint]) -> MarketHistoryResponse:
        profile = resolve_session_profile(ticker)
        anchor_timestamp = points[-1].timestamp if points else datetime.now(timezone.utc)
        started_at = session_started_utc(profile, anchor_timestamp)
        visible_points = [point for point in points if point.timestamp >= started_at]
        if not visible_points:
            visible_points = points[-1:] if points else []

        prices = [point.price for point in visible_points]
        return MarketHistoryResponse(
            code=ticker.code,
            symbol=ticker.symbol,
            name=ticker.name,
            range=MARKET_HISTORY_DEFAULT_RANGE,
            interval=MARKET_HISTORY_INTRADAY_INTERVAL,
            asset_type=profile.asset_type,
            session_timezone=profile.session_timezone,
            session_start=profile.session_start,
            points=visible_points,
            high=max(prices) if prices else None,
            low=min(prices) if prices else None,
            current=prices[-1] if prices else None,
            started_at=started_at,
            ended_at=visible_points[-1].timestamp if visible_points else None,
        )

    @staticmethod
    def _daily_bars_need_refresh(latest_trading_date) -> bool:
        from app.domain.market_rules import daily_bars_need_refresh

        return daily_bars_need_refresh(latest_trading_date)
