from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from app.core.config import Settings


class PostgresDatabase:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.schema_path = settings.postgres_schema_path
        self.dsn = settings.postgres_dsn

    def connect(self) -> psycopg.Connection:
        return psycopg.connect(self.dsn, row_factory=dict_row)

    def initialize(self) -> None:
        schema_sql = self.schema_path.read_text(encoding="utf-8")
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(schema_sql)
            connection.commit()
