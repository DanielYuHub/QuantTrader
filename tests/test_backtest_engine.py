"""Tests for event-driven backtest engine behavior and accounting outputs."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from quant_trader.backtest.costs import CommissionModel, SlippageModel
from quant_trader.backtest.engine import BacktestEngine, BacktestInputs
from quant_trader.market_data.calendar import TradingCalendar
from quant_trader.market_data.models import Bar, Market
from quant_trader.models.common import AssetClass, Side
from quant_trader.strategy.base import BaseStrategy
from quant_trader.strategy.engine import StrategyEngine
from quant_trader.strategy.models import StrategyContext, StrategyEvent, StrategySignal
from quant_trader.strategy.portfolio import PortfolioConstructionConfig, PortfolioConstructor


class AlwaysBuyStrategy(BaseStrategy):
    """Simple test strategy that always emits a BUY signal."""

    strategy_id = "always_buy"

    def on_event(self, event: StrategyEvent, context: StrategyContext) -> list[StrategySignal]:
        _ = context
        return [
            StrategySignal(
                strategy_id=self.strategy_id,
                timestamp=event.timestamp,
                instrument_id=event.instrument_id,
                asset_class=AssetClass.EQUITY,
                side=Side.BUY,
                strength=1.0,
                reason="test buy",
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



def test_backtest_executes_next_bar_to_reduce_lookahead() -> None:
    """Signal from bar N should execute on bar N+1 open."""

    start = datetime(2025, 1, 2, 14, 30, tzinfo=ZoneInfo("UTC"))
    bars = [
        _bar(start, "AAPL", 100.0, 101.0),
        _bar(start + timedelta(days=1), "AAPL", 102.0, 103.0),
    ]
    benchmark = [
        _bar(start, "SPY", 500.0, 501.0),
        _bar(start + timedelta(days=1), "SPY", 502.0, 503.0),
    ]

    engine = StrategyEngine(
        strategies=[AlwaysBuyStrategy()],
        portfolio_constructor=PortfolioConstructor(PortfolioConstructionConfig(base_lot_size=1, min_strength_threshold=0.0)),
    )
    backtest = BacktestEngine(
        strategy_engine=engine,
        calendar=TradingCalendar(),
        slippage_model=SlippageModel(bps=0),
        commission_model=CommissionModel(equity_per_share=0.0, minimum_ticket=0.0),
    )

    result = backtest.run(BacktestInputs(bars_by_instrument={"AAPL": bars}, benchmark_bars=benchmark, option_contracts={}))

    assert len(result.fills) == 1
    assert result.fills[0].timestamp == bars[1].timestamp
    assert result.fills[0].price == 102.0



def test_backtest_generates_performance_and_benchmark_metrics() -> None:
    """Backtest report should include return, drawdown, and benchmark fields."""

    start = datetime(2025, 1, 2, 14, 30, tzinfo=ZoneInfo("UTC"))
    bars = [_bar(start, "AAPL", 100.0, 100.0), _bar(start + timedelta(days=1), "AAPL", 100.0, 105.0)]
    benchmark = [_bar(start, "SPY", 500.0, 500.0), _bar(start + timedelta(days=1), "SPY", 500.0, 510.0)]

    engine = StrategyEngine(
        strategies=[AlwaysBuyStrategy()],
        portfolio_constructor=PortfolioConstructor(PortfolioConstructionConfig(base_lot_size=1, min_strength_threshold=0.0)),
    )
    backtest = BacktestEngine(strategy_engine=engine, calendar=TradingCalendar())
    result = backtest.run(BacktestInputs(bars_by_instrument={"AAPL": bars}, benchmark_bars=benchmark, option_contracts={}))

    assert "total_return" in result.performance_report
    assert "benchmark_return" in result.performance_report
    assert "excess_return" in result.performance_report
    assert any("lookahead" in item.lower() for item in result.assumptions)
    assert any("survivorship bias" in item.lower() for item in result.limitations)
