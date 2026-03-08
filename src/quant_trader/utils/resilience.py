"""Retry and timeout utilities for adapter calls."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from time import sleep
from typing import Callable, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


class RetryError(RuntimeError):
    """Raised when retry attempts are exhausted."""


@dataclass(frozen=True)
class RetryPolicy:
    """Retry policy for transient provider failures."""

    attempts: int = 3
    delay_seconds: float = 0.1


def run_with_retry(func: Callable[P, R], *args: P.args, policy: RetryPolicy, **kwargs: P.kwargs) -> R:
    """Execute function with retry policy and raise `RetryError` when exhausted."""

    last_error: Exception | None = None
    for attempt in range(1, policy.attempts + 1):
        try:
            return func(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - explicit pass-through for transient adapter failures
            last_error = exc
            if attempt == policy.attempts:
                break
            sleep(policy.delay_seconds)

    msg = f"Operation failed after {policy.attempts} attempts"
    raise RetryError(msg) from last_error


def run_with_timeout(func: Callable[P, R], *args: P.args, timeout_seconds: float, **kwargs: P.kwargs) -> R:
    """Execute function with timeout protection.

    Notes:
        Python threads cannot be forcefully terminated. On timeout this helper returns control
        promptly by shutting down the executor with ``wait=False``; a running worker thread may
        still continue in the background until it finishes.
    """

    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(func, *args, **kwargs)
    try:
        return future.result(timeout=timeout_seconds)
    except FutureTimeoutError as exc:
        future.cancel()
        msg = f"Operation timed out after {timeout_seconds} seconds"
        raise TimeoutError(msg) from exc
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
