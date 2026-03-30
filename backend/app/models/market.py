from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MarketQuote(BaseModel):
    code: str
    symbol: str
    name: str
    price: float | None = None
    currency: str = "USD"
    change: float | None = None
    change_percent: float | None = None
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


class MarketSnapshot(BaseModel):
    updated_at: datetime | None = None
    tracked_tickers: list[TrackedTicker] = Field(default_factory=list)
    markets: dict[str, MarketQuote] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
