from app.core.database import PostgresDatabase
from app.models.market import DailyBar


class DailyBarRepository:
    def __init__(self, database: PostgresDatabase) -> None:
        self.database = database
        self.database.initialize()

    def upsert_bars(self, ticker_code: str, bars: list[DailyBar]) -> None:
        if not bars:
            return

        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                for bar in bars:
                    cursor.execute(
                        """
                        INSERT INTO ticker_daily_bars (
                            ticker_code,
                            trading_date,
                            open,
                            high,
                            low,
                            close,
                            volume,
                            source
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (ticker_code, trading_date)
                        DO UPDATE SET
                            open = EXCLUDED.open,
                            high = EXCLUDED.high,
                            low = EXCLUDED.low,
                            close = EXCLUDED.close,
                            volume = EXCLUDED.volume,
                            source = EXCLUDED.source,
                            updated_at = NOW()
                        """,
                        (
                            ticker_code,
                            bar.trading_date,
                            bar.open,
                            bar.high,
                            bar.low,
                            bar.close,
                            bar.volume,
                            bar.source,
                        ),
                    )
            connection.commit()

    def get_latest_trading_date(self, ticker_code: str):
        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT MAX(trading_date) AS latest_trading_date
                    FROM ticker_daily_bars
                    WHERE ticker_code = %s
                    """,
                    (ticker_code,),
                )
                row = cursor.fetchone()

        return row["latest_trading_date"] if row and row["latest_trading_date"] is not None else None

    def list_recent_bars(self, ticker_code: str, limit: int) -> list[DailyBar]:
        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        trading_date,
                        open,
                        high,
                        low,
                        close,
                        volume,
                        source
                    FROM ticker_daily_bars
                    WHERE ticker_code = %s
                    ORDER BY trading_date DESC
                    LIMIT %s
                    """,
                    (ticker_code, limit),
                )
                rows = cursor.fetchall()

        return [
            DailyBar(
                trading_date=row["trading_date"],
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]) if row["volume"] is not None else None,
                source=row["source"],
            )
            for row in rows
        ]
