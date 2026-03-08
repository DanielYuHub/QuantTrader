"""Domain DTOs for provider-agnostic market data handling."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Market(StrEnum):
    """Supported markets in Phase 2 market data layer."""

    US = "US"
    HK = "HK"


class AssetType(StrEnum):
    """Supported instrument types."""

    EQUITY = "EQUITY"
    OPTION = "OPTION"


class OptionRight(StrEnum):
    """Option contract right."""

    CALL = "CALL"
    PUT = "PUT"


class InstrumentRef(BaseModel):
    """Canonical normalized instrument reference."""

    symbol: str
    market: Market
    asset_type: AssetType
    currency: str


class OptionContract(BaseModel):
    """Option contract definition normalized across providers."""

    contract_symbol: str
    underlying_symbol: str
    market: Market
    expiry: datetime
    strike: float = Field(gt=0)
    right: OptionRight
    multiplier: int = Field(default=100, gt=0)
    exchange: str | None = None


class Quote(BaseModel):
    """Normalized quote model with timezone-aware timestamps."""

    symbol: str
    market: Market
    timestamp: datetime
    bid: float = Field(ge=0)
    ask: float = Field(ge=0)
    last: float | None = Field(default=None, ge=0)
    bid_size: int | None = Field(default=None, ge=0)
    ask_size: int | None = Field(default=None, ge=0)


class Bar(BaseModel):
    """Normalized OHLCV bar model."""

    symbol: str
    market: Market
    timestamp: datetime
    open: float = Field(ge=0)
    high: float = Field(ge=0)
    low: float = Field(ge=0)
    close: float = Field(ge=0)
    volume: float = Field(ge=0)


class OptionGreeks(BaseModel):
    """Normalized option greeks snapshot if provider supplies it."""

    iv: float | None = Field(default=None, ge=0)
    delta: float | None = None
    gamma: float | None = None
    theta: float | None = None
    vega: float | None = None
    rho: float | None = None


class OptionChainEntry(BaseModel):
    """Option chain row with optional greek fields."""

    contract: OptionContract
    quote: Quote | None = None
    greeks: OptionGreeks | None = None
    open_interest: int | None = Field(default=None, ge=0)
    implied_volatility: float | None = Field(default=None, ge=0)


class OptionChain(BaseModel):
    """Option chain snapshot for one underlying."""

    underlying_symbol: str
    market: Market
    timestamp: datetime
    entries: list[OptionChainEntry]


class CorporateActionType(StrEnum):
    """Corporate action categories."""

    DIVIDEND = "DIVIDEND"
    SPLIT = "SPLIT"
    MERGER = "MERGER"
    SPINOFF = "SPINOFF"


class CorporateAction(BaseModel):
    """Corporate action event for an equity instrument."""

    symbol: str
    market: Market
    action_type: CorporateActionType
    ex_date: datetime
    pay_date: datetime | None = None
    value: float | None = None
    description: str | None = None
