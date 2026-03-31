from __future__ import annotations

from datetime import date
from typing import Protocol

from app.models.market import DailyBar, TrackedTicker


class TickerRepositoryProtocol(Protocol):
    def list_all(self) -> list[TrackedTicker]:
        ...


class DailyBarRepositoryProtocol(Protocol):
    def upsert_bars(self, ticker_code: str, bars: list[DailyBar]) -> None:
        ...

    def get_latest_trading_date(self, ticker_code: str) -> date | None:
        ...

    def list_recent_bars(self, ticker_code: str, limit: int) -> list[DailyBar]:
        ...
