from abc import ABC, abstractmethod

from app.models.market import DailyBar, MarketHistoryPoint, MarketSnapshot, TrackedTicker


class MarketDataProvider(ABC):
    provider_name: str

    @abstractmethod
    async def fetch_snapshot(self, tickers: list[TrackedTicker]) -> MarketSnapshot:
        raise NotImplementedError

    @abstractmethod
    async def fetch_history(
        self,
        ticker: TrackedTicker,
        *,
        period: str,
        interval: str,
    ) -> list[MarketHistoryPoint]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_daily_bars(
        self,
        ticker: TrackedTicker,
        *,
        period: str,
    ) -> list[DailyBar]:
        raise NotImplementedError
