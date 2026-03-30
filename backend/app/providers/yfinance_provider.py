import asyncio
from datetime import datetime, timezone

import yfinance as yf

from app.core.config import Settings
from app.models.market import DailyBar, MarketHistoryPoint, MarketQuote, MarketSnapshot, TrackedTicker
from app.providers.base import MarketDataProvider


class YFinanceMarketDataProvider(MarketDataProvider):
    provider_name = "yfinance"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def fetch_snapshot(self, tickers: list[TrackedTicker]) -> MarketSnapshot:
        markets: dict[str, MarketQuote] = {}
        errors: list[str] = []

        for ticker in tickers:
            try:
                quote = await asyncio.to_thread(self._fetch_quote, ticker)
                markets[ticker.code] = quote
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{ticker.code}: {type(exc).__name__}: {exc}")

        return MarketSnapshot(
            updated_at=datetime.now(timezone.utc),
            tracked_tickers=tickers,
            markets=markets,
            errors=errors,
        )

    async def fetch_history(
        self,
        ticker: TrackedTicker,
        *,
        period: str,
        interval: str,
    ) -> list[MarketHistoryPoint]:
        return await asyncio.to_thread(
            self._fetch_history,
            ticker,
            period,
            interval,
        )

    async def fetch_daily_bars(
        self,
        ticker: TrackedTicker,
        *,
        period: str,
    ) -> list[DailyBar]:
        return await asyncio.to_thread(
            self._fetch_daily_bars,
            ticker,
            period,
        )

    def _fetch_quote(self, ticker: TrackedTicker) -> MarketQuote:
        instrument = yf.Ticker(ticker.symbol)
        history = instrument.history(
            period="2d",
            interval="1m",
            auto_adjust=False,
            prepost=True,
        )
        if history.empty:
            history = instrument.history(
                period="5d",
                interval="5m",
                auto_adjust=False,
                prepost=True,
            )
        if history.empty:
            raise ValueError(f"No market data returned for {ticker.symbol}")

        latest_row = history.dropna(subset=["Close"]).iloc[-1]
        daily_history = instrument.history(
            period="10d",
            interval="1d",
            auto_adjust=False,
            prepost=False,
        )
        history_5m = instrument.history(
            period="5d",
            interval="5m",
            auto_adjust=False,
            prepost=True,
        )
        prev_5m_close, prev_5m_closed_at = self._resolve_previous_5m_close(history_5m)
        previous_close = self._resolve_previous_close(daily_history, latest_row)
        price = float(latest_row["Close"])
        change = price - previous_close if previous_close is not None else None
        change_percent = (
            ((change / previous_close) * 100)
            if change is not None and previous_close not in (None, 0)
            else None
        )
        five_min_change = price - prev_5m_close if prev_5m_close is not None else None
        five_min_change_percent = (
            ((five_min_change / prev_5m_close) * 100)
            if five_min_change is not None and prev_5m_close not in (None, 0)
            else None
        )

        return MarketQuote(
            code=ticker.code,
            symbol=ticker.symbol,
            name=ticker.name,
            price=price,
            currency="USD",
            change=change,
            change_percent=change_percent,
            five_min_change=five_min_change,
            five_min_change_percent=five_min_change_percent,
            previous_close=previous_close,
            market_state="LIVE",
            source=self.provider_name,
            metadata={
                "last_bar_time": latest_row.name.to_pydatetime()
                .astimezone(timezone.utc)
                .isoformat(),
                "requested_symbol": ticker.symbol,
                "prev_5m_close": prev_5m_close,
                "prev_5m_bar_closed_at": prev_5m_closed_at,
            },
        )

    def _fetch_history(
        self,
        ticker: TrackedTicker,
        period: str,
        interval: str,
    ) -> list[MarketHistoryPoint]:
        instrument = yf.Ticker(ticker.symbol)
        history = instrument.history(
            period=period,
            interval=interval,
            auto_adjust=False,
            prepost=True,
        )
        closes = history["Close"].dropna()
        if closes.empty:
            raise ValueError(f"No history returned for {ticker.symbol}")

        points: list[MarketHistoryPoint] = []
        for timestamp, close in closes.items():
            points.append(
                MarketHistoryPoint(
                    timestamp=timestamp.to_pydatetime().astimezone(timezone.utc),
                    price=float(close),
                )
            )

        return points

    def _fetch_daily_bars(
        self,
        ticker: TrackedTicker,
        period: str,
    ) -> list[DailyBar]:
        instrument = yf.Ticker(ticker.symbol)
        history = instrument.history(
            period=period,
            interval="1d",
            auto_adjust=False,
            prepost=False,
        )
        rows = history.dropna(subset=["Open", "High", "Low", "Close"])
        if rows.empty:
            raise ValueError(f"No daily bars returned for {ticker.symbol}")

        bars: list[DailyBar] = []
        for timestamp, row in rows.iterrows():
            bars.append(
                DailyBar(
                    trading_date=timestamp.date(),
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=float(row["Volume"]) if "Volume" in row and row["Volume"] == row["Volume"] else None,
                    source=self.provider_name,
                )
            )

        return bars

    @staticmethod
    def _resolve_previous_close(history, latest_row) -> float | None:
        closes = history["Close"].dropna()
        if closes.empty:
            return None
        if len(closes) == 1:
            return float(closes.iloc[0])

        latest_date = latest_row.name.date()
        most_recent_daily_date = closes.index[-1].date()

        if latest_date == most_recent_daily_date:
            return float(closes.iloc[-2])

        return float(closes.iloc[-1])

    @staticmethod
    def _resolve_previous_5m_close(history) -> tuple[float | None, str | None]:
        closes = history["Close"].dropna()
        if closes.empty:
            return None, None
        close_row = closes.iloc[-2] if len(closes) > 1 else closes.iloc[-1]
        close_time = closes.index[-2] if len(closes) > 1 else closes.index[-1]
        return float(close_row), close_time.to_pydatetime().astimezone(timezone.utc).isoformat()
