"""Tests for migration and monitoring hooks."""

from __future__ import annotations

from pathlib import Path

from quant_trader.db.sqlite import SQLiteDatabase
from quant_trader.ops.migrations import MigrationRunner
from quant_trader.ops.monitoring import MetricsSink



def test_metrics_sink_counter_and_gauge() -> None:
    """Metrics sink should track counters and gauges."""

    sink = MetricsSink()
    sink.increment("orders_submitted")
    sink.increment("orders_submitted", 2)
    sink.set_gauge("latency_ms", 5.5)

    assert sink.counters["orders_submitted"] == 3
    assert sink.gauges["latency_ms"] == 5.5



def test_migration_runner_applies_sql_files(tmp_path: Path) -> None:
    """Migration runner should apply unapplied SQL migration files once."""

    migrations = tmp_path / "migrations"
    migrations.mkdir(parents=True)
    (migrations / "001_create_table.sql").write_text(
        "CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT);", encoding="utf-8"
    )

    db_path = tmp_path / "test.db"
    db = SQLiteDatabase(str(db_path))
    runner = MigrationRunner(db, migrations_dir=str(migrations))

    first = runner.run()
    second = runner.run()
    rows = db.fetch_all("SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'")

    assert first.applied == ["001_create_table.sql"]
    assert second.applied == []
    assert rows == [("test_table",)]
    db.close()
