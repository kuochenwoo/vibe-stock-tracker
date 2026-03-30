from datetime import datetime, timedelta, timezone

from app.models.market import DailyBar, MarketHistoryPoint, MarketQuote, MarketSnapshot, TrackedTicker
from app.providers.base import MarketDataProvider


class MockMarketDataProvider(MarketDataProvider):
    provider_name = "mock"

    async def fetch_snapshot(self, tickers: list[TrackedTicker]) -> MarketSnapshot:
        markets = {}
        for ticker in tickers:
            base_price = 68.42 if ticker.code == "CL" else 3087.14
            base_change = 0.57 if ticker.code == "CL" else -4.18
            base_close = 67.85 if ticker.code == "CL" else 3091.32
            prev_5m_close = round(base_price - 0.12, 2)
            five_min_change = round(base_price - prev_5m_close, 2)
            markets[ticker.code] = MarketQuote(
                code=ticker.code,
                symbol=ticker.symbol,
                name=ticker.name,
                price=base_price,
                currency="USD",
                change=base_change,
                change_percent=(base_change / base_close) * 100,
                five_min_change=five_min_change,
                five_min_change_percent=(five_min_change / prev_5m_close) * 100,
                previous_close=base_close,
                market_state="SIMULATED",
                source=self.provider_name,
                metadata={
                    "last_bar_time": datetime.now(timezone.utc).isoformat(),
                    "prev_5m_close": prev_5m_close,
                    "prev_5m_bar_closed_at": datetime.now(timezone.utc).isoformat(),
                },
            )

        return MarketSnapshot(
            updated_at=datetime.now(timezone.utc),
            tracked_tickers=tickers,
            markets=markets,
            errors=[],
        )

    async def fetch_history(
        self,
        ticker: TrackedTicker,
        *,
        period: str,
        interval: str,
    ) -> list[MarketHistoryPoint]:
        now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        base_price = 68.42 if ticker.code == "CL" else 3087.14
        points: list[MarketHistoryPoint] = []

        for index in range(78):
            timestamp = now - timedelta(minutes=(77 - index) * 5)
            wave = ((index % 12) - 6) * 0.18
            points.append(
                MarketHistoryPoint(
                    timestamp=timestamp,
                    price=round(base_price + wave, 2),
                )
            )

        return points

    async def fetch_daily_bars(
        self,
        ticker: TrackedTicker,
        *,
        period: str,
    ) -> list[DailyBar]:
        today = datetime.now(timezone.utc).date()
        base_price = 68.42 if ticker.code == "CL" else 3087.14
        bars: list[DailyBar] = []

        for index in range(180):
            trading_date = today - timedelta(days=179 - index)
            close = round(base_price + ((index % 14) - 7) * 0.24, 2)
            bars.append(
                DailyBar(
                    trading_date=trading_date,
                    open=round(close - 0.31, 2),
                    high=round(close + 0.55, 2),
                    low=round(close - 0.62, 2),
                    close=close,
                    volume=100000 + index * 250,
                    source=self.provider_name,
                )
            )

        return bars
