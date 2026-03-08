"""Database abstraction interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence


class DatabaseInterface(ABC):
    """Minimal database abstraction for persistence concerns."""

    @abstractmethod
    def execute(self, query: str, parameters: Sequence[object] | None = None) -> None:
        """Execute a write query."""

    @abstractmethod
    def fetch_all(self, query: str, parameters: Sequence[object] | None = None) -> list[tuple[object, ...]]:
        """Execute a read query and return all rows."""

    @abstractmethod
    def close(self) -> None:
        """Close open database resources."""
