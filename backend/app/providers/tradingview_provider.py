from app.models.market import MarketSnapshot, TrackedTicker
from app.providers.base import MarketDataProvider


class TradingViewMarketDataProvider(MarketDataProvider):
    provider_name = "tradingview"

    async def fetch_snapshot(self, tickers: list[TrackedTicker]) -> MarketSnapshot:
        raise NotImplementedError(
            "TradingView provider is not implemented yet. "
            "Set MARKET_DATA_PROVIDER=mock or MARKET_DATA_PROVIDER=yfinance for now."
        )
