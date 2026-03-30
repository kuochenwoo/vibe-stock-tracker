from abc import ABC, abstractmethod

from app.models.market import MarketHistoryPoint, MarketSnapshot, TrackedTicker


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
