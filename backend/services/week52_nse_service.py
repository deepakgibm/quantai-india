"""
52-Week Breakout Service using NSETools
Fetches real-time 52-week high and low stocks directly from NSE.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from nsetools import Nse

logger = logging.getLogger(__name__)


@dataclass
class Week52BreakoutStock:
    """Data contract for 52-week breakout stocks."""
    symbol: str
    ltp: float              # Last traded price / new 52W high/low value
    high_52w: float         # 52-week high (new value)
    low_52w: float          # 52-week low (prev value for reference)
    prev_close: float       # Previous 52W high/low value
    change_pct: float       # Percentage change from prev 52W high/low
    breakout_type: str      # "HIGH_BREAKOUT" or "LOW_BREAKDOWN"
    breakout_pct: float     # % change from previous 52W level
    days_data: int          # N/A for NSE data (set to 252)
    volume: int             # Volume (if available)
    avg_volume: float       # Average volume
    volume_ratio: float     # Volume ratio
    industry: str           # Industry sector
    last_update: str        # Timestamp
    
    def to_dict(self) -> Dict:
        return asdict(self)


class Week52BreakoutServiceNSE:
    """
    52-Week Breakout Service using NSETools.
    Fetches real-time 52-week high and low lists from NSE.
    """
    
    def __init__(self):
        self._nse = Nse()
        self._cache: Dict[str, List[Dict]] = {
            "high_breakouts": [],
            "low_breakdowns": []
        }
        self._last_fetch: Optional[datetime] = None
        
    def detect_breakouts(self) -> Dict[str, List[Dict]]:
        """
        Fetch 52-week high and low stocks from NSE.
        
        Returns:
            Dict with "high_breakouts" and "low_breakdowns" lists
        """
        high_breakouts = []
        low_breakdowns = []
        
        try:
            # Fetch 52-week high list from NSE
            logger.info("Fetching 52-week high list from NSE...")
            high_list = self._nse.get_52_week_high()
            
            if high_list:
                logger.info(f"Found {len(high_list)} stocks at 52-week high")
                for item in high_list:
                    try:
                        symbol = item.get('symbol', '')
                        new_52w_hl = item.get('new52WHL', 0)
                        prev_52w_hl = item.get('prev52WHL', 0)
                        
                        # Calculate breakout percentage
                        if prev_52w_hl and prev_52w_hl > 0:
                            breakout_pct = ((new_52w_hl - prev_52w_hl) / prev_52w_hl) * 100
                        else:
                            breakout_pct = 0
                        
                        # Get additional stock details if possible
                        try:
                            quote = self._nse.get_quote(symbol)
                            change_pct = quote.get('pChange', 0) if quote else 0
                            volume = quote.get('totalTradedVolume', 0) if quote else 0
                            industry = quote.get('industry', 'N/A') if quote else 'N/A'
                        except:
                            change_pct = 0
                            volume = 0
                            industry = 'N/A'
                        
                        breakout = Week52BreakoutStock(
                            symbol=symbol,
                            ltp=round(new_52w_hl, 2),
                            high_52w=round(new_52w_hl, 2),
                            low_52w=0,  # Not available in this context
                            prev_close=round(prev_52w_hl, 2),
                            change_pct=round(change_pct, 2),
                            breakout_type="HIGH_BREAKOUT",
                            breakout_pct=round(breakout_pct, 2),
                            days_data=252,
                            volume=int(volume),
                            avg_volume=0,
                            volume_ratio=1.0,
                            industry=industry if industry else 'NSE Stock',
                            last_update=datetime.now().isoformat()
                        )
                        high_breakouts.append(breakout.to_dict())
                    except Exception as e:
                        logger.warning(f"Error processing high breakout {item}: {e}")
                        continue
            
            # Fetch 52-week low list from NSE
            logger.info("Fetching 52-week low list from NSE...")
            low_list = self._nse.get_52_week_low()
            
            if low_list:
                logger.info(f"Found {len(low_list)} stocks at 52-week low")
                for item in low_list:
                    try:
                        symbol = item.get('symbol', '')
                        new_52w_hl = item.get('new52WHL', 0)
                        prev_52w_hl = item.get('prev52WHL', 0)
                        
                        # Calculate breakdown percentage
                        if prev_52w_hl and prev_52w_hl > 0:
                            breakdown_pct = ((prev_52w_hl - new_52w_hl) / prev_52w_hl) * 100
                        else:
                            breakdown_pct = 0
                        
                        # Get additional stock details if possible
                        try:
                            quote = self._nse.get_quote(symbol)
                            change_pct = quote.get('pChange', 0) if quote else 0
                            volume = quote.get('totalTradedVolume', 0) if quote else 0
                            industry = quote.get('industry', 'N/A') if quote else 'N/A'
                        except:
                            change_pct = 0
                            volume = 0
                            industry = 'N/A'
                        
                        breakdown = Week52BreakoutStock(
                            symbol=symbol,
                            ltp=round(new_52w_hl, 2),
                            high_52w=0,  # Not available in this context
                            low_52w=round(new_52w_hl, 2),
                            prev_close=round(prev_52w_hl, 2),
                            change_pct=round(change_pct, 2),
                            breakout_type="LOW_BREAKDOWN",
                            breakout_pct=round(breakdown_pct, 2),
                            days_data=252,
                            volume=int(volume),
                            avg_volume=0,
                            volume_ratio=1.0,
                            industry=industry if industry else 'NSE Stock',
                            last_update=datetime.now().isoformat()
                        )
                        low_breakdowns.append(breakdown.to_dict())
                    except Exception as e:
                        logger.warning(f"Error processing low breakdown {item}: {e}")
                        continue
            
            # Sort by breakout percentage (descending)
            high_breakouts.sort(key=lambda x: x['breakout_pct'], reverse=True)
            low_breakdowns.sort(key=lambda x: x['breakout_pct'], reverse=True)
            
            # Cache results
            self._cache = {
                "high_breakouts": high_breakouts,
                "low_breakdowns": low_breakdowns
            }
            self._last_fetch = datetime.now()
            
            logger.info(f"Found {len(high_breakouts)} 52-week high breakouts, {len(low_breakdowns)} 52-week low breakdowns from NSE")
            
        except Exception as e:
            logger.error(f"NSE 52-week data fetch error: {e}")
            import traceback
            traceback.print_exc()
        
        return self._cache
    
    def get_cached_data(self) -> Dict[str, List[Dict]]:
        """Return cached breakout data."""
        return self._cache
    
    def get_status(self) -> Dict:
        """Get service status."""
        return {
            "is_healthy": self._last_fetch is not None,
            "last_fetch": self._last_fetch.isoformat() if self._last_fetch else None,
            "high_breakout_count": len(self._cache.get("high_breakouts", [])),
            "low_breakdown_count": len(self._cache.get("low_breakdowns", [])),
            "source": "NSE",
            "min_trading_days": 252
        }


# Singleton instance
_week52_nse_service = None


def get_week52_breakout_service_nse() -> Week52BreakoutServiceNSE:
    """Get singleton 52-Week Breakout Service (NSE) instance."""
    global _week52_nse_service
    if _week52_nse_service is None:
        _week52_nse_service = Week52BreakoutServiceNSE()
    return _week52_nse_service
