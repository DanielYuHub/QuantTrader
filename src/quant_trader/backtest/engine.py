"""Event-driven backtest engine with next-bar execution and realistic accounting hooks."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from quant_trader.backtest.accounting import PortfolioAccounting
from quant_trader.backtest.costs import CommissionModel, SlippageModel
from quant_trader.backtest.models import BacktestConfig, BacktestFill, BacktestResult, BarEvent, PendingTarget
from quant_trader.backtest.options import DefaultOptionLifecycleHook, OptionLifecycleHook
from quant_trader.backtest.performance import summarize_performance
from quant_trader.market_data.calendar import TradingCalendar
from quant_trader.market_data.models import Bar, OptionContract
from quant_trader.models.common import AssetClass, Side
from quant_trader.strategy.engine import StrategyEngine
from quant_trader.strategy.models import PositionTarget, StrategyContext, StrategyEvent, StrategyMode


@dataclass
class BacktestInputs:
    """Container for required backtest inputs."""

    bars_by_instrument: dict[str, list[Bar]]
    benchmark_bars: list[Bar]
    option_contracts: dict[str, OptionContract]


class BacktestEngine:
    """Event-driven backtesting engine with no-lookahead default behavior."""

    def __init__(
        self,
        strategy_engine: StrategyEngine,
        calendar: TradingCalendar,
        slippage_model: SlippageModel | None = None,
        commission_model: CommissionModel | None = None,
        option_hook: OptionLifecycleHook | None = None,
        config: BacktestConfig | None = None,
    ) -> None:
        """Initialize backtest engine dependencies."""

        self._strategy_engine = strategy_engine
        self._calendar = calendar
        self._slippage_model = slippage_model or SlippageModel()
        self._commission_model = commission_model or CommissionModel()
        self._option_hook = option_hook or DefaultOptionLifecycleHook()
        self._config = config or BacktestConfig()

    def run(self, inputs: BacktestInputs) -> BacktestResult:
        """Run event-driven backtest over provided historical bars."""

        timeline = self._merge_timeline(inputs.bars_by_instrument)
        benchmark_curve = [(bar.timestamp, bar.close) for bar in inputs.benchmark_bars]

        accounting = PortfolioAccounting(initial_cash=self._config.initial_cash)
        fills: list[BacktestFill] = []
        curve = []
        pending_targets: dict[str, list[PendingTarget]] = defaultdict(list)

        for event in timeline:
            bar = event.bar
            if not self._calendar.is_trading_day(bar.timestamp, bar.market):
                continue

            # 1) execute queued targets at current bar open (next-bar execution, avoids lookahead)
            fills.extend(self._execute_pending(bar, pending_targets, accounting, inputs.option_contracts))

            # 2) run strategy on current bar close info and enqueue next-bar targets
            context = StrategyContext(
                mode=StrategyMode.BACKTEST,
                positions={k: p.quantity for k, p in accounting.positions.items()},
            )
            if self._should_emit_strategy_event(bar, inputs.option_contracts):
                signal_event = StrategyEvent(timestamp=bar.timestamp, instrument_id=bar.symbol, price=bar.close)
                result = self._strategy_engine.process_event(signal_event, context)
                for target in result.targets:
                    pending_targets[target.instrument_id].append(PendingTarget(timestamp=bar.timestamp, target=target))

            # 3) process option expiration hooks
            self._process_option_expiration(bar.timestamp, accounting, inputs.option_contracts, marks=self._latest_marks(inputs, bar.timestamp))

            # 4) mark-to-market snapshot
            snapshot = accounting.snapshot(bar.timestamp, marks=self._latest_marks(inputs, bar.timestamp))
            curve.append(snapshot)

        assumptions = [
            "Execution uses next-bar open to mitigate lookahead bias.",
            "Slippage and commissions are linear configurable models.",
            "Calendar uses configured regular sessions and weekday filters.",
            "Benchmark comparison uses provided benchmark close series.",
        ]
        limitations = [
            "Survivorship bias is not automatically removed unless historical universe is pre-curated externally.",
            "Corporate action adjustment is not automatically applied in this phase.",
            "Options assignment/exercise is exposed via hooks; default behavior is simplified cash-settlement on expiration.",
        ]

        return BacktestResult(
            fills=fills,
            equity_curve=curve,
            attribution=accounting.attribution,
            benchmark_curve=benchmark_curve,
            performance_report=summarize_performance(curve, benchmark_curve),
            assumptions=assumptions,
            limitations=limitations,
        )

    def _execute_pending(
        self,
        bar: Bar,
        pending_targets: dict[str, list[PendingTarget]],
        accounting: PortfolioAccounting,
        option_contracts: dict[str, OptionContract],
    ) -> list[BacktestFill]:
        """Execute queued targets on this bar's open price."""

        queued = pending_targets.get(bar.symbol, [])
        if not queued:
            return []

        fills: list[BacktestFill] = []
        current_qty = accounting.positions.get(bar.symbol).quantity if bar.symbol in accounting.positions else 0

        for pending in queued:
            target = pending.target
            delta = target.target_quantity - current_qty
            if delta == 0:
                continue
            side = Side.BUY if delta > 0 else Side.SELL
            qty = abs(delta)
            slipped_price, slippage = self._slippage_model.apply(bar.open, side)
            commission, fees = self._commission_model.cost(target.asset_class, qty, slipped_price * qty)
            fill = BacktestFill(
                timestamp=bar.timestamp,
                instrument_id=bar.symbol,
                side=side,
                quantity=qty,
                price=slipped_price,
                slippage=slippage,
                commission=commission,
                fees=fees,
                asset_class=target.asset_class,
            )
            accounting.apply_fill(fill)

            # attach option contract metadata when applicable
            if target.asset_class is AssetClass.OPTION and bar.symbol in accounting.positions:
                pos = accounting.positions[bar.symbol]
                accounting.positions[bar.symbol] = pos.model_copy(update={"contract": option_contracts.get(bar.symbol)})

            fills.append(fill)
            current_qty = accounting.positions.get(bar.symbol).quantity if bar.symbol in accounting.positions else 0

        pending_targets[bar.symbol] = []
        return fills

    def _merge_timeline(self, bars_by_instrument: dict[str, list[Bar]]) -> list[BarEvent]:
        """Merge bars into chronological event stream."""

        events = [BarEvent(bar=bar) for bars in bars_by_instrument.values() for bar in bars]
        events.sort(key=lambda event: event.bar.timestamp)
        return events

    def _latest_marks(self, inputs: BacktestInputs, timestamp: datetime) -> dict[str, float]:
        """Build latest available marks up to timestamp to avoid lookahead."""

        marks: dict[str, float] = {}
        for symbol, bars in inputs.bars_by_instrument.items():
            eligible = [bar for bar in bars if bar.timestamp <= timestamp]
            if eligible:
                marks[symbol] = eligible[-1].close
        return marks

    def _process_option_expiration(
        self,
        timestamp: datetime,
        accounting: PortfolioAccounting,
        option_contracts: dict[str, OptionContract],
        marks: dict[str, float],
    ) -> None:
        """Apply option expiration hook and close expired contracts."""

        for instrument_id, position in list(accounting.positions.items()):
            contract = option_contracts.get(instrument_id)
            if contract is None or position.quantity == 0:
                continue
            if contract.expiry <= timestamp:
                spot = marks.get(contract.underlying_symbol)
                cash_adjustment = self._option_hook.on_expiration(position, spot, timestamp)
                accounting.cash += cash_adjustment
                accounting.positions[instrument_id] = position.model_copy(update={"quantity": 0, "average_price": 0.0})

    @staticmethod
    def _should_emit_strategy_event(bar: Bar, option_contracts: dict[str, OptionContract]) -> bool:
        """Return whether a bar should be converted into a strategy event."""

        contract = option_contracts.get(bar.symbol)
        if contract is None:
            return True
        if contract.expiry <= bar.timestamp and bar.close <= 0:
            return False
        return True
