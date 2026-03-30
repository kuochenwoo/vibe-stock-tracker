from psycopg.types.json import Jsonb

from app.core.database import PostgresDatabase
from app.models.market import TrackedTicker


class TickerRepository:
    def __init__(self, database: PostgresDatabase) -> None:
        self.database = database
        self.database.initialize()

    def list_all(self) -> list[TrackedTicker]:
        query = """
            SELECT
                t.code,
                t.provider_symbol AS symbol,
                t.display_name AS name,
                t.provider,
                t.metadata,
                COALESCE(
                    ARRAY_AGG(a.alias ORDER BY a.alias) FILTER (WHERE a.alias IS NOT NULL),
                    ARRAY[]::citext[]
                ) AS aliases
            FROM tracked_tickers t
            LEFT JOIN ticker_aliases a
                ON a.ticker_id = t.id
            WHERE t.is_active = TRUE
            GROUP BY t.id
            ORDER BY t.code
        """
        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()

        return [
            TrackedTicker(
                code=row["code"],
                symbol=row["symbol"],
                name=row["name"],
                provider=row["provider"],
                aliases=list(row["aliases"] or []),
                metadata=row["metadata"] or {},
            )
            for row in rows
        ]

    def add(self, ticker: TrackedTicker) -> list[TrackedTicker]:
        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT 1
                    FROM tracked_tickers
                    WHERE code = %s
                    """,
                    (ticker.code,),
                )
                if cursor.fetchone():
                    raise ValueError(f"Ticker code '{ticker.code}' already exists.")

                cursor.execute(
                    """
                    INSERT INTO tracked_tickers (
                        code,
                        provider,
                        provider_symbol,
                        display_name,
                        metadata
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        ticker.code,
                        ticker.provider,
                        ticker.symbol,
                        ticker.name,
                        Jsonb(ticker.metadata),
                    ),
                )
                ticker_id = cursor.fetchone()["id"]

                for alias in _normalized_aliases(ticker):
                    cursor.execute(
                        """
                        INSERT INTO ticker_aliases (ticker_id, alias, alias_type, source)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (ticker_id, alias, alias_type) DO NOTHING
                        """,
                        (ticker_id, alias, "general", "api"),
                    )

            connection.commit()

        return self.list_all()

    def delete(self, code: str) -> list[TrackedTicker]:
        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM tracked_tickers
                    WHERE code = %s
                    RETURNING id
                    """,
                    (code,),
                )
                deleted = cursor.fetchone()
                if deleted is None:
                    raise ValueError(f"Ticker code '{code}' was not found.")
            connection.commit()

        return self.list_all()


def _normalized_aliases(ticker: TrackedTicker) -> list[str]:
    aliases = {ticker.symbol}
    aliases.update(alias.strip() for alias in ticker.aliases if alias.strip())
    return sorted(aliases)
