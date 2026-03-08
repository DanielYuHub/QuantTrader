"""Simple educational US equity momentum strategy."""

from __future__ import annotations

from collections import deque

from quant_trader.models.common import AssetClass, Side
from quant_trader.strategy.base import BaseStrategy
from quant_trader.strategy.models import StrategyContext, StrategyEvent, StrategySignal


class USEquityMomentumStrategy(BaseStrategy):
    """Buy when short-term momentum is positive, sell when negative."""

    strategy_id = "us_equity_momentum"

    def __init__(self, lookback: int = 3) -> None:
        """Initialize rolling lookback window."""

        self._lookback = lookback
        self._prices: dict[str, deque[float]] = {}

    def on_event(self, event: StrategyEvent, context: StrategyContext) -> list[StrategySignal]:
        """Emit momentum signal after enough observations are collected."""

        _ = context
        window = self._prices.setdefault(event.instrument_id, deque(maxlen=self._lookback))
        window.append(event.price)
        if len(window) < self._lookback:
            return []

        first, last = window[0], window[-1]
        if last > first:
            side = Side.BUY
            reason = "positive momentum"
        elif last < first:
            side = Side.SELL
            reason = "negative momentum"
        else:
            return []

        return [
            StrategySignal(
                strategy_id=self.strategy_id,
                timestamp=event.timestamp,
                instrument_id=event.instrument_id,
                asset_class=AssetClass.EQUITY,
                side=side,
                strength=min(abs(last - first) / max(first, 1e-9), 1.0),
                reason=reason,
            )
        ]
