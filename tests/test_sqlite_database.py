"""Tests for SQLite database adapter."""

from __future__ import annotations

from quant_trader.db.sqlite import SQLiteDatabase



def test_sqlite_database_execute_and_fetch() -> None:
    """SQLite adapter should execute writes and fetch rows."""

    db = SQLiteDatabase(":memory:")
    db.execute("CREATE TABLE positions (instrument_id TEXT, quantity INTEGER)")
    db.execute(
        "INSERT INTO positions (instrument_id, quantity) VALUES (?, ?)",
        ["AAPL", 10],
    )

    rows = db.fetch_all("SELECT instrument_id, quantity FROM positions")

    assert rows == [("AAPL", 10)]
    db.close()
