"""Tests for strategy engine orchestration and portfolio construction."""

from __future__ import annotations

from datetime import datetime, timezone

from quant_trader.models.common import AssetClass, Side
from quant_trader.strategy.base import BaseStrategy
from quant_trader.strategy.engine import ExecutionHandoff, StrategyEngine
from quant_trader.strategy.models import StrategyContext, StrategyEvent, StrategyMode, StrategyScheduleEvent, StrategySignal
from quant_trader.strategy.portfolio import PortfolioConstructionConfig, PortfolioConstructor


class ScheduledDummyStrategy(BaseStrategy):
    """Scheduled-only strategy used for engine behavior tests."""

    strategy_id = "scheduled_dummy"
    supports_event_driven = False
    supports_scheduled = True

    def on_schedule(self, schedule: StrategyScheduleEvent, context: StrategyContext) -> list[StrategySignal]:
        _ = context
        return [
            StrategySignal(
                strategy_id=self.strategy_id,
                timestamp=schedule.timestamp,
                instrument_id="AAPL",
                asset_class=AssetClass.EQUITY,
                side=Side.BUY,
                strength=0.5,
                reason="scheduled rebalance",
            )
        ]


class CaptureHandoff(ExecutionHandoff):
    """Capture execution handoff targets for test assertions."""

    def __init__(self) -> None:
        self.targets_count = 0

    def submit_targets(self, targets: list) -> None:
        self.targets_count += len(targets)



def test_engine_process_schedule_emits_targets_and_handoff() -> None:
    """Scheduled strategy outputs should be converted into targets and handed off."""

    handoff = CaptureHandoff()
    engine = StrategyEngine(
        strategies=[ScheduledDummyStrategy()],
        portfolio_constructor=PortfolioConstructor(PortfolioConstructionConfig(base_lot_size=10)),
        execution_handoff=handoff,
    )
    context = StrategyContext(mode=StrategyMode.PAPER)
    schedule = StrategyScheduleEvent(timestamp=datetime.now(timezone.utc), trigger_name="daily_close")

    result = engine.process_schedule(schedule, context)

    assert len(result.signals) == 1
    assert len(result.targets) == 1
    assert result.targets[0].target_quantity > 0
    assert handoff.targets_count == 1



def test_engine_process_event_with_no_event_strategies_returns_empty() -> None:
    """Event processing should stay empty when no event-driven strategies are registered."""

    engine = StrategyEngine(
        strategies=[ScheduledDummyStrategy()],
        portfolio_constructor=PortfolioConstructor(),
    )
    context = StrategyContext(mode=StrategyMode.BACKTEST)
    event = StrategyEvent(timestamp=datetime.now(timezone.utc), instrument_id="AAPL", price=100.0)

    result = engine.process_event(event, context)

    assert result.signals == []
    assert result.targets == []
