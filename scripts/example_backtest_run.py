"""Example backtest run wiring for Phase 5 components.

This script is intentionally deterministic and educational.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from quant_trader.backtest import BacktestEngine, BacktestInputs
from quant_trader.market_data.calendar import TradingCalendar
from quant_trader.market_data.models import Bar, Market
from quant_trader.models.common import AssetClass, Side
from quant_trader.strategy.base import BaseStrategy
from quant_trader.strategy.engine import StrategyEngine
from quant_trader.strategy.models import StrategyContext, StrategyEvent, StrategySignal
from quant_trader.strategy.portfolio import PortfolioConstructionConfig, PortfolioConstructor


class DemoMomentum(BaseStrategy):
    """Tiny strategy that buys when close exceeds 100."""

    strategy_id = "demo_momentum"

    def on_event(self, event: StrategyEvent, context: StrategyContext) -> list[StrategySignal]:
        _ = context
        if event.price <= 100:
            return []
        return [
            StrategySignal(
                strategy_id=self.strategy_id,
                timestamp=event.timestamp,
                instrument_id=event.instrument_id,
                asset_class=AssetClass.EQUITY,
                side=Side.BUY,
                strength=0.5,
                reason="price breakout",
            )
        ]



def _bar(ts: datetime, symbol: str, open_price: float, close_price: float) -> Bar:
    return Bar(
        symbol=symbol,
        market=Market.US,
        timestamp=ts,
        open=open_price,
        high=max(open_price, close_price),
        low=min(open_price, close_price),
        close=close_price,
        volume=1_000,
    )


if __name__ == "__main__":
    t0 = datetime(2025, 1, 2, 14, 30, tzinfo=ZoneInfo("UTC"))
    bars = [_bar(t0, "AAPL", 100.0, 100.0), _bar(t0 + timedelta(days=1), "AAPL", 101.0, 103.0)]
    benchmark = [_bar(t0, "SPY", 500.0, 500.0), _bar(t0 + timedelta(days=1), "SPY", 501.0, 502.0)]

    strategy_engine = StrategyEngine(
        strategies=[DemoMomentum()],
        portfolio_constructor=PortfolioConstructor(PortfolioConstructionConfig(base_lot_size=10)),
    )
    engine = BacktestEngine(strategy_engine=strategy_engine, calendar=TradingCalendar())

    result = engine.run(BacktestInputs(bars_by_instrument={"AAPL": bars}, benchmark_bars=benchmark, option_contracts={}))

    print("Performance report:", result.performance_report)
    print("Assumptions:", result.assumptions)
    print("Limitations:", result.limitations)
