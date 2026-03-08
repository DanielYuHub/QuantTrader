"""Tests for market data service behaviors."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from quant_trader.interfaces.market_data import MarketDataProviderInterface
from quant_trader.market_data.cache import TTLCache
from quant_trader.market_data.calendar import TradingCalendar
from quant_trader.market_data.models import (
    AssetType,
    Bar,
    CorporateAction,
    CorporateActionType,
    InstrumentRef,
    Market,
    OptionChain,
    OptionChainEntry,
    OptionContract,
    OptionGreeks,
    OptionRight,
    Quote,
)
from quant_trader.market_data.service import MarketDataService, MarketDataServiceConfig
from quant_trader.market_data.symbols import SymbolNormalizer
from quant_trader.utils.resilience import RetryPolicy


class FlakyProvider(MarketDataProviderInterface):
    """Provider used to verify retry and cache behavior."""

    def __init__(self) -> None:
        self.quote_attempts = 0

    @property
    def provider_name(self) -> str:
        return "flaky"

    def list_instruments(self, market: Market, include_options: bool = True) -> list[InstrumentRef]:
        return [
            InstrumentRef(symbol="AAPL", market=Market.US, asset_type=AssetType.EQUITY, currency="USD"),
        ]

    def get_realtime_quote(self, symbol: str, market: Market) -> Quote:
        self.quote_attempts += 1
        if self.quote_attempts == 1:
            raise RuntimeError("transient provider error")
        return Quote(
            symbol=symbol,
            market=market,
            timestamp=datetime(2025, 1, 2, 15, 0, tzinfo=ZoneInfo("UTC")),
            bid=100.0,
            ask=100.2,
            last=100.1,
        )

    def get_historical_bars(
        self,
        symbol: str,
        market: Market,
        start: datetime,
        end: datetime,
        timeframe: str,
    ) -> list[Bar]:
        return [
            Bar(
                symbol=symbol,
                market=market,
                timestamp=start,
                open=99.0,
                high=101.0,
                low=98.5,
                close=100.0,
                volume=1_000_000,
            )
        ]

    def get_option_chain(self, underlying_symbol: str, market: Market, as_of: datetime | None = None) -> OptionChain:
        contract = OptionContract(
            contract_symbol="AAPL250117C00100000",
            underlying_symbol=underlying_symbol,
            market=market,
            expiry=datetime(2025, 1, 17, tzinfo=ZoneInfo("UTC")),
            strike=100.0,
            right=OptionRight.CALL,
        )
        entry = OptionChainEntry(
            contract=contract,
            quote=Quote(
                symbol=contract.contract_symbol,
                market=market,
                timestamp=datetime(2025, 1, 2, 15, 0, tzinfo=ZoneInfo("UTC")),
                bid=2.1,
                ask=2.2,
                last=2.15,
            ),
            greeks=OptionGreeks(iv=0.25, delta=0.52, gamma=0.04, theta=-0.01, vega=0.12),
            implied_volatility=0.25,
        )
        return OptionChain(
            underlying_symbol=underlying_symbol,
            market=market,
            timestamp=datetime(2025, 1, 2, 15, 0, tzinfo=ZoneInfo("UTC")),
            entries=[entry],
        )

    def get_corporate_actions(
        self,
        symbol: str,
        market: Market,
        start: datetime,
        end: datetime,
    ) -> list[CorporateAction]:
        action = CorporateAction(
            symbol=symbol,
            market=market,
            action_type=CorporateActionType.DIVIDEND,
            ex_date=start + timedelta(days=1),
            value=0.25,
            description="Quarterly dividend",
        )
        return [action]



def _build_service(provider: MarketDataProviderInterface) -> MarketDataService:
    return MarketDataService(
        provider=provider,
        calendar=TradingCalendar(),
        symbol_normalizer=SymbolNormalizer(),
        cache=TTLCache(),
        config=MarketDataServiceConfig(
            timeout_seconds=0.5,
            retry_policy=RetryPolicy(attempts=2, delay_seconds=0.0),
            quote_ttl_seconds=60,
            chain_ttl_seconds=60,
        ),
    )



def test_quote_retries_and_is_cached() -> None:
    """Service should retry transient failures and cache successful quote."""

    provider = FlakyProvider()
    service = _build_service(provider)

    first = service.quote("aapl", Market.US)
    second = service.quote("AAPL", Market.US)

    assert first.symbol == "AAPL"
    assert second.symbol == "AAPL"
    assert provider.quote_attempts == 2



def test_option_chain_contains_iv_and_greeks_when_available() -> None:
    """Chain retrieval should preserve optional IV/greek fields."""

    service = _build_service(FlakyProvider())
    chain = service.option_chain("AAPL", Market.US)

    assert chain.entries[0].implied_volatility == pytest.approx(0.25)
    assert chain.entries[0].greeks is not None
    assert chain.entries[0].greeks.delta == pytest.approx(0.52)



def test_historical_bars_and_corporate_actions_supported() -> None:
    """Service should return bars and corporate actions from provider."""

    service = _build_service(FlakyProvider())
    start = datetime(2025, 1, 1, tzinfo=ZoneInfo("UTC"))
    end = datetime(2025, 1, 3, tzinfo=ZoneInfo("UTC"))

    bars = service.historical_bars("AAPL", Market.US, start, end, "1d")
    actions = service.corporate_actions("AAPL", Market.US, start, end)

    assert len(bars) == 1
    assert bars[0].close == pytest.approx(100.0)
    assert len(actions) == 1
    assert actions[0].action_type == CorporateActionType.DIVIDEND
