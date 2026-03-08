"""Simple educational HK equity mean reversion strategy."""

from __future__ import annotations

from collections import deque
from statistics import mean

from quant_trader.models.common import AssetClass, Side
from quant_trader.strategy.base import BaseStrategy
from quant_trader.strategy.models import StrategyContext, StrategyEvent, StrategySignal


class HKMeanReversionStrategy(BaseStrategy):
    """Buy oversold and sell overbought around short rolling mean."""

    strategy_id = "hk_equity_mean_reversion"

    def __init__(self, lookback: int = 5, threshold_bps: float = 100.0) -> None:
        """Initialize rolling window and bps deviation threshold."""

        self._lookback = lookback
        self._threshold = threshold_bps / 10_000
        self._prices: dict[str, deque[float]] = {}

    def on_event(self, event: StrategyEvent, context: StrategyContext) -> list[StrategySignal]:
        """Emit mean-reversion signal when deviation exceeds threshold."""

        _ = context
        window = self._prices.setdefault(event.instrument_id, deque(maxlen=self._lookback))
        window.append(event.price)
        if len(window) < self._lookback:
            return []

        avg = mean(window)
        deviation = (event.price - avg) / max(avg, 1e-9)

        if deviation <= -self._threshold:
            side = Side.BUY
            reason = "price below rolling mean"
        elif deviation >= self._threshold:
            side = Side.SELL
            reason = "price above rolling mean"
        else:
            return []

        return [
            StrategySignal(
                strategy_id=self.strategy_id,
                timestamp=event.timestamp,
                instrument_id=event.instrument_id,
                asset_class=AssetClass.EQUITY,
                side=side,
                strength=min(abs(deviation) / (self._threshold * 2), 1.0),
                reason=reason,
            )
        ]
