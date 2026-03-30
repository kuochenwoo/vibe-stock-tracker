from psycopg.types.json import Jsonb

from app.core.database import PostgresDatabase
from app.models.social import SocialPost


class TruthSocialRepository:
    def __init__(self, database: PostgresDatabase) -> None:
        self.database = database
        self.database.initialize()
        self._ensure_table()

    def _ensure_table(self) -> None:
        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS truth_social_posts (
                        id TEXT PRIMARY KEY,
                        author_handle TEXT NOT NULL,
                        author_display_name TEXT,
                        source_url TEXT,
                        title TEXT NOT NULL,
                        summary TEXT NOT NULL,
                        published_at TIMESTAMPTZ,
                        tags JSONB NOT NULL DEFAULT '[]'::jsonb,
                        raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
            connection.commit()

    def upsert_posts(self, author_handle: str, posts: list[SocialPost], raw_payloads: dict[str, dict] | None = None) -> None:
        if not posts:
            return

        payload_map = raw_payloads or {}
        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                for post in posts:
                    cursor.execute(
                        """
                        INSERT INTO truth_social_posts (
                            id,
                            author_handle,
                            author_display_name,
                            source_url,
                            title,
                            summary,
                            published_at,
                            tags,
                            raw_payload
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id)
                        DO UPDATE SET
                            author_display_name = EXCLUDED.author_display_name,
                            source_url = EXCLUDED.source_url,
                            title = EXCLUDED.title,
                            summary = EXCLUDED.summary,
                            published_at = EXCLUDED.published_at,
                            tags = EXCLUDED.tags,
                            raw_payload = EXCLUDED.raw_payload,
                            updated_at = NOW()
                        """,
                        (
                            post.id,
                            author_handle,
                            post.author,
                            post.url,
                            post.title,
                            post.summary,
                            post.published_at,
                            Jsonb(post.tags),
                            Jsonb(payload_map.get(post.id, {})),
                        ),
                    )
            connection.commit()

    def list_recent_posts(self, author_handle: str, limit: int) -> list[SocialPost]:
        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        id,
                        author_display_name,
                        source_url,
                        title,
                        summary,
                        published_at,
                        tags
                    FROM truth_social_posts
                    WHERE author_handle = %s
                    ORDER BY published_at DESC NULLS LAST, updated_at DESC
                    LIMIT %s
                    """,
                    (author_handle, limit),
                )
                rows = cursor.fetchall()

        return [
            SocialPost(
                id=row["id"],
                title=row["title"],
                summary=row["summary"],
                published_at=row["published_at"],
                url=row["source_url"],
                author=row["author_display_name"],
                tags=row["tags"] or [],
            )
            for row in rows
        ]
