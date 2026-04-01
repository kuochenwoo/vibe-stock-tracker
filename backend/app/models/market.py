from datetime import date, datetime
from typing import Annotated, Any, Literal

from fastapi import Query
from pydantic import BaseModel, Field

from app.core.constants import (
    MARKET_HISTORY_DEFAULT_RANGE,
    MARKET_HISTORY_YEAR_RANGE,
    TRUTH_SOCIAL_DEFAULT_LIMIT,
    TRUTH_SOCIAL_MAX_LIMIT,
    WIRE_NEWS_DEFAULT_LIMIT,
    WIRE_NEWS_MAX_LIMIT,
)


class MarketQuote(BaseModel):
    code: str
    symbol: str
    name: str
    price: float | None = None
    currency: str = "USD"
    change: float | None = None
    change_percent: float | None = None
    five_min_change: float | None = None
    five_min_change_percent: float | None = None
    previous_close: float | None = None
    market_state: str = "UNKNOWN"
    source: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class TrackedTicker(BaseModel):
    code: str
    symbol: str
    name: str
    provider: str = "yfinance"
    aliases: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CreateTrackedTickerRequest(BaseModel):
    code: str
    symbol: str
    name: str
    provider: str = "yfinance"
    aliases: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PanelOrderPreference(BaseModel):
    codes: list[str] = Field(default_factory=list)
    updated_at: datetime | None = None


class UpdatePanelOrderPreferenceRequest(BaseModel):
    codes: list[str] = Field(default_factory=list)


class AlertHistoryReadPreference(BaseModel):
    last_read_triggered_at: datetime | None = None
    updated_at: datetime | None = None


class UpdateAlertHistoryReadRequest(BaseModel):
    last_read_triggered_at: datetime


class AlertRule(BaseModel):
    id: str
    market: str
    direction: str
    value: float
    enabled: bool = True
    created_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CreateAlertRuleRequest(BaseModel):
    market: str
    direction: str
    value: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class AlertHistoryItem(BaseModel):
    id: str
    alert_rule_id: str | None = None
    market: str
    direction: str
    threshold: float
    price: float
    triggered_at: datetime


class CreateAlertHistoryRequest(BaseModel):
    alert_rule_id: str | None = None
    market: str
    direction: str
    threshold: float
    price: float


class MarketHistoryPoint(BaseModel):
    timestamp: datetime
    price: float


class DailyBar(BaseModel):
    trading_date: date
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None
    source: str


class MovingAverageSnapshot(BaseModel):
    code: str
    symbol: str
    name: str
    as_of_date: date | None = None
    last_close: float | None = None
    sma_20: float | None = None
    sma_30: float | None = None
    sma_60: float | None = None
    bars_loaded: int = 0


class MarketHistoryResponse(BaseModel):
    code: str
    symbol: str
    name: str
    range: str = "1d"
    interval: str = "5m"
    asset_type: str
    session_timezone: str
    session_start: str
    points: list[MarketHistoryPoint] = Field(default_factory=list)
    high: float | None = None
    low: float | None = None
    current: float | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None


class MarketHistoryQuery(BaseModel):
    range: Literal["1d", "1y"] = MARKET_HISTORY_DEFAULT_RANGE


WireNewsLimitQuery = Annotated[int, Query(ge=1, le=WIRE_NEWS_MAX_LIMIT)]
TruthSocialLimitQuery = Annotated[int, Query(ge=1, le=TRUTH_SOCIAL_MAX_LIMIT)]


class MarketSnapshot(BaseModel):
    updated_at: datetime | None = None
    tracked_tickers: list[TrackedTicker] = Field(default_factory=list)
    macro_tickers: list[TrackedTicker] = Field(default_factory=list)
    markets: dict[str, MarketQuote] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
