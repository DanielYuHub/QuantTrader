"""Run cooperative scheduler loop for local/dev deployment."""

from __future__ import annotations

from time import sleep

from quant_trader.core.logging import get_logger
from quant_trader.ops.scheduler import TaskScheduler


if __name__ == "__main__":
    logger = get_logger(__name__)
    scheduler = TaskScheduler()

    scheduler.register("heartbeat", 10, lambda: logger.info("scheduler heartbeat"))

    while True:
        scheduler.tick()
        sleep(1)
