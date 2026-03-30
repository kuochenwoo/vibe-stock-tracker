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
