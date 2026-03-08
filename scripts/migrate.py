"""Apply SQL migrations for local development and CI workflows."""

from __future__ import annotations

from quant_trader.config.settings import load_settings
from quant_trader.db.sqlite import SQLiteDatabase
from quant_trader.ops.migrations import MigrationRunner


if __name__ == "__main__":
    settings = load_settings()
    db_url = settings.database.url

    if db_url.startswith("sqlite:///"):
        db_path = db_url.replace("sqlite:///", "", 1)
    else:
        raise SystemExit("Only sqlite:/// URLs are supported by MigrationRunner in this phase")

    db = SQLiteDatabase(db_path)
    result = MigrationRunner(db).run()
    print("Applied migrations:", result.applied)
    db.close()
