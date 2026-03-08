"""Shared domain models used across interface boundaries."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, PositiveInt, model_validator


class AssetClass(StrEnum):
    """Supported asset classes."""

    EQUITY = "EQUITY"
    OPTION = "OPTION"


class Side(StrEnum):
    """Order side values."""

    BUY = "BUY"
    SELL = "SELL"


class OrderType(StrEnum):
    """Order type values."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"


class OrderStatus(StrEnum):
    """Order status values."""

    PENDING_NEW = "PENDING_NEW"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REPLACED = "REPLACED"
    REJECTED = "REJECTED"


class Instrument(BaseModel):
    """Canonical instrument model."""

    instrument_id: str
    symbol: str
    exchange: str
    currency: str
    asset_class: AssetClass


class MarketQuote(BaseModel):
    """Normalized market quote."""

    instrument_id: str
    timestamp: datetime
    bid: float = Field(ge=0)
    ask: float = Field(ge=0)
    last: float | None = Field(default=None, ge=0)

    def is_stale(self, max_age_seconds: int, now: datetime | None = None) -> bool:
        """Return whether quote timestamp is older than max age threshold."""

        now_ts = now or datetime.now(timezone.utc)
        ts = self.timestamp if self.timestamp.tzinfo else self.timestamp.replace(tzinfo=timezone.utc)
        return now_ts - ts > timedelta(seconds=max_age_seconds)


class Signal(BaseModel):
    """Strategy signal payload passed to portfolio/risk layers."""

    strategy_id: str
    instrument_id: str
    timestamp: datetime
    direction: Side
    confidence: float = Field(ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class OrderRequest(BaseModel):
    """Order request created by portfolio/OMS."""

    idempotency_key: str
    instrument_id: str
    side: Side
    quantity: PositiveInt
    order_type: OrderType
    asset_class: AssetClass = AssetClass.EQUITY
    limit_price: float | None = Field(default=None, gt=0)
    stop_price: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_price_requirements(self) -> OrderRequest:
        """Validate order type-specific pricing fields."""

        if self.order_type is OrderType.LIMIT and self.limit_price is None:
            msg = "LIMIT order requires limit_price"
            raise ValueError(msg)
        if self.order_type is OrderType.STOP and self.stop_price is None:
            msg = "STOP order requires stop_price"
            raise ValueError(msg)
        return self


class TradeFill(BaseModel):
    """Execution fill event for an order."""

    fill_id: str
    order_id: str
    quantity: PositiveInt
    price: float = Field(gt=0)
    timestamp: datetime


class Order(BaseModel):
    """Order state model."""

    order_id: str
    request: OrderRequest
    status: OrderStatus
    filled_quantity: int = 0
    average_fill_price: float | None = Field(default=None, gt=0)
    reject_reason: str | None = None


class Position(BaseModel):
    """Position state model."""

    instrument_id: str
    quantity: int
    average_price: float = Field(ge=0)


class RiskDecision(BaseModel):
    """Result of risk checks."""

    allowed: bool
    reason: str | None = None
