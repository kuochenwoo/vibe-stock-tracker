from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import DEFAULT_MARKET_POLL_INTERVAL_SECONDS


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "Market Alerts API"
    data_dir: Path = Path("data")
    cors_allow_origins: list[str] = Field(
        default_factory=lambda: ["http://127.0.0.1:5173", "http://localhost:5173"]
    )
    cors_allow_origin_regex: str = (
        r"https?://("
        r"localhost|127\.0\.0\.1|0\.0\.0\.0|"
        r"10(?:\.\d{1,3}){3}|"
        r"192\.168(?:\.\d{1,3}){2}|"
        r"172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2}"
        r")(?::\d+)?$"
    )
    market_poll_interval_seconds: int = DEFAULT_MARKET_POLL_INTERVAL_SECONDS
    market_data_provider: str = "yfinance"
    postgres_dsn: str = "postgresql://market_alerts:market_alerts@localhost:5432/market_alerts"
    postgres_schema_path: Path = Path("../infra/postgres/init/001_market_schema.sql")
    redis_url: str = "redis://localhost:6379/0"
    wire_news_feed_url: str = "https://www.bloomberg.com/latest?utm_source=homepage&utm_medium=web&utm_campaign=latest"
    wire_news_fallback_rss_url: str = (
        "https://news.google.com/rss/search?q=site:bloomberg.com&hl=en-US&gl=US&ceid=US:en"
    )
    wire_news_source_name: str = "Bloomberg"
    truth_social_feed_url: str = "https://www.trumpstruth.org/feed"
    truth_social_account_handle: str = "realDonaldTrump"


@lru_cache
def get_settings() -> Settings:
    return Settings()
