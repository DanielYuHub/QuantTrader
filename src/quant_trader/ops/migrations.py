"""Database migration approach using SQL files under db/migrations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from quant_trader.db.sqlite import SQLiteDatabase


@dataclass
class MigrationResult:
    """Migration execution report."""

    applied: list[str]


class MigrationRunner:
    """Apply SQL migrations in lexical order with version tracking table."""

    def __init__(self, db: SQLiteDatabase, migrations_dir: str = "db/migrations") -> None:
        self._db = db
        self._dir = Path(migrations_dir)

    def run(self) -> MigrationResult:
        """Apply unapplied migrations and return applied filenames."""

        self._db.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY)"
        )
        applied_rows = self._db.fetch_all("SELECT version FROM schema_migrations")
        applied_set = {str(row[0]) for row in applied_rows}

        applied_now: list[str] = []
        for path in sorted(self._dir.glob("*.sql")):
            if path.name in applied_set:
                continue
            sql = path.read_text(encoding="utf-8").strip()
            if sql:
                self._db.execute(sql)
            self._db.execute("INSERT INTO schema_migrations (version) VALUES (?)", [path.name])
            applied_now.append(path.name)

        return MigrationResult(applied=applied_now)
