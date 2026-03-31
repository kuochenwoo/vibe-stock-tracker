from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from app.core.constants import (
    ASSET_TYPE_CRYPTO,
    CRYPTO_SYMBOL_SUFFIXES,
    DAILY_BAR_REFRESH_LAG_DAYS,
    DEFAULT_SESSION_START_BY_ASSET,
    DEFAULT_SESSION_TIMEZONE_BY_ASSET,
    FUTURES_SYMBOL_SUFFIX,
    MARKET_HISTORY_INTRADAY_FRESH_MINUTES,
    MARKET_HISTORY_YEAR_FRESH_DAYS,
    MARKET_HISTORY_YEAR_RANGE,
)
from app.models.market import MarketHistoryResponse, TrackedTicker


class TickerSessionProfile(BaseModel):
    asset_type: str
    session_timezone: str
    session_start: str


def resolve_session_profile(ticker: TrackedTicker) -> TickerSessionProfile:
    metadata = ticker.metadata or {}
    asset_type = str(metadata.get("asset_type") or infer_asset_type(ticker.symbol)).lower()
    timezone_name = str(metadata.get("session_timezone") or default_timezone(asset_type))
    session_start = str(metadata.get("session_start") or default_session_start(asset_type))
    return TickerSessionProfile(
        asset_type=asset_type,
        session_timezone=timezone_name,
        session_start=session_start,
    )


def infer_asset_type(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if normalized.endswith(FUTURES_SYMBOL_SUFFIX):
        return "futures"
    if normalized.endswith(CRYPTO_SYMBOL_SUFFIXES):
        return ASSET_TYPE_CRYPTO
    return "stock"


def default_timezone(asset_type: str) -> str:
    return DEFAULT_SESSION_TIMEZONE_BY_ASSET.get(asset_type, "America/New_York")


def default_session_start(asset_type: str) -> str:
    return DEFAULT_SESSION_START_BY_ASSET.get(asset_type, "04:00")


def parse_session_start(value: str) -> time:
    hour_text, minute_text = value.split(":", maxsplit=1)
    return time(hour=int(hour_text), minute=int(minute_text))


def latest_session_start(current: datetime, session_start: time) -> datetime:
    anchored = current.replace(
        hour=session_start.hour,
        minute=session_start.minute,
        second=0,
        microsecond=0,
    )
    if current < anchored:
        anchored -= timedelta(days=1)
    return anchored


def history_is_fresh(history: MarketHistoryResponse) -> bool:
    if history.ended_at is None:
        return False
    if history.range == MARKET_HISTORY_YEAR_RANGE:
        return history.ended_at.date() >= (
            datetime.now(timezone.utc).date() - timedelta(days=MARKET_HISTORY_YEAR_FRESH_DAYS)
        )
    return datetime.now(timezone.utc) - history.ended_at <= timedelta(
        minutes=MARKET_HISTORY_INTRADAY_FRESH_MINUTES
    )


def daily_bars_need_refresh(latest_trading_date: date | None) -> bool:
    if latest_trading_date is None:
        return True
    return latest_trading_date < (
        datetime.now(timezone.utc).date() - timedelta(days=DAILY_BAR_REFRESH_LAG_DAYS)
    )


def session_started_utc(profile: TickerSessionProfile, anchor: datetime) -> datetime:
    zone = ZoneInfo(profile.session_timezone)
    start_time = parse_session_start(profile.session_start)
    return latest_session_start(anchor.astimezone(zone), start_time).astimezone(timezone.utc)
