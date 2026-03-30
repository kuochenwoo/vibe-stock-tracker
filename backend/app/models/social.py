from datetime import datetime

from pydantic import BaseModel, Field


class SocialPost(BaseModel):
    id: str
    source: str = "Truth Social"
    published_at: datetime | None = None
    title: str
    summary: str
    url: str | None = None
    author: str | None = None
    tags: list[str] = Field(default_factory=list)


class SocialFeedResponse(BaseModel):
    source: str = "truth_social"
    account: str
    fetched_at: datetime
    items: list[SocialPost] = Field(default_factory=list)
