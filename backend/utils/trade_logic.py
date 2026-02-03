import logging
from typing import Dict, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

def validate_directional_consistency(
    is_bullish: bool, 
    price: float, 
    entry: float, 
    target: float, 
    stop_loss: float
) -> Tuple[bool, str]:
    """
    Validates that trade levels follow directional rules.
    - BULLISH: Target > Entry > Stop Loss and Entry >= Price (or breakout)
    - BEARISH: Target < Entry < Stop Loss and Entry <= Price
    """
    if is_bullish:
        if not (target > entry > stop_loss):
            return False, f"Invalid Bullish Levels: T:{target} E:{entry} SL:{stop_loss} (Target must be > Entry > SL)"
    else:
        if not (target < entry < stop_loss):
            return False, f"Invalid Bearish Levels: T:{target} E:{entry} SL:{stop_loss} (Target must be < Entry < SL)"
    
    return True, "Success"

def calculate_rr_ratio(entry: float, target: float, stop_loss: float) -> float:
    """Calculates Risk-Reward ratio."""
    risk = abs(entry - stop_loss)
    reward = abs(target - entry)
    if risk == 0:
        return 0.0
    return round(reward / risk, 2)

def calculate_atr_levels(
    is_bullish: bool,
    base_price: float,
    atr: float,
    target_multiplier: float = 2.0,
    sl_multiplier: float = 1.5
) -> Dict[str, float]:
    """
    Calculates Entry, Target, and SL using ATR.
    - Entry: base_price (breakout level or current price)
    - Target: Entry +/- (ATR * target_multiplier)
    - SL: Entry -/+ (ATR * sl_multiplier)
    """
    entry = base_price
    if is_bullish:
        target = entry + (atr * target_multiplier)
        stop_loss = entry - (atr * sl_multiplier)
    else:
        target = entry - (atr * target_multiplier)
        stop_loss = entry + (atr * sl_multiplier)
        
    return {
        "entry_price": round(entry, 2),
        "target_price": round(target, 2),
        "stop_loss": round(stop_loss, 2)
    }

def is_price_fresh(timestamp_str: Optional[str], max_age_seconds: int = 10) -> bool:
    """Checks if a price tick is fresh (default 10s)."""
    if not timestamp_str:
        return False
        
    try:
        # Handle various ISO formats
        if timestamp_str.endswith('Z'):
            timestamp_str = timestamp_str.replace('Z', '+00:00')
        
        ts = datetime.fromisoformat(timestamp_str)
        
        # Ensure comparison is offset-aware or not
        now = datetime.now(ts.tzinfo) if ts.tzinfo else datetime.now()
        age = (now - ts).total_seconds()
        
        return age <= max_age_seconds
    except Exception as e:
        logger.warning(f"Timestamp check failed: {e}")
        return False
