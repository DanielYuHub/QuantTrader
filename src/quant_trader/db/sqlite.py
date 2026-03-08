"""SQLite database adapter implementing the repository database interface."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from pathlib import Path

from quant_trader.interfaces.database import DatabaseInterface


class SQLiteDatabase(DatabaseInterface):
    """SQLite implementation of the `DatabaseInterface`."""

    def __init__(self, db_path: str) -> None:
        """Create a SQLite connection for the provided path."""

        self._db_path: str = db_path
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._connection: sqlite3.Connection = sqlite3.connect(db_path)

    def execute(self, query: str, parameters: Sequence[object] | None = None) -> None:
        """Execute a mutation statement and commit."""

        cursor = self._connection.cursor()
        cursor.execute(query, tuple(parameters or ()))
        self._connection.commit()

    def fetch_all(self, query: str, parameters: Sequence[object] | None = None) -> list[tuple[object, ...]]:
        """Execute a query and return all result rows."""

        cursor = self._connection.cursor()
        cursor.execute(query, tuple(parameters or ()))
        return cursor.fetchall()

    def close(self) -> None:
        """Close connection."""

        self._connection.close()
