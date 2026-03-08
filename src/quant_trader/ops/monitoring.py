"""Monitoring hooks and metrics sink integration points."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MetricsSink:
    """Simple in-memory metrics sink abstraction for instrumentation hooks."""

    counters: dict[str, float] = field(default_factory=dict)
    gauges: dict[str, float] = field(default_factory=dict)

    def increment(self, name: str, value: float = 1.0) -> None:
        """Increment counter metric."""

        self.counters[name] = self.counters.get(name, 0.0) + value

    def set_gauge(self, name: str, value: float) -> None:
        """Set gauge metric value."""

        self.gauges[name] = value
