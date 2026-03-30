from app.core.config import Settings
from app.providers.base import MarketDataProvider
from app.providers.mock_provider import MockMarketDataProvider
from app.providers.tradingview_provider import TradingViewMarketDataProvider
from app.providers.yfinance_provider import YFinanceMarketDataProvider


class MarketDataProviderFactory:
    @staticmethod
    def create(settings: Settings) -> MarketDataProvider:
        provider = settings.market_data_provider.lower()

        if provider == "yfinance":
            return YFinanceMarketDataProvider(settings)
        if provider == "mock":
            return MockMarketDataProvider()
        if provider == "tradingview":
            return TradingViewMarketDataProvider()

        raise ValueError(
            f"Unsupported market data provider '{settings.market_data_provider}'. "
            "Supported providers: yfinance, mock, tradingview."
        )
