"""Simple educational covered call strategy."""

from __future__ import annotations

from quant_trader.models.common import AssetClass, Side
from quant_trader.strategy.base import BaseStrategy
from quant_trader.strategy.models import StrategyContext, StrategyScheduleEvent, StrategySignal


class CoveredCallStrategy(BaseStrategy):
    """Sell one out-of-the-money call per 100 shares of underlying inventory."""

    strategy_id = "covered_call"
    supports_event_driven = False
    supports_scheduled = True

    def __init__(self, underlying_symbol: str) -> None:
        """Initialize strategy for one underlying symbol."""

        self._underlying_symbol = underlying_symbol

    def on_schedule(self, schedule: StrategyScheduleEvent, context: StrategyContext) -> list[StrategySignal]:
        """Emit sell-call signal if covered inventory and chain are available."""

        shares = context.positions.get(self._underlying_symbol, 0)
        if shares < 100:
            return []
        chain = context.option_chains.get(self._underlying_symbol)
        if chain is None or not chain.entries:
            return []

        chosen = next((e for e in chain.entries if e.contract.right.value == "CALL"), None)
        if chosen is None:
            return []

        contracts = shares // 100
        return [
            StrategySignal(
                strategy_id=self.strategy_id,
                timestamp=schedule.timestamp,
                instrument_id=chosen.contract.contract_symbol,
                asset_class=AssetClass.OPTION,
                side=Side.SELL,
                strength=min(contracts / 10, 1.0),
                reason="covered call income",
                metadata={"contracts": contracts, "underlying": self._underlying_symbol},
            )
        ]
