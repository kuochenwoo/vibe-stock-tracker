from app.models.market import MovingAverageSnapshot
from app.providers.base import MarketDataProvider
from app.repositories.daily_bar_repository import DailyBarRepository
from app.repositories.ticker_repository import TickerRepository


class MovingAverageService:
    def __init__(
        self,
        provider: MarketDataProvider,
        ticker_repository: TickerRepository,
        daily_bar_repository: DailyBarRepository,
    ) -> None:
        self.provider = provider
        self.ticker_repository = ticker_repository
        self.daily_bar_repository = daily_bar_repository

    async def get_snapshot(self, code: str) -> MovingAverageSnapshot:
        ticker = self._get_ticker(code)
        bars = await self.provider.fetch_daily_bars(ticker, period="2y")
        self.daily_bar_repository.upsert_bars(ticker.code, bars)
        recent_bars = list(reversed(self.daily_bar_repository.list_recent_bars(ticker.code, 60)))
        closes = [bar.close for bar in recent_bars]

        return MovingAverageSnapshot(
            code=ticker.code,
            symbol=ticker.symbol,
            name=ticker.name,
            as_of_date=recent_bars[-1].trading_date if recent_bars else None,
            last_close=recent_bars[-1].close if recent_bars else None,
            sma_20=_simple_moving_average(closes, 20),
            sma_30=_simple_moving_average(closes, 30),
            sma_60=_simple_moving_average(closes, 60),
            bars_loaded=len(recent_bars),
        )

    def _get_ticker(self, code: str):
        lookup = code.strip().upper()
        for ticker in self.ticker_repository.list_all():
            if ticker.code == lookup:
                return ticker
        raise ValueError(f"Ticker code '{lookup}' was not found.")


def _simple_moving_average(closes: list[float], window: int) -> float | None:
    if len(closes) < window:
        return None
    values = closes[-window:]
    return round(sum(values) / window, 6)
