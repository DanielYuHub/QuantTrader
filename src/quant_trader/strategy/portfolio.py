"""Portfolio construction logic that maps strategy signals into position targets."""

from __future__ import annotations

from dataclasses import dataclass

from quant_trader.models.common import Side
from quant_trader.strategy.models import PositionTarget, StrategyContext, StrategySignal


@dataclass(frozen=True)
class PortfolioConstructionConfig:
    """Configurable sizing knobs for signal-to-target translation."""

    base_lot_size: int = 100
    min_strength_threshold: float = 0.1


class PortfolioConstructor:
    """Signal-to-target transformer independent from execution layer."""

    def __init__(self, config: PortfolioConstructionConfig | None = None) -> None:
        """Initialize constructor with optional config."""

        self._config = config or PortfolioConstructionConfig()

    def build_targets(self, signals: list[StrategySignal], context: StrategyContext) -> list[PositionTarget]:
        """Convert strategy signals into portfolio target quantities."""

        targets: list[PositionTarget] = []
        for signal in signals:
            if signal.strength < self._config.min_strength_threshold:
                continue
            signed_multiplier = 1 if signal.side is Side.BUY else -1
            delta_qty = int(self._config.base_lot_size * signal.strength) * signed_multiplier
            current = context.positions.get(signal.instrument_id, 0)
            target_qty = current + delta_qty
            targets.append(
                PositionTarget(
                    strategy_id=signal.strategy_id,
                    instrument_id=signal.instrument_id,
                    asset_class=signal.asset_class,
                    target_quantity=target_qty,
                    metadata={"reason": signal.reason, **signal.metadata},
                )
            )
        return targets
