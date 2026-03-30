from datetime import UTC, datetime
from typing import Any

import httpx

from app.models.sentiment import FearGreedReading, FearGreedSnapshot


class FearGreedService:
    graph_url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    page_url = "https://edition.cnn.com/markets/fear-and-greed"

    async def fetch_snapshot(self) -> FearGreedSnapshot:
        async with httpx.AsyncClient(
            timeout=10.0,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/136.0.0.0 Safari/537.36"
                )
            },
        ) as client:
            response = await client.get(self.graph_url)
            response.raise_for_status()
            payload = response.json()

        current = payload.get("fear_and_greed") or {}

        return FearGreedSnapshot(
            value=self._coerce_score(current.get("score")),
            rating=self._coerce_rating(current.get("rating"), current.get("score")),
            updated_at=self._coerce_datetime(
                current.get("timestamp")
                or current.get("updated")
                or current.get("last_updated")
                or payload.get("timestamp")
            ),
            source_url=self.page_url,
            previous_close=self._coerce_reading(current.get("previous_close")),
            one_week_ago=self._coerce_reading(
                current.get("previous_1_week") or current.get("one_week_ago")
            ),
            one_month_ago=self._coerce_reading(
                current.get("previous_1_month") or current.get("one_month_ago")
            ),
            one_year_ago=self._coerce_reading(
                current.get("previous_1_year") or current.get("one_year_ago")
            ),
        )

    def _coerce_reading(self, value: Any) -> FearGreedReading | None:
        if isinstance(value, dict):
            score = self._coerce_score(value.get("score"))
            rating = self._coerce_rating(value.get("rating"), value.get("score"))
        else:
            score = self._coerce_score(value)
            rating = self._coerce_rating(None, value)

        if score is None and rating is None:
            return None

        return FearGreedReading(value=score, rating=rating)

    def _coerce_score(self, value: Any) -> int | None:
        if value is None:
            return None

        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None

        try:
            score = int(round(float(value)))
        except (TypeError, ValueError):
            return None

        return max(0, min(score, 100))

    def _coerce_rating(self, rating: Any, fallback_score: Any) -> str | None:
        if isinstance(rating, str) and rating.strip():
            return rating.strip().title()

        score = self._coerce_score(fallback_score)
        if score is None:
            return None

        if score <= 24:
            return "Extreme Fear"
        if score <= 44:
            return "Fear"
        if score <= 55:
            return "Neutral"
        if score <= 75:
            return "Greed"
        return "Extreme Greed"

    def _coerce_datetime(self, value: Any) -> datetime | None:
        if isinstance(value, (int, float)):
            timestamp = float(value)
            if timestamp > 1_000_000_000_000:
                timestamp /= 1000
            return datetime.fromtimestamp(timestamp, tz=UTC)

        if isinstance(value, str) and value.strip():
            parsed = value.strip().replace("Z", "+00:00")
            try:
                dt = datetime.fromisoformat(parsed)
            except ValueError:
                return None

            if dt.tzinfo is None:
                return dt.replace(tzinfo=UTC)
            return dt

        return None
