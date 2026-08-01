import math
import logging
from datetime import datetime, timezone
from typing import Dict, Any
from services.price_manager.market_status_service import get_market_status_service

logger = logging.getLogger(__name__)

class PriceValidator:
    """
    Validates stock price records to reject corrupt, stale, or anomalous data
    before it is exposed to the UI or strategy engine.
    """
    
    MAX_CHANGE_PCT_LIMIT = 21.0  # standard circuit limit (20%) + tolerance
    MAX_AGE_SECONDS = 60.0       # Max age allowed for live pricing during open hours

    def __init__(self):
        self._status_service = get_market_status_service()

    def validate_price_dict(self, symbol: str, data: Dict[str, Any]) -> bool:
        """
        Validate raw dictionary fields from API/Cache before constructing DTO.
        """
        try:
            # 1. Null / Type Checks
            if not symbol or not data:
                return False
                
            ltp = data.get("ltp") or data.get("price") or data.get("last_price")
            prev_close = data.get("prev_close") or data.get("previous_close") or data.get("close_price")
            
            if ltp is None or prev_close is None:
                logger.warning(f"Validation failed: Null price/prev_close for {symbol}")
                return False
                
            # 2. Convert to float and check for NaN or infinite
            try:
                ltp = float(ltp)
                prev_close = float(prev_close)
            except (ValueError, TypeError):
                logger.warning(f"Validation failed: Non-numeric price fields for {symbol}")
                return False
                
            if math.isnan(ltp) or math.isinf(ltp) or math.isnan(prev_close) or math.isinf(prev_close):
                logger.warning(f"Validation failed: NaN/Inf detected for {symbol}")
                return False
                
            # 3. Negatives / Zeroes check
            if ltp <= 0.0 or prev_close <= 0.0:
                # India VIX can be volatile but shouldn't be negative or zero.
                logger.warning(f"Validation failed: Price <= 0 for {symbol} (LTP={ltp}, PrevClose={prev_close})")
                return False
                
            # 4. Circuit limit anomaly check (wild price jumps)
            if prev_close > 0:
                change_pct = abs(((ltp - prev_close) / prev_close) * 100.0)
                if change_pct > self.MAX_CHANGE_PCT_LIMIT:
                    logger.warning(f"Validation failed: Circuit limit anomaly for {symbol} ({change_pct:.2f}%)")
                    return False
                    
            # 5. Freshness Check (Only during open trading session)
            if self._status_service.is_live_session():
                ts_str = data.get("timestamp")
                if ts_str:
                    try:
                        # Standardize parse
                        if isinstance(ts_str, (int, float)):
                            ts = datetime.fromtimestamp(ts_str / 1000.0, tz=timezone.utc)
                        else:
                            ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                        
                        age = (datetime.now(timezone.utc) - ts).total_seconds()
                        if age > self.MAX_AGE_SECONDS:
                            logger.warning(f"Validation failed: Stale tick for {symbol} (age={age:.1f}s > {self.MAX_AGE_SECONDS}s)")
                            return False
                    except Exception as e:
                        logger.warning(f"Validation warning: Failed to parse timestamp for freshness check on {symbol}: {e}")
                        
            return True
        except Exception as e:
            logger.error(f"Validator: Unexpected error validating {symbol}: {e}")
            return False

_price_validator = None

def get_price_validator() -> PriceValidator:
    global _price_validator
    if _price_validator is None:
        _price_validator = PriceValidator()
    return _price_validator
