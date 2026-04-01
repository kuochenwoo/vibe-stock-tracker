from psycopg.types.json import Jsonb

from app.core.database import PostgresDatabase
from app.models.market import AlertRule


class AlertRepository:
    def __init__(self, database: PostgresDatabase) -> None:
        self.database = database
        self.database.initialize()

    def list_all(self) -> list[AlertRule]:
        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        id::text AS id,
                        ticker_code::text AS market,
                        direction,
                        threshold::float8 AS value,
                        is_enabled AS enabled,
                        created_at,
                        metadata
                    FROM alert_rules
                    WHERE is_enabled = TRUE
                    ORDER BY created_at DESC
                    """
                )
                rows = cursor.fetchall()

        return [_row_to_alert(row) for row in rows]

    def get(self, alert_id: str) -> AlertRule | None:
        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        id::text AS id,
                        ticker_code::text AS market,
                        direction,
                        threshold::float8 AS value,
                        is_enabled AS enabled,
                        created_at,
                        metadata
                    FROM alert_rules
                    WHERE id = %s::uuid
                    """,
                    (alert_id,),
                )
                row = cursor.fetchone()

        return _row_to_alert(row) if row else None

    def add(self, alert: AlertRule) -> list[AlertRule]:
        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO alert_rules (
                        id,
                        ticker_code,
                        direction,
                        threshold,
                        is_enabled,
                        metadata
                    )
                    VALUES (%s::uuid, %s, %s, %s, %s, %s)
                    """,
                    (
                        alert.id,
                        alert.market,
                        alert.direction,
                        alert.value,
                        alert.enabled,
                        Jsonb(alert.metadata),
                    ),
                )
            connection.commit()

        return self.list_all()

    def delete(self, alert_id: str) -> list[AlertRule]:
        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM alert_rules
                    WHERE id = %s::uuid
                    RETURNING id
                    """,
                    (alert_id,),
                )
                deleted = cursor.fetchone()
                if deleted is None:
                    raise ValueError(f"Alert '{alert_id}' was not found.")
            connection.commit()

        return self.list_all()

    def record_history(
        self,
        id: str,
        alert_rule_id: str | None,
        market: str,
        direction: str,
        threshold: float,
        price: float,
    ) -> None:
        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO alert_history (
                        id,
                        alert_rule_id,
                        ticker_code,
                        direction,
                        threshold,
                        price
                    )
                    VALUES (%s::uuid, %s::uuid, %s, %s, %s, %s)
                    """,
                    (
                        id,
                        alert_rule_id,
                        market,
                        direction,
                        threshold,
                        price,
                    ),
                )
            connection.commit()

    def list_history(self, limit: int = 50) -> list[dict]:
        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        id::text AS id,
                        alert_rule_id::text AS alert_rule_id,
                        ticker_code::text AS market,
                        direction,
                        threshold::float8 AS threshold,
                        price::float8 AS price,
                        triggered_at
                    FROM alert_history
                    ORDER BY triggered_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                return cursor.fetchall()


def _row_to_alert(row: dict) -> AlertRule:
    return AlertRule(
        id=row["id"],
        market=row["market"],
        direction=row["direction"],
        value=row["value"],
        enabled=row["enabled"],
        created_at=row["created_at"],
        metadata=row["metadata"] or {},
    )
