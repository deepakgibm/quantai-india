"""
Database Data Fetcher Service
Tertiary fallback for when WebSocket and REST API are unavailable.
Uses historical data from the database to provide momentum data during market hours.

Uses NEW SCHEMA:
- stock_candle (instrument_id, timeframe SMALLINT, candle_ts)
- instrument_master (instrument_id, symbol, ...)
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import psycopg2
import pandas as pd
from config import settings
from urllib.parse import urlparse

# Import new schema utilities
from services.instrument_resolver import resolve_instrument_id, get_symbol_for_instrument_id
from services.timeframe_converter import text_to_minutes, minutes_to_text

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
        Fetch latest available data from database using stock_candle + instrument_master.
        
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
            
            logger.info("Fetching momentum data from stock_candle table")
            
            # Get latest date from new schema
            cursor.execute("SELECT MAX(candle_ts::date) FROM stock_candle")
            max_date_row = cursor.fetchone()
            
            if not max_date_row or not max_date_row[0]:
                logger.error("No data in stock_candle table")
                return {}
            
            max_date = max_date_row[0]
            logger.info(f"Latest date in stock_candle: {max_date}")
            
            # Query using new schema with instrument_master join
            cursor.execute("""
                SELECT im.symbol, sc.candle_ts::date as trade_date, sc.close
                FROM stock_candle sc
                JOIN instrument_master im ON sc.instrument_id = im.instrument_id
                WHERE sc.timeframe = 1440  -- Daily candles (1440 minutes)
                AND im.is_active = TRUE
                AND sc.candle_ts >= %s::timestamp - interval '10 days'
                ORDER BY im.symbol, sc.candle_ts DESC
                LIMIT 10000
            """, (max_date,))
            
            rows = cursor.fetchall()
            logger.info(f"stock_candle query returned {len(rows)} rows")
            
            if not rows:
                logger.warning("No daily data found")
                return {}
            
            return self._process_momentum_rows(rows, conn)
            
        except Exception as e:
            logger.error(f"Database fetch error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            conn.close()
        
        return results
    
    def _process_momentum_rows(self, rows: List, conn) -> Dict[str, DatabaseTick]:
        """Process rows from either schema into DatabaseTick objects."""
        results = {}
        
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

    def get_historical_data(
        self,
        symbol: str,
        interval: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical OHLCV data for backtesting.
        Uses stock_candle + instrument_master.
        """
        from models_alpha import TimeframeMapper
        
        tf_minutes = TimeframeMapper.to_minutes(interval)
        conn = self._get_connection()
        if not conn:
            return None
            
        try:
            cursor = conn.cursor()
            
            # Step 1: Resolve instrument_id from instrument_master
            cursor.execute("SELECT instrument_id FROM instrument_master WHERE symbol = %s", (symbol,))
            id_row = cursor.fetchone()
            if not id_row:
                logger.warning(f"Could not resolve instrument_id for {symbol}")
                return None
            
            instrument_id = id_row[0]
            logger.info(f"Fetching historical {interval} data for {symbol} (id={instrument_id}) from stock_candle")
            
            # Step 2: Query stock_candle using instrument_id
            cursor.execute("""
                SELECT candle_ts, open, high, low, close, volume
                FROM stock_candle
                WHERE instrument_id = %s AND timeframe = %s
                AND candle_ts::date >= %s::date
                AND candle_ts::date <= %s::date
                ORDER BY candle_ts ASC
            """, (instrument_id, tf_minutes, start_date, end_date))
            
            rows = cursor.fetchall()
            if not rows:
                logger.warning(f"No historical data for {symbol} in stock_candle")
                return None
                
            df = pd.DataFrame(rows, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize(None)
            df.set_index('timestamp', inplace=True)
            
            # Enforce numeric types
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
            return df
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return None
        finally:
            conn.close()

    def get_stock_data(self, *args, **kwargs):
        """Alias for get_historical_data to satisfy Experiment Lab."""
        return self.get_historical_data(*args, **kwargs)

    def get_available_symbols(self, timeframe: str = "1D") -> List[str]:
        """Get list of symbols available for a given timeframe."""
        from models_alpha import TimeframeMapper
        tf_minutes = TimeframeMapper.to_minutes(timeframe)
        
        conn = self._get_connection()
        if not conn:
            return []
            
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT im.symbol
                FROM stock_candle sc
                JOIN instrument_master im ON sc.instrument_id = im.instrument_id
                WHERE sc.timeframe = %s
                ORDER BY im.symbol
            """, (tf_minutes,))
            
            rows = cursor.fetchall()
            return [row[0] for row in rows]
        except Exception as e:
            logger.error(f"Error fetching symbols from DB: {e}")
            return []
        finally:
            conn.close()


    def fetch_indices_snapshots(self) -> List[Dict]:
        """Fetch latest index snapshots from DB."""
        conn = self._get_connection()
        if not conn:
            return []
            
        try:
            cursor = conn.cursor()
            # Fetch latest daily candle for indices
            # Using window function to get latest per symbol
            cursor.execute("""
                WITH LatestCandles AS (
                    SELECT 
                        im.symbol, 
                        sc.close, 
                        sc.open,
                        sc.candle_ts,
                        ROW_NUMBER() OVER (PARTITION BY im.symbol ORDER BY sc.candle_ts DESC) as rn
                    FROM stock_candle sc
                    JOIN instrument_master im ON sc.instrument_id = im.instrument_id
                    WHERE im.symbol IN ('NIFTY 50', 'BANK NIFTY', 'INDIA VIX')
                    AND sc.timeframe = 1440
                )
                SELECT symbol, close, open, candle_ts 
                FROM LatestCandles 
                WHERE rn = 1
            """)
            
            rows = cursor.fetchall()
            snapshots = []
            for row in rows:
                name = row[0]
                close = float(row[1])
                open_price = float(row[2])
                change = close - open_price
                percent = (change / open_price * 100) if open_price > 0 else 0
                
                snapshots.append({
                    "name": name,
                    "value": round(close, 2),
                    "change": round(change, 2),
                    "percent": round(percent, 2)
                })
            return snapshots
        except Exception as e:
            logger.error(f"Error fetching indices snapshots: {e}")
            return []
        finally:
            conn.close()

# Singleton instance
_db_data_fetcher = None


def get_db_data_fetcher() -> DatabaseDataFetcher:
    """Get singleton Database data fetcher instance."""
    global _db_data_fetcher
    if _db_data_fetcher is None:
        _db_data_fetcher = DatabaseDataFetcher()
    return _db_data_fetcher
