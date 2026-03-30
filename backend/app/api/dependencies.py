from app.core.cache import RedisMarketCache
from app.core.config import get_settings
from app.core.database import PostgresDatabase
from app.models.market import TrackedTicker
from app.providers.factory import MarketDataProviderFactory
from app.repositories.alert_repository import AlertRepository
from app.repositories.daily_bar_repository import DailyBarRepository
from app.repositories.preferences_repository import PreferencesRepository
from app.repositories.ticker_repository import TickerRepository
from app.repositories.truth_social_repository import TruthSocialRepository
from app.services.alert_service import AlertService
from app.services.fear_greed_service import FearGreedService
from app.services.market_poller import MarketPoller
from app.services.market_service import MarketService
from app.services.market_state import MarketStateStore
from app.services.moving_average_service import MovingAverageService
from app.services.preferences_service import PreferencesService
from app.services.ticker_service import TickerService
from app.services.truth_social_service import TruthSocialService

settings = get_settings()
state_store = MarketStateStore()
provider = MarketDataProviderFactory.create(settings)
database = PostgresDatabase(settings)
market_cache = RedisMarketCache(settings)
ticker_repository = TickerRepository(database)
alert_repository = AlertRepository(database)
preferences_repository = PreferencesRepository(database)
daily_bar_repository = DailyBarRepository(database)
truth_social_repository = TruthSocialRepository(database)
ticker_service = TickerService(repository=ticker_repository)
alert_service = AlertService(
    repository=alert_repository,
    ticker_repository=ticker_repository,
)
preferences_service = PreferencesService(
    repository=preferences_repository,
    ticker_repository=ticker_repository,
)
fear_greed_service = FearGreedService()
moving_average_service = MovingAverageService(
    provider=provider,
    ticker_repository=ticker_repository,
    daily_bar_repository=daily_bar_repository,
)
truth_social_service = TruthSocialService(
    feed_url=settings.truth_social_feed_url,
    account_handle=settings.truth_social_account_handle,
    account_url=f"https://truthsocial.com/@{settings.truth_social_account_handle}",
    repository=truth_social_repository,
)
macro_tickers = [
    {
        "code": "VIX",
        "symbol": "^VIX",
        "name": "VIX Index",
    },
    {
        "code": "ES",
        "symbol": "ES=F",
        "name": "S&P 500 Futures",
    },
    {
        "code": "NQ",
        "symbol": "NQ=F",
        "name": "Nasdaq-100 Futures",
    },
]
market_service = MarketService(
    provider=provider,
    state_store=state_store,
    ticker_service=ticker_service,
    cache=market_cache,
    daily_bar_repository=daily_bar_repository,
    macro_tickers=[
        TrackedTicker(
            code=item["code"],
            symbol=item["symbol"],
            name=item["name"],
            provider=settings.market_data_provider,
            metadata={
                "asset_type": "stock" if item["code"] == "VIX" else "futures",
                "session_timezone": "America/New_York" if item["code"] == "VIX" else "America/New_York",
                "session_start": "04:00" if item["code"] == "VIX" else "18:00",
                "macro": True,
            },
        )
        for item in macro_tickers
    ],
)
market_poller = MarketPoller(
    service=market_service,
    interval_seconds=settings.market_poll_interval_seconds,
)
