from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
import re
from urllib.parse import urljoin
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

import httpx

from app.core.constants import (
    TRUTH_SOCIAL_ACTIVE_END,
    TRUTH_SOCIAL_ACTIVE_REFRESH_MINUTES,
    TRUTH_SOCIAL_ACTIVE_START,
    TRUTH_SOCIAL_FETCH_FLOOR,
    TRUTH_SOCIAL_IDLE_REFRESH_MINUTES,
    TRUTH_SOCIAL_SUMMARY_LIMIT,
)
from app.models.social import SocialFeedResponse, SocialPost
from app.repositories.truth_social_repository import TruthSocialRepository

HTML_TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")


class TruthSocialService:
    def __init__(
        self,
        *,
        feed_url: str,
        account_handle: str,
        account_url: str,
        repository: TruthSocialRepository,
    ) -> None:
        self.feed_url = feed_url
        self.account_handle = account_handle
        self.account_url = account_url
        self.repository = repository
        self._last_refresh_at: datetime | None = None

    async def get_latest_posts(self, limit: int = 10) -> SocialFeedResponse:
        fetch_error: Exception | None = None

        if self._should_refresh():
            try:
                posts, raw_payloads = await self._fetch_feed_posts(limit=max(limit, TRUTH_SOCIAL_FETCH_FLOOR))
                if posts:
                    self.repository.upsert_posts(self.account_handle, posts, raw_payloads)
                self._last_refresh_at = datetime.now(timezone.utc)
            except Exception as exc:  # noqa: BLE001
                fetch_error = exc

        items = self.repository.list_recent_posts(self.account_handle, limit)
        if not items and fetch_error is not None:
            raise fetch_error

        return SocialFeedResponse(
            account=self.account_handle,
            fetched_at=datetime.now(timezone.utc),
            items=items,
        )

    def _should_refresh(self) -> bool:
        if self._last_refresh_at is None:
            return True

        now = datetime.now(timezone.utc)
        refresh_interval = _current_refresh_interval(now)
        return now - self._last_refresh_at >= refresh_interval

    async def _fetch_feed_posts(self, limit: int) -> tuple[list[SocialPost], dict[str, dict]]:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(15.0),
            headers={"User-Agent": "market-alerts-truth-social/1.0"},
            follow_redirects=True,
        ) as client:
            response = await client.get(self.feed_url)
            response.raise_for_status()

        root = ET.fromstring(response.text)
        channel = root.find("channel")
        if channel is None:
            raise ValueError("Truth Social feed returned an unexpected RSS payload.")

        posts: list[SocialPost] = []
        raw_payloads: dict[str, dict] = {}
        for item in channel.findall("item")[:limit]:
            post = self._normalize_item(item)
            posts.append(post)
            raw_payloads[post.id] = {
                "title": item.findtext("title"),
                "description": item.findtext("description"),
                "link": item.findtext("link"),
                "guid": item.findtext("guid"),
                "pubDate": item.findtext("pubDate"),
            }

        return posts, raw_payloads

    def _normalize_item(self, item: ET.Element) -> SocialPost:
        guid = (item.findtext("guid") or item.findtext("link") or item.findtext("title") or "").strip()
        title_text = (item.findtext("title") or "").strip()
        description_html = item.findtext("description") or ""
        summary_text = _strip_html(description_html)
        normalized_title, normalized_summary = _build_title_and_summary(title_text, summary_text)
        link = item.findtext("link")
        published_at = _parse_rss_datetime(item.findtext("pubDate"))

        return SocialPost(
            id=guid,
            title=normalized_title,
            summary=normalized_summary,
            published_at=published_at,
            url=urljoin(self.account_url + "/", link) if link else self.account_url,
            author=self.account_handle,
            tags=_extract_tags(f"{normalized_title} {normalized_summary}"),
        )


def _strip_html(value: str) -> str:
    text = HTML_TAG_RE.sub(" ", value)
    text = unescape(text)
    return WHITESPACE_RE.sub(" ", text).strip()


def _build_title_and_summary(title: str, summary: str) -> tuple[str, str]:
    base = summary or title or "Truth Social post"
    normalized = base.strip()
    if len(normalized) <= 110:
        return normalized, normalized

    split_index = normalized.find(". ")
    if 20 <= split_index <= 110:
        first_sentence = normalized[: split_index + 1].strip()
        remainder = normalized[split_index + 1 :].strip()
        return first_sentence, _summarize_text(remainder or first_sentence)

    return normalized[:110].rstrip() + "...", _summarize_text(normalized)


def _parse_rss_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = parsedate_to_datetime(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _extract_tags(text: str) -> list[str]:
    tags: list[str] = []
    keywords = {
        "tariff": "#Tariffs",
        "fed": "#Fed",
        "market": "#Markets",
        "oil": "#Oil",
        "border": "#Border",
        "china": "#China",
        "stock": "#Stocks",
    }
    lowered = text.lower()
    for keyword, tag in keywords.items():
        if keyword in lowered:
            tags.append(tag)
    return tags[:4]


def _summarize_text(text: str, limit: int = TRUTH_SOCIAL_SUMMARY_LIMIT) -> str:
    normalized = WHITESPACE_RE.sub(" ", text).strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."


def _current_refresh_interval(now_utc: datetime) -> timedelta:
    ny = now_utc.astimezone(ZoneInfo("America/New_York"))
    is_weekday = ny.weekday() < 5
    if is_weekday and TRUTH_SOCIAL_ACTIVE_START <= ny.time() <= TRUTH_SOCIAL_ACTIVE_END:
        return timedelta(minutes=TRUTH_SOCIAL_ACTIVE_REFRESH_MINUTES)
    return timedelta(minutes=TRUTH_SOCIAL_IDLE_REFRESH_MINUTES)
