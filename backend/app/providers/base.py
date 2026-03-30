from abc import ABC, abstractmethod

from app.models.market import MarketSnapshot, TrackedTicker


class MarketDataProvider(ABC):
    provider_name: str

    @abstractmethod
    async def fetch_snapshot(self, tickers: list[TrackedTicker]) -> MarketSnapshot:
        raise NotImplementedError
