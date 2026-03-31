from datetime import datetime, timezone

from app.models.market import MarketSnapshot, TrackedTicker
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

    async def get_snapshot(self) -> MarketSnapshot:
        return await self.state_store.get_snapshot()


def _merge_tickers(primary: list[TrackedTicker], secondary: list[TrackedTicker]) -> list[TrackedTicker]:
    merged: dict[str, TrackedTicker] = {ticker.code: ticker for ticker in primary}
    for ticker in secondary:
        merged.setdefault(ticker.code, ticker)
    return list(merged.values())
