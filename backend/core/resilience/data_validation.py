import logging
from typing import Dict, Any, Tuple, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from models import MarketDataQuarantine

logger = logging.getLogger(__name__)

class DataValidationEngine:
    """
    Validates market data ticks and candles before they are written to the main DB.
    Quarantines invalid data.
    """
    def __init__(self, db: Session):
        self.db = db

    def validate_and_quarantine(self, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validates the data. If invalid/anomalous, stores in quarantine DB.
        Returns: (is_valid: bool, rejection_reason: Optional[str])
        """
        symbol = params.get("symbol")
        high = params.get("high", 0)
        low = params.get("low", 0)
        open_price = params.get("open", 0)
        close_price = params.get("close", 0)
        volume = params.get("volume", 0)
        
        rejection_reason = None
        
        # 1. Negative or Zero Value Checks
        if open_price <= 0 or close_price <= 0 or high <= 0 or low <= 0:
            rejection_reason = "NEGATIVE_OR_ZERO_PRICE"
            
        # 2. Structural OHLC Bounds Check
        elif high < low:
            rejection_reason = "HIGH_LESS_THAN_LOW"
        elif high < open_price or high < close_price:
            rejection_reason = "HIGH_LESS_THAN_OPEN_OR_CLOSE"
        elif low > open_price or low > close_price:
            rejection_reason = "LOW_GREATER_THAN_OPEN_OR_CLOSE"
            
        if rejection_reason:
            self._save_to_quarantine(params, rejection_reason)
            logger.warning(f"Validation FAILED for {symbol}: {rejection_reason}")
            return False, rejection_reason

        return True, None

    def check_anomaly(self, params: Dict[str, Any], avg_volume_14d: float) -> bool:
        """
        Checks for non-fatal anomalies (like extreme volume spikes or splits/bonus logic).
        Returns True if anomalous without rejecting it from the main database.
        """
        volume = params.get("volume", 0)
        symbol = params.get("symbol")
        
        # E.g. Splitting or Bonus might show an extreme gap down and volume up
        # If Volume is 15x normal, flag it as anomalous
        if avg_volume_14d > 0 and volume > (avg_volume_14d * 15):
             logger.info(f"ANOMALY EVENT: {symbol} triggered a 15x volume spike ({volume})")
             # Here we could publish an event to EventBridge or Redis
             return True
             
        return False
        
    def filter_split_bonus_adjustments(self, df: Any):
        """
        Handles exception for historical split/bonus adjustments.
        (Placeholder for Polars/Pandas transformations on historical sets.)
        """
        # Logic to adjust historical arrays backwards given a multiplier
        pass

    def _save_to_quarantine(self, params: Dict[str, Any], reason: str):
        quarantine = MarketDataQuarantine(
            symbol=params.get("symbol"),
            timestamp=params.get("timestamp", datetime.utcnow()),
            timeframe=params.get("timeframe"),
            open=params.get("open"),
            high=params.get("high"),
            low=params.get("low"),
            close=params.get("close"),
            volume=params.get("volume"),
            rejection_reason=reason
        )
        self.db.add(quarantine)
        try:
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to write to quarantine DB: {e}")
            self.db.rollback()
