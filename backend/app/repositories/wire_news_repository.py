from psycopg.types.json import Jsonb

from app.core.database import PostgresDatabase
from app.models.news import NewsItem


class WireNewsRepository:
    def __init__(self, database: PostgresDatabase) -> None:
        self.database = database
        self.database.initialize()
        self._ensure_table()

    def _ensure_table(self) -> None:
        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS wire_news_items (
                        id TEXT PRIMARY KEY,
                        source TEXT NOT NULL,
                        title TEXT NOT NULL,
                        summary TEXT NOT NULL,
                        source_url TEXT,
                        published_at TIMESTAMPTZ,
                        tags JSONB NOT NULL DEFAULT '[]'::jsonb,
                        raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
            connection.commit()

    def upsert_items(self, items: list[NewsItem], raw_payloads: dict[str, dict] | None = None) -> None:
        if not items:
            return

        payload_map = raw_payloads or {}
        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                for item in items:
                    cursor.execute(
                        """
                        INSERT INTO wire_news_items (
                            id,
                            source,
                            title,
                            summary,
                            source_url,
                            published_at,
                            tags,
                            raw_payload
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id)
                        DO UPDATE SET
                            source = EXCLUDED.source,
                            title = EXCLUDED.title,
                            summary = EXCLUDED.summary,
                            source_url = EXCLUDED.source_url,
                            published_at = EXCLUDED.published_at,
                            tags = EXCLUDED.tags,
                            raw_payload = EXCLUDED.raw_payload,
                            updated_at = NOW()
                        """,
                        (
                            item.id,
                            item.source,
                            item.title,
                            item.summary,
                            item.url,
                            item.published_at,
                            Jsonb(item.tags),
                            Jsonb(_json_safe(payload_map.get(item.id, {}))),
                        ),
                    )
            connection.commit()

    def list_recent_items(self, source: str, limit: int) -> list[NewsItem]:
        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        id,
                        source,
                        title,
                        summary,
                        source_url,
                        published_at,
                        tags
                    FROM wire_news_items
                    WHERE source = %s
                    ORDER BY published_at DESC NULLS LAST, updated_at DESC
                    LIMIT %s
                    """,
                    (source, limit),
                )
                rows = cursor.fetchall()

        return [
            NewsItem(
                id=row["id"],
                source=row["source"],
                title=row["title"],
                summary=row["summary"],
                url=row["source_url"],
                published_at=row["published_at"],
                tags=row["tags"] or [],
            )
            for row in rows
        ]


def _json_safe(value):
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except TypeError:
            return str(value)
    return value
