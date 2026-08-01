from datetime import time
from services.market_hours_service import get_market_hours_service, NSE_HOLIDAYS
from services.price_manager.models import MarketStatus

class MarketStatusService:
    """
    Standardized authority for checking market session status (PRE_OPEN, OPEN, CLOSED, HOLIDAY, WEEKEND, AFTER_MARKET).
    Consumes rules directly from MarketHoursService.
    """
    
    def __init__(self):
        self._market_hours = get_market_hours_service()

    def get_status(self) -> MarketStatus:
        now_ist = self._market_hours._get_ist_now()
        today = now_ist.date()
        
        # 1. Check if Weekend
        if today.weekday() >= 5:
            return MarketStatus.WEEKEND
            
        # 2. Check if Holiday
        if today in NSE_HOLIDAYS:
            return MarketStatus.HOLIDAY
            
        current_time = now_ist.time()
        
        # 3. Check Pre-Open (09:00 - 09:15 IST)
        if time(9, 0) <= current_time < time(9, 15):
            return MarketStatus.PRE_OPEN
            
        # 4. Check Open Trading Session (09:15 - 15:30 IST)
        if time(9, 15) <= current_time <= time(15, 30):
            return MarketStatus.OPEN
            
        # 5. Check After Market / Post-Close (15:30 - 16:00 IST)
        if time(15, 30) < current_time <= time(16, 0):
            return MarketStatus.AFTER_MARKET
            
        # 6. Default Closed
        return MarketStatus.CLOSED

    def is_live_session(self) -> bool:
        """Helper to check if websocket live feed should be active."""
        return self.get_status() == MarketStatus.OPEN

_market_status_service = None

def get_market_status_service() -> MarketStatusService:
    global _market_status_service
    if _market_status_service is None:
        _market_status_service = MarketStatusService()
    return _market_status_service
