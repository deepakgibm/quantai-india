"""
Unified Market Data Layer
Centralized historical market data engine using DuckDB, Polars, and SQLite/Postgres fallback.
"""

import os
import logging
import pandas as pd
import duckdb
from typing import Optional, Union
from pathlib import Path
from datetime import datetime, date
from config import settings

logger = logging.getLogger(__name__)

class HistoricalMarketDataEngine:
    """
    Centralized market data engine designed to query the Parquet data lake.
    Falls back to SQL databases when Parquet data is missing.
    """

    def __init__(self, lake_root: Optional[str] = None):
        self.lake_root = Path(lake_root or os.path.join(
            settings.BASE_DIR, 'data', 'parquet'
        ))
        # Map timeframes to standard minute directory strings
        self.tf_map = {
            "1m": "1", "3m": "3", "5m": "5", "15m": "15", 
            "30m": "30", "1h": "60", "1d": "1440", "1w": "10080"
        }
        self.db = duckdb.connect(database=':memory:')
        self._candle_cache = {}
        logger.info(f"HistoricalMarketDataEngine initialized at {self.lake_root}")

    def get_partition_path(self, symbol: str, timeframe: str) -> Path:
        tf_mins = self.tf_map.get(timeframe.lower(), timeframe)
        return self.lake_root / f"symbol={symbol}" / f"timeframe={tf_mins}"

    def load_candles(
        self,
        symbol: str,
        timeframe: str,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Load historical candles as a Pandas DataFrame.
        Resolves schema mismatches and uses local DuckDB execution.
        """
        symbol = symbol.upper().strip()
        timeframe = timeframe.lower()
        
        # 1. Parse dates with defaults
        if not start_date:
            start_date = "2020-01-01"
        if not end_date:
            from datetime import datetime
            end_date = datetime.now().strftime("%Y-%m-%d")

        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)

        cache_key = (symbol, timeframe, str(start_date), str(end_date), limit)
        logger.debug(f"[CANDLE CACHE] Checking key={cache_key} | in_cache={hasattr(self, '_candle_cache') and cache_key in self._candle_cache}")
        if hasattr(self, '_candle_cache') and cache_key in self._candle_cache:
            logger.info(f"[CANDLE CACHE] HIT: returning copy for {symbol} ({timeframe})")
            return self._candle_cache[cache_key].copy()

        partition_dir = self.get_partition_path(symbol, timeframe)
        parquet_glob = str(partition_dir / "**" / "*.parquet").replace("\\", "/")

        df_pd = pd.DataFrame()

        # 2. Try Parquet Lake (DuckDB)
        if partition_dir.exists():
            try:
                sql = f"""
                    SELECT 
                        instrument_id,
                        timeframe,
                        candle_ts as timestamp,
                        CAST(open AS DOUBLE) as open, 
                        CAST(high AS DOUBLE) as high, 
                        CAST(low AS DOUBLE) as low, 
                        CAST(close AS DOUBLE) as close, 
                        volume
                    FROM read_parquet('{parquet_glob}', hive_partitioning=1)
                    WHERE 1=1
                """
                if start_dt:
                    sql += f" AND candle_ts >= '{start_dt.strftime('%Y-%m-%d %H:%M:%S')}'"
                if end_dt:
                    sql += f" AND candle_ts <= '{end_dt.strftime('%Y-%m-%d %H:%M:%S')}'"
                
                sql += " ORDER BY candle_ts ASC"
                
                if limit:
                    sql += f" LIMIT {limit}"

                with duckdb.connect(database=':memory:') as conn:
                    df_pl = conn.execute(sql).pl()
                if not df_pl.is_empty():
                    df_pd = df_pl.to_pandas()
                    logger.info(f"Loaded {len(df_pd)} rows for {symbol} ({timeframe}) from Parquet Lake.")
            except Exception as e:
                logger.warning(f"Failed to query Parquet Lake for {symbol} via DuckDB: {e}")

        # 3. Fallback to SQL database
        if df_pd.empty:
            try:
                from services.db_data_fetcher import get_db_data_fetcher
                fetcher = get_db_data_fetcher()
                start_str = start_dt.strftime("%Y-%m-%d") if start_dt else None
                end_str = end_dt.strftime("%Y-%m-%d") if end_dt else None
                
                df_raw = fetcher.get_stock_data(symbol, timeframe, start_str, end_str)
                if df_raw is not None and not df_raw.empty:
                    df_pd = df_raw.copy()
                    if 'timestamp' not in df_pd.columns and df_pd.index.name == 'timestamp':
                        df_pd = df_pd.reset_index()
                    elif 'timestamp' not in df_pd.columns and isinstance(df_pd.index, pd.DatetimeIndex):
                        df_pd.index.name = 'timestamp'
                        df_pd = df_pd.reset_index()
                    logger.info(f"Loaded {len(df_pd)} rows for {symbol} ({timeframe}) from Database.")
            except Exception as e:
                logger.error(f"Fallback database fetch failed for {symbol}: {e}")

        # 4. Final Fallback: NO mock data allowed in production. Raise error if empty.
        if df_pd.empty:
            logger.error(f"No database or Parquet records found for {symbol} ({timeframe}).")
            from core.exceptions import DataUnavailableError
            raise DataUnavailableError(
                message=f"No historical data available for {symbol} ({timeframe}).",
                symbol=symbol
            )

        # Standardize columns
        if not df_pd.empty:
            df_pd['timestamp'] = pd.to_datetime(df_pd['timestamp']).dt.tz_localize(None)
            df_pd = df_pd.sort_values('timestamp').reset_index(drop=True)
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df_pd[col] = pd.to_numeric(df_pd[col], errors='coerce').fillna(0.0)

        # Cache the result
        if not hasattr(self, '_candle_cache'):
            self._candle_cache = {}
        if not df_pd.empty:
            logger.info(f"[CANDLE CACHE] MISS: loaded {len(df_pd)} candles for {symbol}, saving to cache")
            self._candle_cache[cache_key] = df_pd
        else:
            logger.warning(f"[CANDLE CACHE] loaded empty candles for {symbol}")

        return df_pd


_data_engine = None

def get_market_data_engine() -> HistoricalMarketDataEngine:
    global _data_engine
    if _data_engine is None:
        _data_engine = HistoricalMarketDataEngine()
    return _data_engine
