from datetime import datetime, timezone

from app.models.market import MarketSnapshot
from app.providers.base import MarketDataProvider
from app.services.market_state import MarketStateStore
from app.services.ticker_service import TickerService


class MarketService:
    def __init__(
        self,
        provider: MarketDataProvider,
        state_store: MarketStateStore,
        ticker_service: TickerService,
    ) -> None:
        self.provider = provider
        self.state_store = state_store
        self.ticker_service = ticker_service

    async def refresh_snapshot(self) -> MarketSnapshot:
        tickers = self.ticker_service.list_tickers()
        try:
            snapshot = await self.provider.fetch_snapshot(tickers)
        except Exception as exc:  # noqa: BLE001
            previous = await self.state_store.get_snapshot()
            snapshot = MarketSnapshot(
                updated_at=datetime.now(timezone.utc),
                tracked_tickers=tickers,
                markets=previous.markets,
                errors=[f"{type(exc).__name__}: {exc}"],
            )

        await self.state_store.set_snapshot(snapshot)
        await self.state_store.broadcast(snapshot)
        return snapshot

    async def get_snapshot(self) -> MarketSnapshot:
        return await self.state_store.get_snapshot()
