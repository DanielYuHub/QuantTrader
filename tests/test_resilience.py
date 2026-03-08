"""Tests for retry/timeout resilience helpers."""

from __future__ import annotations

from time import monotonic, sleep

import pytest

from quant_trader.utils.resilience import run_with_timeout


def test_run_with_timeout_returns_control_promptly_for_slow_worker() -> None:
    """Timeout helper should not block caller waiting for worker completion after timeout."""

    def slow_operation() -> int:
        sleep(2.0)
        return 1

    start = monotonic()
    with pytest.raises(TimeoutError):
        run_with_timeout(slow_operation, timeout_seconds=0.1)
    elapsed = monotonic() - start

    assert elapsed < 0.8
