from datetime import datetime

from pydantic import BaseModel, Field


class NewsItem(BaseModel):
    id: str
    source: str
    title: str
    summary: str
    url: str | None = None
    published_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)


class NewsFeedResponse(BaseModel):
    source: str
    fetched_at: datetime
    items: list[NewsItem] = Field(default_factory=list)
