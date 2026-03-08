"""Trading calendar and timezone utilities for US and HK markets."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from zoneinfo import ZoneInfo

from quant_trader.market_data.models import Market


@dataclass(frozen=True)
class TradingSession:
    """Regular trading session metadata for a market."""

    market: Market
    timezone: ZoneInfo
    open_time: time
    close_time: time
    holidays: set[str] = field(default_factory=set)


class TradingCalendar:
    """Calendar-aware utility for session checks and timezone conversion."""

    def __init__(self) -> None:
        """Initialize market sessions with regular trading hours."""

        self._sessions: dict[Market, TradingSession] = {
            Market.US: TradingSession(
                market=Market.US,
                timezone=ZoneInfo("America/New_York"),
                open_time=time(hour=9, minute=30),
                close_time=time(hour=16, minute=0),
            ),
            Market.HK: TradingSession(
                market=Market.HK,
                timezone=ZoneInfo("Asia/Hong_Kong"),
                open_time=time(hour=9, minute=30),
                close_time=time(hour=16, minute=0),
            ),
        }

    def session(self, market: Market) -> TradingSession:
        """Return session metadata for a market."""

        return self._sessions[market]

    def convert_timestamp(self, timestamp: datetime, market: Market) -> datetime:
        """Convert timestamp to market-local timezone.

        Naive timestamps are treated as UTC.
        """

        session = self.session(market)
        ts = timestamp.replace(tzinfo=ZoneInfo("UTC")) if timestamp.tzinfo is None else timestamp
        return ts.astimezone(session.timezone)

    def is_trading_day(self, timestamp: datetime, market: Market) -> bool:
        """Return whether timestamp falls on an active trading day."""

        local_ts = self.convert_timestamp(timestamp, market)
        date_key = local_ts.date().isoformat()
        if local_ts.weekday() >= 5:
            return False
        return date_key not in self.session(market).holidays

    def is_regular_session_open(self, timestamp: datetime, market: Market) -> bool:
        """Return whether timestamp is within regular market session."""

        if not self.is_trading_day(timestamp, market):
            return False
        session = self.session(market)
        local_ts = self.convert_timestamp(timestamp, market)
        current = local_ts.timetz().replace(tzinfo=None)
        return session.open_time <= current <= session.close_time
