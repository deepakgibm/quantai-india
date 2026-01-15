"""
Market Hours Service
Detects NSE market hours and trading status for intelligent data sourcing.

NSE Market Hours:
- Pre-Open: 09:00 - 09:15 IST
- Normal Trading: 09:15 - 15:30 IST
- Post-Close: 15:30 - 16:00 IST (optional)

Trading Days: Monday to Friday (excludes NSE holidays)
"""

import logging
from datetime import datetime, time, date, timedelta
from typing import Optional, Tuple
import os

logger = logging.getLogger(__name__)

# Try to import pytz for timezone handling
try:
    import pytz
    IST = pytz.timezone('Asia/Kolkata')
    PYTZ_AVAILABLE = True
except ImportError:
    IST = None
    PYTZ_AVAILABLE = False
    logger.warning("pytz not available, using system time (assumes IST)")


# =============================================================================
# NSE Holiday Calendar (2025-2026)
# =============================================================================
NSE_HOLIDAYS_2025 = {
    date(2025, 1, 26),   # Republic Day
    date(2025, 2, 26),   # Mahashivratri
    date(2025, 3, 14),   # Holi
    date(2025, 3, 31),   # Eid-ul-Fitr
    date(2025, 4, 10),   # Ram Navami
    date(2025, 4, 14),   # Ambedkar Jayanti
    date(2025, 4, 18),   # Good Friday
    date(2025, 5, 1),    # May Day
    date(2025, 6, 7),    # Eid-ul-Adha
    date(2025, 8, 15),   # Independence Day
    date(2025, 8, 27),   # Janmashtami
    date(2025, 10, 2),   # Gandhi Jayanti
    date(2025, 10, 21),  # Diwali (Laxmi Puja)
    date(2025, 10, 22),  # Diwali (Balipratipada)
    date(2025, 11, 5),   # Guru Nanak Jayanti
    date(2025, 12, 25),  # Christmas
}

NSE_HOLIDAYS_2026 = {
    date(2026, 1, 26),   # Republic Day
    date(2026, 3, 17),   # Holi
    date(2026, 4, 3),    # Good Friday
    date(2026, 4, 14),   # Ambedkar Jayanti
    date(2026, 5, 1),    # May Day
    date(2026, 8, 15),   # Independence Day
    date(2026, 10, 2),   # Gandhi Jayanti
    date(2026, 11, 9),   # Diwali
    date(2026, 12, 25),  # Christmas
}

NSE_HOLIDAYS = NSE_HOLIDAYS_2025 | NSE_HOLIDAYS_2026


class MarketHoursService:
    """
    Detects NSE market hours and trading status.
    
    Usage:
        service = MarketHoursService()
        if service.is_market_open():
            # Use WebSocket for live data
        else:
            # Use REST API for EOD data
    """
    
    # NSE Trading Hours (IST)
    MARKET_OPEN = time(9, 15)    # 09:15 IST
    MARKET_CLOSE = time(15, 30)  # 15:30 IST
    
    # Pre-market session (optional)
    PRE_OPEN_START = time(9, 0)   # 09:00 IST
    PRE_OPEN_END = time(9, 15)    # 09:15 IST
    
    def __init__(self):
        self._cached_trading_date: Optional[str] = None
        self._cache_date: Optional[date] = None
    
    def _get_ist_now(self) -> datetime:
        """Get current time in IST timezone."""
        if PYTZ_AVAILABLE and IST:
            return datetime.now(IST)
        else:
            # Fallback: assume system is in IST
            return datetime.now()
    
    def is_trading_day(self, check_date: Optional[date] = None) -> bool:
        """
        Check if the given date is a trading day.
        
        Excludes:
        - Weekends (Saturday, Sunday)
        - NSE holidays
        """
        if check_date is None:
            check_date = self._get_ist_now().date()
        
        # Check weekend
        if check_date.weekday() >= 5:  # Saturday=5, Sunday=6
            return False
        
        # Check NSE holidays
        if check_date in NSE_HOLIDAYS:
            return False
        
        return True
    
    def is_market_open(self) -> bool:
        """
        Check if NSE market is currently open for trading.
        
        Returns True during normal trading hours (09:15 - 15:30 IST)
        on trading days only.
        """
        now = self._get_ist_now()
        
        # Not a trading day
        if not self.is_trading_day(now.date()):
            return False
        
        # Check time
        current_time = now.time()
        return self.MARKET_OPEN <= current_time <= self.MARKET_CLOSE
    
    def is_pre_market(self) -> bool:
        """Check if in pre-market session (09:00 - 09:15 IST)."""
        now = self._get_ist_now()
        
        if not self.is_trading_day(now.date()):
            return False
        
        current_time = now.time()
        return self.PRE_OPEN_START <= current_time < self.PRE_OPEN_END
    
    def get_trading_date(self) -> str:
        """
        Get the current or most recent trading date.
        
        Returns date in format: "2026-01-02"
        
        Logic:
        - During market hours: Returns today
        - After market close: Returns today
        - Before market open: Returns previous trading day
        - Weekends/holidays: Returns last trading day
        """
        now = self._get_ist_now()
        today = now.date()
        
        # Cache check
        if self._cache_date == today and self._cached_trading_date:
            return self._cached_trading_date
        
        current_time = now.time()
        
        # If market is open or after close, use today (if trading day)
        if self.is_trading_day(today):
            if current_time >= self.MARKET_OPEN:
                self._cached_trading_date = today.isoformat()
                self._cache_date = today
                return self._cached_trading_date
        
        # Find the most recent trading day
        check_date = today
        for _ in range(7):  # Max 7 days back (worst case: long weekend + holiday)
            check_date -= timedelta(days=1)
            if self.is_trading_day(check_date):
                self._cached_trading_date = check_date.isoformat()
                self._cache_date = today
                return self._cached_trading_date
        
        # Fallback (shouldn't happen)
        self._cached_trading_date = today.isoformat()
        self._cache_date = today
        return self._cached_trading_date
    
    def time_to_open(self) -> int:
        """
        Get seconds until market opens.
        
        Returns:
            - Positive: Seconds until open
            - 0 or negative: Market is already open
        """
        now = self._get_ist_now()
        
        if not self.is_trading_day(now.date()):
            # Find next trading day
            next_trading = self._get_next_trading_day()
            market_open_dt = datetime.combine(next_trading, self.MARKET_OPEN)
            if PYTZ_AVAILABLE and IST:
                market_open_dt = IST.localize(market_open_dt)
            return int((market_open_dt - now).total_seconds())
        
        market_open_dt = datetime.combine(now.date(), self.MARKET_OPEN)
        if PYTZ_AVAILABLE and IST:
            market_open_dt = IST.localize(market_open_dt)
        
        diff = (market_open_dt - now).total_seconds()
        return max(0, int(diff))
    
    def time_to_close(self) -> int:
        """
        Get seconds until market closes.
        
        Returns:
            - Positive: Seconds until close
            - 0 or negative: Market is already closed
        """
        now = self._get_ist_now()
        
        if not self.is_market_open():
            return 0
        
        market_close_dt = datetime.combine(now.date(), self.MARKET_CLOSE)
        if PYTZ_AVAILABLE and IST:
            market_close_dt = IST.localize(market_close_dt)
        
        diff = (market_close_dt - now).total_seconds()
        return max(0, int(diff))
    
    def _get_next_trading_day(self) -> date:
        """Get the next trading day from today."""
        check_date = self._get_ist_now().date()
        for _ in range(7):
            check_date += timedelta(days=1)
            if self.is_trading_day(check_date):
                return check_date
        return check_date  # Fallback
    
    def get_market_status(self) -> dict:
        """
        Get comprehensive market status.
        
        Returns:
            {
                "is_open": bool,
                "is_trading_day": bool,
                "is_pre_market": bool,
                "trading_date": "2026-01-02",
                "time_to_open": 3600,
                "time_to_close": 0,
                "current_time_ist": "21:59:53"
            }
        """
        now = self._get_ist_now()
        
        return {
            "is_open": self.is_market_open(),
            "is_trading_day": self.is_trading_day(),
            "is_pre_market": self.is_pre_market(),
            "trading_date": self.get_trading_date(),
            "time_to_open": self.time_to_open(),
            "time_to_close": self.time_to_close(),
            "current_time_ist": now.strftime("%H:%M:%S")
        }


# =============================================================================
# Singleton Instance
# =============================================================================
_market_hours_service: Optional[MarketHoursService] = None


def get_market_hours_service() -> MarketHoursService:
    """Get the singleton MarketHoursService instance."""
    global _market_hours_service
    if _market_hours_service is None:
        _market_hours_service = MarketHoursService()
    return _market_hours_service
