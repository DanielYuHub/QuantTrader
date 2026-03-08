"""Base strategy abstractions for event-driven and scheduled strategies."""

from __future__ import annotations

from abc import ABC

from quant_trader.strategy.models import StrategyContext, StrategyEvent, StrategyScheduleEvent, StrategySignal


class BaseStrategy(ABC):
    """Base class for reusable strategy modules."""

    strategy_id: str
    supports_event_driven: bool = True
    supports_scheduled: bool = False

    def on_event(self, event: StrategyEvent, context: StrategyContext) -> list[StrategySignal]:
        """Handle market event and emit alpha signals."""

        _ = event, context
        return []

    def on_schedule(self, schedule: StrategyScheduleEvent, context: StrategyContext) -> list[StrategySignal]:
        """Handle scheduler trigger and emit alpha signals."""

        _ = schedule, context
        return []
