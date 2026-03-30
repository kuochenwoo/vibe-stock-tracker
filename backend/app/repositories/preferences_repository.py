from psycopg.types.json import Jsonb

from app.core.database import PostgresDatabase
from app.models.market import PanelOrderPreference

PANEL_ORDER_PREFERENCE_KEY = "panel_order"


class PreferencesRepository:
    def __init__(self, database: PostgresDatabase) -> None:
        self.database = database
        self.database.initialize()

    def get_panel_order(self) -> PanelOrderPreference:
        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT value, updated_at
                    FROM app_preferences
                    WHERE preference_key = %s
                    """,
                    (PANEL_ORDER_PREFERENCE_KEY,),
                )
                row = cursor.fetchone()

        if not row:
            return PanelOrderPreference()

        value = row["value"] or {}
        codes = value.get("codes", []) if isinstance(value, dict) else []
        return PanelOrderPreference(codes=[str(code).upper() for code in codes], updated_at=row["updated_at"])

    def save_panel_order(self, codes: list[str]) -> PanelOrderPreference:
        normalized_codes = [code.strip().upper() for code in codes if code and code.strip()]
        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO app_preferences (preference_key, value, updated_at)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT (preference_key)
                    DO UPDATE SET
                        value = EXCLUDED.value,
                        updated_at = NOW()
                    RETURNING value, updated_at
                    """,
                    (PANEL_ORDER_PREFERENCE_KEY, Jsonb({"codes": normalized_codes})),
                )
                row = cursor.fetchone()
            connection.commit()

        value = row["value"] or {}
        return PanelOrderPreference(
            codes=[str(code).upper() for code in value.get("codes", [])],
            updated_at=row["updated_at"],
        )
