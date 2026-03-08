"""Lightweight scheduler setup for periodic operational tasks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

from quant_trader.core.logging import get_logger

TaskCallable = Callable[[], None]


@dataclass
class ScheduledTask:
    """Scheduled task with interval tracking."""

    name: str
    interval_seconds: int
    func: TaskCallable
    next_run: datetime


class TaskScheduler:
    """Simple cooperative scheduler for periodic jobs."""

    def __init__(self) -> None:
        self._tasks: list[ScheduledTask] = []
        self._logger = get_logger(__name__)

    def register(self, name: str, interval_seconds: int, func: TaskCallable) -> None:
        """Register periodic task."""

        if interval_seconds <= 0:
            msg = "interval_seconds must be greater than 0"
            raise ValueError(msg)

        self._tasks.append(
            ScheduledTask(
                name=name,
                interval_seconds=interval_seconds,
                func=func,
                next_run=datetime.now(timezone.utc),
            )
        )

    def tick(self, now: datetime | None = None) -> list[str]:
        """Run due tasks once and return list of executed task names."""

        ts = now or datetime.now(timezone.utc)
        executed: list[str] = []
        for task in self._tasks:
            if ts >= task.next_run:
                task.func()
                executed.append(task.name)
                task.next_run = ts + timedelta(seconds=task.interval_seconds)
                self._logger.info("Executed scheduled task %s", task.name)
        return executed
