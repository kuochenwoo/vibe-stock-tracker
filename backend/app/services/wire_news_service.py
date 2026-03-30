from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import html
import json
import re
from xml.etree import ElementTree

import httpx

from app.core.constants import WIRE_NEWS_CACHE_TTL_SECONDS
from app.models.news import NewsFeedResponse, NewsItem
from app.repositories.wire_news_repository import WireNewsRepository

SCRIPT_JSON_RE = re.compile(
    r'<script[^>]+type="application/ld\+json"[^>]*>(?P<json>.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
ARTICLE_RE = re.compile(
    r'"headline":"(?P<headline>[^"]+?)".*?"url":"(?P<url>https:\\/\\/www\.bloomberg\.com\\/[^"]+?)".*?"description":"(?P<description>[^"]*?)"',
    re.DOTALL,
)


class WireNewsService:
    def __init__(
        self,
        *,
        feed_url: str,
        fallback_rss_url: str,
        source_name: str,
        repository: WireNewsRepository,
        cache_ttl_seconds: int = WIRE_NEWS_CACHE_TTL_SECONDS,
    ) -> None:
        self.feed_url = feed_url
        self.fallback_rss_url = fallback_rss_url
        self.source_name = source_name
        self.repository = repository
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self._last_refresh_at: datetime | None = None

    async def get_latest_items(self, limit: int = 10) -> NewsFeedResponse:
        fetch_error: Exception | None = None

        if self._should_refresh():
            try:
                items, raw_payloads = await self._fetch_page_items()
                if items:
                    self.repository.upsert_items(items, raw_payloads)
                self._last_refresh_at = datetime.now(timezone.utc)
            except Exception as exc:  # noqa: BLE001
                fetch_error = exc

        items = self.repository.list_recent_items(self.source_name, limit)
        if not items and fetch_error is not None:
            raise fetch_error

        return NewsFeedResponse(
            source=self.source_name,
            fetched_at=datetime.now(timezone.utc),
            items=items,
        )

    def _should_refresh(self) -> bool:
        if self._last_refresh_at is None:
            return True
        return datetime.now(timezone.utc) - self._last_refresh_at >= self.cache_ttl

    async def _fetch_page_items(self) -> tuple[list[NewsItem], dict[str, dict]]:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(15.0),
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/146.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            },
            follow_redirects=True,
        ) as client:
            response = await client.get(self.feed_url)
            if response.status_code == 403 or _looks_like_robot_challenge(response.text):
                return await self._fetch_rss_items(client)

            response.raise_for_status()
            entries = _extract_articles(response.text)
            if entries:
                return _build_news_items(
                    entries=entries,
                    source_name=self.source_name,
                )
            return await self._fetch_rss_items(client)

    async def _fetch_rss_items(
        self,
        client: httpx.AsyncClient,
    ) -> tuple[list[NewsItem], dict[str, dict]]:
        response = await client.get(self.fallback_rss_url)
        response.raise_for_status()
        return _build_news_items(
            entries=_extract_google_news_rss(response.text),
            source_name=self.source_name,
        )


def _extract_articles(html: str) -> list[dict]:
    items: list[dict] = []
    seen_ids: set[str] = set()

    for match in SCRIPT_JSON_RE.finditer(html):
        block = match.group("json").strip()
        try:
            payload = json.loads(block)
        except Exception:
            continue

        for article in _walk_json_for_articles(payload):
            article_id = article["id"]
            if article_id in seen_ids:
                continue
            seen_ids.add(article_id)
            items.append(article)

    if items:
        return items

    for match in ARTICLE_RE.finditer(html):
        url = match.group("url").replace("\\/", "/")
        title = _decode_text(match.group("headline"))
        summary = _decode_text(match.group("description"))
        article_id = url
        if article_id in seen_ids:
            continue
        seen_ids.add(article_id)
        items.append(
            {
                "id": article_id,
                "title": title,
                "summary": summary or title,
                "url": url,
                "published_at": None,
            }
        )

    return items


def _extract_google_news_rss(xml_text: str) -> list[dict]:
    root = ElementTree.fromstring(xml_text)
    items: list[dict] = []
    channel = root.find("channel")
    if channel is None:
        return items

    for node in channel.findall("item"):
        title = _normalize_rss_title(node.findtext("title"))
        link = (node.findtext("link") or "").strip()
        guid = (node.findtext("guid") or link).strip()
        description = _extract_description_text(node.findtext("description"))
        if not title or not link:
            continue
        items.append(
            {
                "id": guid or link,
                "title": title,
                "summary": description or title,
                "url": link,
                "published_at": _parse_rfc2822_datetime(node.findtext("pubDate")),
            }
        )

    return items


def _walk_json_for_articles(payload) -> list[dict]:
    articles: list[dict] = []

    def visit(node) -> None:
        if isinstance(node, dict):
            node_type = node.get("@type") or node.get("type")
            if node_type in {"NewsArticle", "Article"} and node.get("headline") and node.get("url"):
                title = _normalize_text(node.get("headline", ""))
                summary = _normalize_text(node.get("description", "")) or title
                articles.append(
                    {
                        "id": node.get("url"),
                        "title": title,
                        "summary": summary,
                        "url": node.get("url"),
                        "published_at": _parse_datetime(node.get("datePublished")),
                    }
                )
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(payload)
    return articles


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _decode_text(value: str) -> str:
    return _normalize_text(bytes(value, "utf-8").decode("unicode_escape"))


def _normalize_rss_title(value: str | None) -> str:
    if not value:
        return ""
    title = html.unescape(value)
    return _normalize_text(re.sub(r"\s+-\s+Bloomberg\.com$", "", title))


def _extract_description_text(value: str | None) -> str:
    if not value:
        return ""
    decoded = html.unescape(value)
    stripped = re.sub(r"<[^>]+>", " ", decoded)
    stripped = stripped.replace("\xa0", " ")
    stripped = re.sub(r"\s+", " ", stripped)
    stripped = re.sub(r"\s*Bloomberg\.com\s*$", "", stripped, flags=re.IGNORECASE)
    return stripped.strip()


def _parse_rfc2822_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _build_news_items(
    *,
    entries: list[dict],
    source_name: str,
) -> tuple[list[NewsItem], dict[str, dict]]:
    fetched_at = datetime.now(timezone.utc)
    items: list[NewsItem] = []
    raw_payloads: dict[str, dict] = {}

    for index, entry in enumerate(entries[:25]):
        item = NewsItem(
            id=entry["id"],
            source=source_name,
            title=entry["title"],
            summary=entry["summary"],
            url=entry["url"],
            published_at=entry["published_at"] or (fetched_at - timedelta(minutes=index)),
            tags=_extract_tags(f"{entry['title']} {entry['summary']}"),
        )
        items.append(item)
        raw_payloads[item.id] = entry

    if not items:
        raise ValueError("No Bloomberg wire items could be extracted from the configured sources.")

    return items, raw_payloads


def _looks_like_robot_challenge(page_text: str) -> bool:
    lowered = page_text.lower()
    return "are you a robot?" in lowered or "bloomberg - are you a robot?" in lowered


def _extract_tags(text: str) -> list[str]:
    keywords = {
        "market": "#Markets",
        "stocks": "#Stocks",
        "oil": "#Oil",
        "gold": "#Gold",
        "fed": "#Fed",
        "china": "#China",
        "treasury": "#Rates",
        "nasdaq": "#Nasdaq",
        "s&p": "#SPX",
        "bitcoin": "#Bitcoin",
    }
    lowered = text.lower()
    tags = [tag for keyword, tag in keywords.items() if keyword in lowered]
    return tags[:4]
