from datetime import datetime

from pydantic import BaseModel


class FearGreedReading(BaseModel):
    value: int | None = None
    rating: str | None = None


class FearGreedSnapshot(BaseModel):
    value: int | None = None
    rating: str | None = None
    updated_at: datetime | None = None
    source: str = "cnn"
    source_url: str = "https://edition.cnn.com/markets/fear-and-greed"
    previous_close: FearGreedReading | None = None
    one_week_ago: FearGreedReading | None = None
    one_month_ago: FearGreedReading | None = None
    one_year_ago: FearGreedReading | None = None
