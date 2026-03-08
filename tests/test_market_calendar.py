"""Tests for trading calendar utilities."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from quant_trader.market_data.calendar import TradingCalendar
from quant_trader.market_data.models import Market



def test_convert_timestamp_to_market_timezone() -> None:
    """Calendar should convert UTC timestamp to market local timezone."""

    calendar = TradingCalendar()
    ts = datetime(2025, 1, 2, 15, 0, tzinfo=ZoneInfo("UTC"))

    local = calendar.convert_timestamp(ts, Market.US)

    assert local.tzinfo is not None
    assert local.tzinfo.key == "America/New_York"



def test_session_open_for_hk_regular_hours() -> None:
    """Calendar should identify regular HK session hours."""

    calendar = TradingCalendar()
    hk_time = datetime(2025, 1, 2, 10, 0, tzinfo=ZoneInfo("Asia/Hong_Kong"))

    assert calendar.is_regular_session_open(hk_time, Market.HK)
