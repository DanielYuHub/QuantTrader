"""Production-focused risk framework with portfolio, market, options, and operational guards."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, Field

from quant_trader.core.logging import get_logger
from quant_trader.models.common import AssetClass, MarketQuote, OrderRequest, RiskDecision, Side


class InstrumentRiskInfo(BaseModel):
    """Metadata used for risk checks beyond plain order attributes."""

    instrument_id: str
    asset_class: AssetClass
    sector: str = "UNKNOWN"
    group: str = "DEFAULT"
    expiry: datetime | None = None


class OptionGreekExposure(BaseModel):
    """Aggregated option greek exposures."""

    delta: float = 0.0
    gamma: float = 0.0
    vega: float = 0.0


class RiskSnapshot(BaseModel):
    """Current risk state snapshot used by pre-trade controls."""

    timestamp: datetime
    positions: dict[str, int] = Field(default_factory=dict)
    quotes: dict[str, MarketQuote] = Field(default_factory=dict)
    instruments: dict[str, InstrumentRiskInfo] = Field(default_factory=dict)
    exposure_by_sector: dict[str, float] = Field(default_factory=dict)
    exposure_by_group: dict[str, float] = Field(default_factory=dict)
    gross_exposure: float = 0.0
    net_exposure: float = 0.0
    realized_pnl_today: float = 0.0
    unrealized_pnl: float = 0.0
    strategy_drawdown: dict[str, float] = Field(default_factory=dict)
    option_greeks: OptionGreekExposure = Field(default_factory=OptionGreekExposure)
    broker_connected: bool = True


@dataclass(frozen=True)
class ProductionRiskLimits:
    """Comprehensive risk limits for production-focused pre-trade checks."""

    max_position_per_instrument: int = 1_000
    max_sector_exposure: float = 250_000.0
    max_group_exposure: float = 250_000.0
    max_gross_exposure: float = 1_000_000.0
    max_net_exposure: float = 500_000.0
    max_daily_loss: float = 10_000.0
    max_strategy_drawdown: float = 0.2
    max_orders_per_minute: int = 60
    max_option_delta: float = 5_000.0
    max_option_gamma: float = 2_000.0
    max_option_vega: float = 4_000.0
    min_days_to_option_expiry: int = 1
    max_stale_quote_seconds: int = 5


class ProductionRiskEngine:
    """Risk engine with instrument, portfolio, market, options, and operational controls."""

    def __init__(self, limits: ProductionRiskLimits) -> None:
        """Initialize risk engine with configured hard limits."""

        self._limits = limits
        self._logger = get_logger(__name__)
        self._emergency_stop: bool = False
        self._emergency_reason: str | None = None
        self._order_window_key: tuple[int, int, int, int, int] | None = None
        self._orders_in_window = 0
        self._seen_order_keys: set[str] = set()
        self._audit: list[dict[str, str | bool | float]] = []

    def evaluate_order(self, order_request: OrderRequest, snapshot: RiskSnapshot, now: datetime) -> RiskDecision:
        """Evaluate one order against all configured risk controls."""

        violations: list[str] = []

        if self._emergency_stop:
            violations.append(f"emergency stop active: {self._emergency_reason or 'unknown reason'}")

        if not snapshot.broker_connected:
            violations.append("broker connectivity unhealthy")

        if order_request.idempotency_key in self._seen_order_keys:
            violations.append("duplicate order idempotency key")

        self._roll_rate_window(now)
        if self._orders_in_window >= self._limits.max_orders_per_minute:
            violations.append("max order rate exceeded")

        if snapshot.realized_pnl_today + snapshot.unrealized_pnl <= -abs(self._limits.max_daily_loss):
            violations.append("max daily loss breached")

        strategy_id = self._strategy_id(order_request)
        if snapshot.strategy_drawdown.get(strategy_id, 0.0) >= self._limits.max_strategy_drawdown:
            violations.append("max strategy drawdown breached")

        quote = snapshot.quotes.get(order_request.instrument_id)
        if quote is None:
            violations.append("missing quote")
            reference_price = 0.0
        else:
            if quote.is_stale(self._limits.max_stale_quote_seconds, now):
                violations.append("stale market data")
            reference_price = quote.last or (quote.bid + quote.ask) / 2

        signed_qty = int(order_request.quantity if order_request.side is Side.BUY else -order_request.quantity)
        current_qty = snapshot.positions.get(order_request.instrument_id, 0)
        projected_qty = current_qty + signed_qty
        if abs(projected_qty) > self._limits.max_position_per_instrument:
            violations.append("position limit exceeded")

        order_notional_signed = signed_qty * reference_price
        order_notional_abs = abs(order_notional_signed)

        projected_gross = snapshot.gross_exposure + order_notional_abs
        if projected_gross > self._limits.max_gross_exposure:
            violations.append("gross exposure limit exceeded")

        projected_net = snapshot.net_exposure + order_notional_signed
        if abs(projected_net) > self._limits.max_net_exposure:
            violations.append("net exposure limit exceeded")

        instrument = snapshot.instruments.get(order_request.instrument_id)
        if instrument is not None:
            sector_exposure = snapshot.exposure_by_sector.get(instrument.sector, 0.0) + order_notional_abs
            if sector_exposure > self._limits.max_sector_exposure:
                violations.append("sector exposure limit exceeded")

            group_exposure = snapshot.exposure_by_group.get(instrument.group, 0.0) + order_notional_abs
            if group_exposure > self._limits.max_group_exposure:
                violations.append("group exposure limit exceeded")

            if order_request.asset_class is AssetClass.OPTION and instrument.expiry is not None:
                days_to_expiry = (instrument.expiry.date() - now.date()).days
                if days_to_expiry < self._limits.min_days_to_option_expiry:
                    violations.append("option expiration risk threshold breached")

        if order_request.asset_class is AssetClass.OPTION:
            if abs(snapshot.option_greeks.delta) > self._limits.max_option_delta:
                violations.append("option delta exposure exceeded")
            if abs(snapshot.option_greeks.gamma) > self._limits.max_option_gamma:
                violations.append("option gamma exposure exceeded")
            if abs(snapshot.option_greeks.vega) > self._limits.max_option_vega:
                violations.append("option vega exposure exceeded")

        allowed = len(violations) == 0
        if allowed:
            self._orders_in_window += 1
            self._seen_order_keys.add(order_request.idempotency_key)
            self._record_audit(order_request, True, "allowed")
            return RiskDecision(allowed=True)

        reason = "; ".join(violations)
        self._record_audit(order_request, False, reason)
        self._logger.warning("Risk blocked order %s: %s", order_request.idempotency_key, reason)
        return RiskDecision(allowed=False, reason=reason)

    def trigger_emergency_stop(self, reason: str) -> None:
        """Activate emergency stop workflow."""

        self._emergency_stop = True
        self._emergency_reason = reason
        self._logger.error("Emergency stop activated: %s", reason)

    def clear_emergency_stop(self) -> None:
        """Deactivate emergency stop state after manual intervention."""

        self._emergency_stop = False
        self._emergency_reason = None
        self._logger.warning("Emergency stop cleared")

    def emergency_stop_active(self) -> bool:
        """Return emergency stop status."""

        return self._emergency_stop

    def audit_log(self) -> list[dict[str, str | bool | float]]:
        """Return immutable copy of risk audit records."""

        return list(self._audit)

    def _roll_rate_window(self, now: datetime) -> None:
        """Maintain per-minute order-rate bucket."""

        key = (now.year, now.month, now.day, now.hour, now.minute)
        if key != self._order_window_key:
            self._order_window_key = key
            self._orders_in_window = 0

    def _record_audit(self, order_request: OrderRequest, allowed: bool, reason: str) -> None:
        """Append one audit event record."""

        self._audit.append(
            {
                "idempotency_key": order_request.idempotency_key,
                "instrument_id": order_request.instrument_id,
                "asset_class": order_request.asset_class.value,
                "allowed": allowed,
                "reason": reason,
            }
        )

    @staticmethod
    def _strategy_id(order_request: OrderRequest) -> str:
        """Derive strategy identifier from idempotency key convention."""

        return order_request.idempotency_key.split(":", maxsplit=1)[0]
