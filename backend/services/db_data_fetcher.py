"""
Database Data Fetcher Service
Tertiary fallback for when WebSocket and REST API are unavailable.
Uses historical data from the database to provide momentum data during market hours.
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import psycopg2
from config import settings
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class DatabaseTick:
    """Data contract for database-sourced momentum data."""
    symbol: str
    ltp: float           # Last traded price (from latest close)
    prev_close: float    # Previous day close
    change_pct: float    
    bucket: str          # Momentum bucket
    direction: str       # Bullish/Bearish/Neutral
    source: str = "DB"   # Always "DB" for database data
    confidence: str = "LOW"  # Always LOW for historical data
    timestamp: str = ""  # When data was fetched
    data_date: str = ""  # Actual date of the data
    
    def to_dict(self) -> Dict:
        return asdict(self)


def calculate_bucket(change_pct: float) -> Tuple[str, str]:
    """Calculate momentum bucket and direction from percent change."""
    abs_change = abs(change_pct)
    
    if change_pct >= 3.0:
        bucket = "STRONG_BULLISH"
        direction = "Bullish"
    elif change_pct >= 1.5:
        bucket = "MODERATE_BULLISH"
        direction = "Bullish"
    elif change_pct <= -3.0:
        bucket = "STRONG_BEARISH"
        direction = "Bearish"
    elif change_pct <= -1.5:
        bucket = "MODERATE_BEARISH"
        direction = "Bearish"
    else:
        bucket = "NEUTRAL"
        direction = "Neutral"
    
    return bucket, direction


class DatabaseDataFetcher:
    """
    Fetches market data from local database as final fallback.
    Uses Nifty500Daily table for historical close prices.
    """
    
    DB_PATH = "quantai.db"
    
    def __init__(self):
        self._cache: Dict[str, DatabaseTick] = {}
        self._symbols: List[str] = []
        self._last_fetch: Optional[datetime] = None
        
    def _get_connection(self):
        """Get database connection."""
        try:
            if "postgresql" in settings.DATABASE_URL:
                # Parse DATABASE_URL for psycopg2
                result = urlparse(settings.DATABASE_URL.replace("+asyncpg", ""))
                return psycopg2.connect(
                    host=result.hostname or 'localhost',
                    port=result.port or 5432,
                    user=result.username or 'postgres',
                    password=result.password or 'admin',
                    database=result.path.lstrip('/') or 'quantai'
                )
            else:
                # Fallback or other DBs (not expected here based on USER request)
                return None
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            return None
    
    def fetch_latest_data(self, symbols: List[str] = None) -> Dict[str, DatabaseTick]:
        """
        Fetch latest available data from database.
        Uses stock_data table for price data - FAST query.
        
        Args:
            symbols: List of symbols to fetch. If None, fetches all available.
            
        Returns:
            Dict mapping symbol to DatabaseTick
        """
        conn = self._get_connection()
        if not conn:
            logger.error("Could not connect to database")
            return {}
        
        results = {}
        
        try:
            cursor = conn.cursor()
            
            logger.info("Fetching momentum data from stock_data table (simple approach)")
            
            # Step 1: Get the global max date in the database (fast)
            cursor.execute("SELECT MAX(timestamp::date) FROM stock_data")
            max_date_row = cursor.fetchone()
            if not max_date_row or not max_date_row[0]:
                logger.error("No data in stock_data table")
                return {}
            
            max_date = max_date_row[0]
            logger.info(f"Latest date in database: {max_date}")
            
            # Step 2: Get latest close prices for the most recent 2 trading days
            # Optimized query: use direct timestamp comparison instead of date casting
            # and add LIMIT to prevent full table scans
            cursor.execute("""
                SELECT symbol, timestamp::date as trade_date, close
                FROM stock_data
                WHERE timestamp >= %s::timestamp - interval '5 days'
                ORDER BY symbol, timestamp DESC
                LIMIT 10000
            """, (max_date,))
            
            rows = cursor.fetchall()
            logger.info(f"Query returned {len(rows)} rows (limited to 10000)")
            
            # Process rows to get latest and previous close per symbol
            symbol_data = {}
            for row in rows:
                symbol = row[0]
                trade_date = row[1]
                close = float(row[2])
                
                if symbol not in symbol_data:
                    symbol_data[symbol] = []
                
                # Only keep up to 2 unique dates per symbol
                dates_seen = [d['date'] for d in symbol_data[symbol]]
                if trade_date not in dates_seen and len(symbol_data[symbol]) < 2:
                    symbol_data[symbol].append({'date': trade_date, 'close': close})
            
            logger.info(f"Processed {len(symbol_data)} unique symbols")
            
            # Create DatabaseTick objects
            count = 0
            for symbol, data_list in symbol_data.items():
                if count >= 200:
                    break
                    
                if len(data_list) >= 1:
                    latest_close = data_list[0]['close']
                    data_date = data_list[0]['date']
                    prev_close = data_list[1]['close'] if len(data_list) >= 2 else latest_close
                    
                    # Calculate daily change percentage
                    if prev_close > 0:
                        change_pct = ((latest_close - prev_close) / prev_close) * 100
                    else:
                        change_pct = 0.0
                    
                    bucket, direction = calculate_bucket(change_pct)
                    
                    tick = DatabaseTick(
                        symbol=symbol,
                        ltp=round(latest_close, 2),
                        prev_close=round(prev_close, 2),
                        change_pct=round(change_pct, 2),
                        bucket=bucket,
                        direction=direction,
                        source="DB",
                        confidence="LOW",
                        timestamp=datetime.now().isoformat(),
                        data_date=str(data_date)
                    )
                    
                    results[symbol] = tick
                    self._cache[symbol] = tick
                    count += 1
            
            self._last_fetch = datetime.now()
            logger.info(f"Database fetcher loaded {len(results)} symbols")
            
        except Exception as e:
            logger.error(f"Database fetch error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            conn.close()
        
        return results
    
    def get_cached_data(self) -> List[Dict]:
        """Return all cached data."""
        return [tick.to_dict() for tick in self._cache.values()]
    
    def get_status(self) -> Dict:
        """Get fetcher status."""
        return {
            "source": "DB",
            "is_healthy": len(self._cache) > 0,
            "last_fetch": self._last_fetch.isoformat() if self._last_fetch else None,
            "symbol_count": len(self._cache),
            "poll_interval": 60  # DB data doesn't change frequently
        }


# Singleton instance
_db_data_fetcher = None


def get_db_data_fetcher() -> DatabaseDataFetcher:
    """Get singleton Database data fetcher instance."""
    global _db_data_fetcher
    if _db_data_fetcher is None:
        _db_data_fetcher = DatabaseDataFetcher()
    return _db_data_fetcher
