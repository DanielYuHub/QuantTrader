"""Models for strategy signals, targets, runtime context, and events."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from quant_trader.market_data.models import OptionChain
from quant_trader.models.common import AssetClass, Side


class StrategyMode(StrEnum):
    """Strategy runtime mode."""

    BACKTEST = "BACKTEST"
    PAPER = "PAPER"
    LIVE = "LIVE"


class StrategyEvent(BaseModel):
    """Event-driven market input consumed by strategies."""

    timestamp: datetime
    instrument_id: str
    price: float = Field(gt=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class StrategyScheduleEvent(BaseModel):
    """Scheduled clock trigger event."""

    timestamp: datetime
    trigger_name: str


class StrategyContext(BaseModel):
    """Runtime context shared with strategy logic."""

    mode: StrategyMode
    positions: dict[str, int] = Field(default_factory=dict)
    option_chains: dict[str, OptionChain] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class StrategySignal(BaseModel):
    """Alpha signal model, intentionally separate from execution order models."""

    strategy_id: str
    timestamp: datetime
    instrument_id: str
    asset_class: AssetClass
    side: Side
    strength: float = Field(ge=0.0, le=1.0)
    reason: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class PositionTarget(BaseModel):
    """Portfolio construction output and execution handoff payload."""

    strategy_id: str
    instrument_id: str
    asset_class: AssetClass
    target_quantity: int
    max_slippage_bps: float = Field(default=25.0, ge=0.0)
    metadata: dict[str, Any] = Field(default_factory=dict)
