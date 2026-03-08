"""Simple educational options volatility breakout strategy."""

from __future__ import annotations

from collections import deque
from statistics import mean

from quant_trader.models.common import AssetClass, Side
from quant_trader.strategy.base import BaseStrategy
from quant_trader.strategy.models import StrategyContext, StrategyScheduleEvent, StrategySignal


class OptionsVolatilityBreakoutStrategy(BaseStrategy):
    """Buy option exposure when average IV jumps above recent baseline."""

    strategy_id = "options_vol_breakout"
    supports_event_driven = False
    supports_scheduled = True

    def __init__(self, underlying_symbol: str, lookback: int = 5, breakout_multiplier: float = 1.2) -> None:
        """Initialize rolling IV history parameters."""

        self._underlying_symbol = underlying_symbol
        self._lookback = lookback
        self._multiplier = breakout_multiplier
        self._iv_history: deque[float] = deque(maxlen=lookback)

    def on_schedule(self, schedule: StrategyScheduleEvent, context: StrategyContext) -> list[StrategySignal]:
        """Emit signal when IV exceeds rolling mean by configured multiplier."""

        chain = context.option_chains.get(self._underlying_symbol)
        if chain is None:
            return []

        iv_values = [entry.implied_volatility for entry in chain.entries if entry.implied_volatility is not None]
        if not iv_values:
            return []

        current_iv = mean(iv_values)
        if len(self._iv_history) == self._lookback:
            baseline = mean(self._iv_history)
            self._iv_history.append(current_iv)
            if baseline > 0 and current_iv >= baseline * self._multiplier:
                contract = chain.entries[0].contract.contract_symbol
                return [
                    StrategySignal(
                        strategy_id=self.strategy_id,
                        timestamp=schedule.timestamp,
                        instrument_id=contract,
                        asset_class=AssetClass.OPTION,
                        side=Side.BUY,
                        strength=min((current_iv / baseline) - 1.0, 1.0),
                        reason="implied volatility breakout",
                        metadata={"iv": current_iv, "baseline_iv": baseline},
                    )
                ]
            return []

        self._iv_history.append(current_iv)
        return []
