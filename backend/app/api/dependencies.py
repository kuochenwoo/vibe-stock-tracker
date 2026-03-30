from app.core.cache import RedisMarketCache
from app.core.config import get_settings
from app.core.database import PostgresDatabase
from app.providers.factory import MarketDataProviderFactory
from app.repositories.ticker_repository import TickerRepository
from app.services.fear_greed_service import FearGreedService
from app.services.market_poller import MarketPoller
from app.services.market_service import MarketService
from app.services.market_state import MarketStateStore
from app.services.ticker_service import TickerService

settings = get_settings()
state_store = MarketStateStore()
provider = MarketDataProviderFactory.create(settings)
database = PostgresDatabase(settings)
market_cache = RedisMarketCache(settings)
ticker_repository = TickerRepository(database)
ticker_service = TickerService(repository=ticker_repository)
fear_greed_service = FearGreedService()
market_service = MarketService(
    provider=provider,
    state_store=state_store,
    ticker_service=ticker_service,
    cache=market_cache,
)
market_poller = MarketPoller(
    service=market_service,
    interval_seconds=settings.market_poll_interval_seconds,
)
