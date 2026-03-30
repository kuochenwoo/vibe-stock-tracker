from datetime import datetime, timezone

from app.models.market import MarketQuote, MarketSnapshot, TrackedTicker
from app.providers.base import MarketDataProvider


class MockMarketDataProvider(MarketDataProvider):
    provider_name = "mock"

    async def fetch_snapshot(self, tickers: list[TrackedTicker]) -> MarketSnapshot:
        markets = {}
        for ticker in tickers:
            base_price = 68.42 if ticker.code == "CL" else 3087.14
            base_change = 0.57 if ticker.code == "CL" else -4.18
            base_close = 67.85 if ticker.code == "CL" else 3091.32
            markets[ticker.code] = MarketQuote(
                code=ticker.code,
                symbol=ticker.symbol,
                name=ticker.name,
                price=base_price,
                currency="USD",
                change=base_change,
                change_percent=(base_change / base_close) * 100,
                previous_close=base_close,
                market_state="SIMULATED",
                source=self.provider_name,
            )

        return MarketSnapshot(
            updated_at=datetime.now(timezone.utc),
            tracked_tickers=tickers,
            markets=markets,
            errors=[],
        )
