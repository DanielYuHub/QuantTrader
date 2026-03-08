"""Strategy engine for running event-driven and scheduled strategies uniformly."""

from __future__ import annotations

from dataclasses import dataclass

from quant_trader.strategy.base import BaseStrategy
from quant_trader.strategy.models import (
    PositionTarget,
    StrategyContext,
    StrategyEvent,
    StrategyScheduleEvent,
    StrategySignal,
)
from quant_trader.strategy.portfolio import PortfolioConstructor


class ExecutionHandoff:
    """Execution handoff protocol-like class for dependency injection."""

    def submit_targets(self, targets: list[PositionTarget]) -> None:
        """Receive position targets for downstream OMS/execution processing."""

        _ = targets


@dataclass
class EngineResult:
    """Result object capturing emitted signals and portfolio targets."""

    signals: list[StrategySignal]
    targets: list[PositionTarget]


class StrategyEngine:
    """Coordinates strategy execution and portfolio construction outputs."""

    def __init__(
        self,
        strategies: list[BaseStrategy],
        portfolio_constructor: PortfolioConstructor,
        execution_handoff: ExecutionHandoff | None = None,
    ) -> None:
        """Initialize strategy engine with explicit dependencies."""

        self._strategies = strategies
        self._portfolio_constructor = portfolio_constructor
        self._execution_handoff = execution_handoff

    def process_event(self, event: StrategyEvent, context: StrategyContext) -> EngineResult:
        """Run event-driven strategies and build resulting targets."""

        signals: list[StrategySignal] = []
        for strategy in self._strategies:
            if strategy.supports_event_driven:
                signals.extend(strategy.on_event(event, context))
        return self._build_result(signals, context)

    def process_schedule(self, schedule: StrategyScheduleEvent, context: StrategyContext) -> EngineResult:
        """Run scheduled strategies and build resulting targets."""

        signals: list[StrategySignal] = []
        for strategy in self._strategies:
            if strategy.supports_scheduled:
                signals.extend(strategy.on_schedule(schedule, context))
        return self._build_result(signals, context)

    def _build_result(self, signals: list[StrategySignal], context: StrategyContext) -> EngineResult:
        """Convert signals into targets and optionally hand off to execution."""

        targets = self._portfolio_constructor.build_targets(signals, context)
        if self._execution_handoff is not None and targets:
            self._execution_handoff.submit_targets(targets)
        return EngineResult(signals=signals, targets=targets)
