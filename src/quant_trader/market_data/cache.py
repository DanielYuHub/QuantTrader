"""Simple in-memory TTL cache for market data queries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class CacheItem(Generic[T]):
    """Single cache entry with expiry metadata."""

    value: T
    expires_at: datetime


class TTLCache(Generic[T]):
    """Dictionary-backed TTL cache."""

    def __init__(self) -> None:
        """Initialize empty cache."""

        self._items: dict[str, CacheItem[T]] = {}

    def get(self, key: str) -> T | None:
        """Return cached value if key exists and not expired."""

        item = self._items.get(key)
        if item is None:
            return None
        if datetime.now(timezone.utc) > item.expires_at:
            self._items.pop(key, None)
            return None
        return item.value

    def set(self, key: str, value: T, ttl_seconds: int) -> None:
        """Store value with TTL in seconds."""

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        self._items[key] = CacheItem(value=value, expires_at=expires_at)

    def clear(self) -> None:
        """Clear cache content."""

        self._items.clear()
