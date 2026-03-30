from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    market_poll_interval_seconds: int = 5
    market_data_provider: str = "yfinance"


@lru_cache
def get_settings() -> Settings:
    return Settings()
