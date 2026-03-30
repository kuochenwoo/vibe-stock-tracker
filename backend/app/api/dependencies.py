from app.core.config import get_settings
from app.providers.factory import MarketDataProviderFactory
from app.repositories.ticker_repository import TickerRepository
from app.services.market_poller import MarketPoller
from app.services.market_service import MarketService
from app.services.market_state import MarketStateStore
from app.services.ticker_service import TickerService

settings = get_settings()
state_store = MarketStateStore()
provider = MarketDataProviderFactory.create(settings)
ticker_repository = TickerRepository(settings.data_dir / "tracked_tickers.json")
ticker_service = TickerService(repository=ticker_repository)
market_service = MarketService(
    provider=provider,
    state_store=state_store,
    ticker_service=ticker_service,
)
market_poller = MarketPoller(
    service=market_service,
    interval_seconds=settings.market_poll_interval_seconds,
)
