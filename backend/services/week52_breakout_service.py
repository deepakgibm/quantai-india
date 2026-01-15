"""
52-Week Breakout Service
Detects stocks making new 52-week highs and 52-week low breakdowns.
Uses daily candles with minimum 252 trading days of data.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import psycopg2
from config import settings
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class Week52BreakoutStock:
    """Data contract for 52-week breakout stocks."""
    symbol: str
    ltp: float              # Last traded price (latest close)
    high_52w: float         # 52-week high
    low_52w: float          # 52-week low
    prev_close: float       # Previous day close
    change_pct: float       # Daily change percent
    breakout_type: str      # "HIGH_BREAKOUT" or "LOW_BREAKDOWN"
    breakout_pct: float     # % above 52-week high or % below 52-week low
    days_data: int          # Number of trading days used for calculation
    volume: int             # Latest volume
    avg_volume: float       # Average volume (20-day)
    volume_ratio: float     # Today's volume vs average
    industry: str           # Industry sector
    last_update: str        # Timestamp
    
    def to_dict(self) -> Dict:
        return asdict(self)


class Week52BreakoutService:
    """
    Detects 52-week high breakouts and low breakdowns.
    Uses nifty100_daily table (can be extended to Nifty 500 when data is available).
    """
    
    DB_PATH = "quantai.db"
    MIN_TRADING_DAYS = 200  # Minimum ~1 year of trading days (252 ideal, but 200 acceptable)
    
    def __init__(self):
        self._cache: Dict[str, List[Dict]] = {
            "high_breakouts": [],
            "low_breakdowns": []
        }
        self._last_fetch: Optional[datetime] = None
        
    def _get_connection(self):
        """Get database connection."""
        try:
            if "postgresql" in settings.DATABASE_URL:
                result = urlparse(settings.DATABASE_URL.replace("+asyncpg", ""))
                return psycopg2.connect(
                    host=result.hostname or 'localhost',
                    port=result.port or 5432,
                    user=result.username or 'postgres',
                    password=result.password or 'admin',
                    database=result.path.lstrip('/') or 'quantai'
                )
            else:
                return None
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            return None
    
    def detect_breakouts(self) -> Dict[str, List[Dict]]:
        """
        Detect 52-week high breakouts and low breakdowns.
        
        Returns:
            Dict with "high_breakouts" and "low_breakdowns" lists
        """
        conn = self._get_connection()
        if not conn:
            logger.error("Could not connect to database")
            return {"high_breakouts": [], "low_breakdowns": []}
        
        high_breakouts = []
        low_breakdowns = []
        
        try:
            cursor = conn.cursor()
            
            # Get all symbols with sufficient data
            cursor.execute(f"""
                SELECT symbol, COUNT(*) as days
                FROM stock_candles
                WHERE timeframe = '1d'
                GROUP BY symbol
                HAVING days >= {self.MIN_TRADING_DAYS}
            """)
            valid_symbols = {row[0]: row[1] for row in cursor.fetchall()}
            
            logger.info(f"Found {len(valid_symbols)} symbols with >= {self.MIN_TRADING_DAYS} days of data")
            
            # For each symbol, analyze 52-week high/low
            for symbol, days_count in valid_symbols.items():
                try:
                    # Get the last 2 trading days for comparison
                    cursor.execute("""
                        SELECT timestamp, open, high, low, close, volume
                        FROM stock_candles
                        WHERE symbol = %s AND timeframe = '1d'
                        ORDER BY timestamp DESC
                        LIMIT 2
                    """, (symbol,))
                    
                    recent = cursor.fetchall()
                    if len(recent) < 2:
                        continue
                    
                    latest = recent[0]
                    prev = recent[1]
                    
                    timestamp, open_p, today_high, today_low, ltp, volume = latest
                    prev_close = prev[4]  # Previous day close
                    
                    # Get 52-week high and low (excluding today to detect NEW breakouts)
                    cursor.execute("""
                        SELECT MAX(high), MIN(low)
                        FROM stock_candles
                        WHERE symbol = %s AND timeframe = '1d'
                        AND timestamp < %s
                        AND timestamp >= (%s::timestamp - interval '365 days')
                    """, (symbol, timestamp, timestamp))
                    
                    stats = cursor.fetchone()
                    if not stats or stats[0] is None:
                        continue
                    
                    past_high_52w, past_low_52w = stats
                    
                    # Get 20-day average volume
                    cursor.execute("""
                        SELECT AVG(volume)
                        FROM (
                            SELECT volume FROM stock_candles
                            WHERE symbol = %s AND timeframe = '1d'
                            ORDER BY timestamp DESC
                            LIMIT 20
                        ) as subquery
                    """, (symbol,))
                    avg_vol = cursor.fetchone()[0] or volume
                    
                    # Calculate metrics
                    change_pct = ((ltp - prev_close) / prev_close * 100) if prev_close > 0 else 0
                    volume_ratio = (volume / avg_vol) if avg_vol > 0 else 1.0
                    
                    # Check for 52-week high breakout (today's high exceeds past 52-week high)
                    if today_high > past_high_52w:
                        breakout_pct = ((today_high - past_high_52w) / past_high_52w * 100) if past_high_52w > 0 else 0
                        
                        breakout = Week52BreakoutStock(
                            symbol=symbol,
                            ltp=round(ltp, 2),
                            high_52w=round(past_high_52w, 2),
                            low_52w=round(past_low_52w, 2),
                            prev_close=round(prev_close, 2),
                            change_pct=round(change_pct, 2),
                            breakout_type="HIGH_BREAKOUT",
                            breakout_pct=round(breakout_pct, 2),
                            days_data=days_count,
                            volume=int(volume),
                            avg_volume=round(avg_vol, 0),
                            volume_ratio=round(volume_ratio, 2),
                            industry="Nifty Stock",
                            last_update=str(timestamp)
                        )
                        high_breakouts.append(breakout.to_dict())
                    
                    # Check for 52-week low breakdown (today's low goes below past 52-week low)
                    if today_low < past_low_52w:
                        breakdown_pct = ((past_low_52w - today_low) / past_low_52w * 100) if past_low_52w > 0 else 0
                        
                        breakdown = Week52BreakoutStock(
                            symbol=symbol,
                            ltp=round(ltp, 2),
                            high_52w=round(past_high_52w, 2),
                            low_52w=round(past_low_52w, 2),
                            prev_close=round(prev_close, 2),
                            change_pct=round(change_pct, 2),
                            breakout_type="LOW_BREAKDOWN",
                            breakout_pct=round(breakdown_pct, 2),
                            days_data=days_count,
                            volume=int(volume),
                            avg_volume=round(avg_vol, 0),
                            volume_ratio=round(volume_ratio, 2),
                            industry="Nifty Stock",
                            last_update=str(timestamp)
                        )
                        low_breakdowns.append(breakdown.to_dict())
                        
                except Exception as e:
                    logger.warning(f"Error processing {symbol}: {e}")
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
            
            logger.info(f"Found {len(high_breakouts)} 52-week high breakouts, {len(low_breakdowns)} 52-week low breakdowns")
            
        except Exception as e:
            logger.error(f"Breakout detection error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            conn.close()
        
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
            "min_trading_days": self.MIN_TRADING_DAYS
        }


# Singleton instance
_week52_service = None


def get_week52_breakout_service() -> Week52BreakoutService:
    """Get singleton 52-Week Breakout Service instance."""
    global _week52_service
    if _week52_service is None:
        _week52_service = Week52BreakoutService()
    return _week52_service
