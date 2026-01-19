"""
DuckDB Analytics Engine
High-performance analytical queries for stock data using DuckDB.
Optimized for complex aggregations, joins, and time-series analysis.
"""

import duckdb
import pandas as pd
import os
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DuckDBAnalyticsEngine:
    """
    Analytics engine using DuckDB for fast OLAP queries.
    
    DuckDB advantages:
    - Columnar storage: 10-100x faster for analytical queries
    - Zero-copy Pandas integration
    - Can query Parquet files directly
    - In-process, no server needed
    """
    
    def __init__(self, db_path: str = ":memory:", parquet_dir: str = None):
        """
        Initialize DuckDB connection.
        
        Args:
            db_path: Path to DuckDB file, or ':memory:' for in-memory
            parquet_dir: Optional directory containing Parquet archive files
        """
        self.db_path = db_path
        self.parquet_dir = parquet_dir or os.path.join(
            os.path.dirname(__file__), '..', 'data', 'parquet'
        )
        self._conn: Optional[duckdb.DuckDBPyConnection] = None
        self._initialize()
    
    def _initialize(self):
        """Initialize DuckDB connection and load extensions."""
        try:
            self._conn = duckdb.connect(self.db_path)
            
            # Install and load useful extensions
            self._conn.execute("INSTALL httpfs")
            self._conn.execute("LOAD httpfs")
            
            logger.info(f"DuckDB initialized: {self.db_path}")
            
            # Create views for Parquet files if directory exists
            if os.path.exists(self.parquet_dir):
                self._register_parquet_views()
                
        except Exception as e:
            logger.error(f"DuckDB initialization failed: {e}")
            raise
    
    def _register_parquet_views(self):
        """Register Parquet files as queryable views."""
        parquet_path = Path(self.parquet_dir)
        
        for pq_file in parquet_path.glob("*.parquet"):
            view_name = pq_file.stem.replace("-", "_").replace(" ", "_")
            try:
                self._conn.execute(f"""
                    CREATE OR REPLACE VIEW {view_name} AS 
                    SELECT * FROM read_parquet('{pq_file.as_posix()}')
                """)
                logger.debug(f"Registered parquet view: {view_name}")
            except Exception as e:
                logger.warning(f"Failed to register {pq_file}: {e}")
    
    def query(self, sql: str, params: Dict = None) -> pd.DataFrame:
        """
        Execute SQL query and return DataFrame.
        
        Args:
            sql: SQL query string
            params: Optional parameters for parameterized queries
        
        Returns:
            pandas DataFrame with results
        """
        try:
            if params:
                result = self._conn.execute(sql, params)
            else:
                result = self._conn.execute(sql)
            df = result.df()
            # Handle NaN/Inf for JSON compatibility
            df = df.fillna(0).replace([float('inf'), float('-inf')], 0)
            return df
        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise
    
    def load_from_postgres(self, pg_connection_string: str, table: str, 
                           where_clause: str = None):
        """
        Load data from PostgreSQL into DuckDB for fast analytics.
        
        Args:
            pg_connection_string: PostgreSQL connection string
            table: Table name to load
            where_clause: Optional WHERE clause to filter data
        """
        try:
            self._conn.execute("INSTALL postgres")
            self._conn.execute("LOAD postgres")
            
            query = f"SELECT * FROM {table}"
            if where_clause:
                query += f" WHERE {where_clause}"
            
            self._conn.execute(f"""
                CREATE OR REPLACE TABLE {table} AS 
                SELECT * FROM postgres_scan('{pg_connection_string}', '{table}')
                {f'WHERE {where_clause}' if where_clause else ''}
            """)
            
            logger.info(f"Loaded {table} from PostgreSQL")
        except Exception as e:
            logger.error(f"Failed to load from PostgreSQL: {e}")
            raise
    
    def load_dataframe(self, df: pd.DataFrame, table_name: str):
        """
        Load pandas DataFrame into DuckDB table.
        
        Args:
            df: pandas DataFrame
            table_name: Name for the DuckDB table
        """
        self._conn.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM df")
        logger.info(f"Loaded DataFrame into table '{table_name}': {len(df)} rows")
    
    # ========== Analytics Functions ==========
    
    def _ensure_table_exists(self, table_name: str):
        """Ensure a table exists in DuckDB, trying to load it from Postgres if missing."""
        try:
            # Check if table exists in DuckDB catalog
            tables = self._conn.execute("SHOW TABLES").fetchall()
            table_list = [t[0] for t in tables]
            
            if table_name in table_list:
                return

            logger.info(f"Table {table_name} not found in DuckDB. Attempting to load from Postgres...")
            print(f"DEBUG: Table {table_name} not found. Catalog: {table_list}")
            
            try:
                from config import settings
                pg_conn = settings.SYNC_DATABASE_URL
                # Handle host.docker.internal for local dev
                if "localhost" in pg_conn and os.path.exists('/.dockerenv'):
                    pg_conn = pg_conn.replace("localhost", "host.docker.internal")
                
                logger.info(f"Using PG Connection for DuckDB: {pg_conn}")
                self.load_from_postgres(pg_conn, table_name)
                
                # Verify again
                tables = self._conn.execute("SHOW TABLES").fetchall()
                if table_name in [t[0] for t in tables]:
                    logger.info(f"Successfully loaded {table_name} into DuckDB")
                    return
            except Exception as e:
                logger.error(f"Failed to auto-load {table_name} from Postgres: {e}")
                print(f"DEBUG: PG Load failed: {e}")
                
            # Final Fallback: Create empty table
            logger.warning(f"Creating empty fallback table for {table_name}")
            if table_name == 'stock_candle':
                self._conn.execute("""
                    CREATE TABLE IF NOT EXISTS stock_candle (
                        instrument_id BIGINT,
                        timeframe SMALLINT,
                        candle_ts TIMESTAMP,
                        open DOUBLE,
                        high DOUBLE,
                        low DOUBLE,
                        close DOUBLE,
                        volume BIGINT
                    )
                """)
            elif table_name == 'instrument_master':
                self._conn.execute("""
                    CREATE TABLE IF NOT EXISTS instrument_master (
                        instrument_id BIGINT,
                        symbol VARCHAR,
                        company_name VARCHAR,
                        sector VARCHAR,
                        is_active BOOLEAN
                    )
                """)
        except Exception as e:
            logger.error(f"Critical error in _ensure_table_exists: {e}")
            print(f"DEBUG: Critical error in _ensure_table_exists: {e}")

    def get_top_momentum_stocks(self, n: int = 10, 
                                 lookback_days: int = 20) -> pd.DataFrame:
        """
        Get top N stocks by momentum (ROC).
        Uses DuckDB window functions for efficient computation.
        """
        self._ensure_table_exists('stock_candle')
        self._ensure_table_exists('instrument_master')
        sql = f"""
        WITH latest_prices AS (
            SELECT 
                im.symbol,
                sc.close,
                LAG(sc.close, {lookback_days}) OVER (PARTITION BY im.symbol ORDER BY sc.candle_ts) as prev_close,
                sc.candle_ts as timestamp,
                ROW_NUMBER() OVER (PARTITION BY im.symbol ORDER BY sc.candle_ts DESC) as rn
            FROM stock_candle sc
            JOIN instrument_master im ON sc.instrument_id = im.instrument_id
            WHERE sc.timeframe = 1440
        ),
        momentum AS (
            SELECT 
                symbol,
                close as current_price,
                prev_close,
                ((close - prev_close) / prev_close * 100) as roc,
                timestamp
            FROM latest_prices
            WHERE rn = 1 AND prev_close IS NOT NULL
        )
        SELECT 
            symbol,
            current_price,
            roc,
            timestamp
        FROM momentum
        WHERE roc IS NOT NULL
        ORDER BY roc DESC
        LIMIT {n}
        """
        return self.query(sql)
    
    def get_volatility_analysis(self, symbol: str, 
                                 lookback_days: int = 30) -> pd.DataFrame:
        """
        Analyze volatility metrics for a symbol.
        """
        self._ensure_table_exists('stock_candle')
        self._ensure_table_exists('instrument_master')
        sql = f"""
        WITH daily_returns AS (
            SELECT 
                im.symbol,
                sc.candle_ts::date as date,
                sc.close,
                (sc.close - LAG(sc.close) OVER (ORDER BY sc.candle_ts)) / LAG(sc.close) OVER (ORDER BY sc.candle_ts) as daily_return
            FROM stock_candle sc
            JOIN instrument_master im ON sc.instrument_id = im.instrument_id
            WHERE im.symbol = '{symbol}' AND sc.timeframe = 1440
            ORDER BY sc.candle_ts DESC
            LIMIT {lookback_days}
        )
        SELECT 
            symbol,
            COUNT(*) as trading_days,
            AVG(daily_return) * 100 as avg_daily_return,
            STDDEV(daily_return) * 100 as daily_volatility,
            STDDEV(daily_return) * SQRT(252) * 100 as annualized_volatility,
            MAX(daily_return) * 100 as max_daily_gain,
            MIN(daily_return) * 100 as max_daily_loss
        FROM daily_returns
        WHERE daily_return IS NOT NULL
        GROUP BY symbol
        """
        return self.query(sql)
        return self.query(sql)
    
    def get_correlation_matrix(self, symbols: List[str], 
                                lookback_days: int = 60) -> pd.DataFrame:
        """
        Calculate correlation matrix between symbols.
        """
        self._ensure_table_exists('stock_candle')
        self._ensure_table_exists('instrument_master')
        # Get returns for all symbols
        sql = f"""
        WITH returns AS (
            SELECT 
                im.symbol,
                sc.candle_ts::date as date,
                (sc.close - LAG(sc.close) OVER (PARTITION BY im.symbol ORDER BY sc.candle_ts)) / 
                LAG(sc.close) OVER (PARTITION BY im.symbol ORDER BY sc.candle_ts) as ret
            FROM stock_candle sc
            JOIN instrument_master im ON sc.instrument_id = im.instrument_id
            WHERE im.symbol IN ({','.join([f"'{s}'" for s in symbols])})
            AND sc.timeframe = 1440
            AND sc.candle_ts >= CURRENT_DATE - INTERVAL '{lookback_days} days'
        )
        SELECT symbol, date, ret
        FROM returns
        WHERE ret IS NOT NULL
        ORDER BY date, symbol
        """
        df = self.query(sql)
        
        if df.empty:
            return pd.DataFrame()
        
        # Pivot and calculate correlation
        pivot = df.pivot(index='date', columns='symbol', values='ret')
        return pivot.corr()
    
    def get_sector_performance(self, sector_mapping: Dict[str, str],
                                 lookback_days: int = 30) -> pd.DataFrame:
        """
        Calculate sector-wise performance.
        
        Args:
            sector_mapping: Dict mapping symbol -> sector
        """
        self._ensure_table_exists('stock_candle')
        self._ensure_table_exists('instrument_master')
        
        sql = f"""
        WITH latest_candles AS (
            SELECT 
                sc.instrument_id,
                sc.close,
                sc.candle_ts,
                FIRST_VALUE(sc.close) OVER (PARTITION BY sc.instrument_id ORDER BY sc.candle_ts ASC) as start_close,
                ROW_NUMBER() OVER (PARTITION BY sc.instrument_id ORDER BY sc.candle_ts DESC) as rn
            FROM stock_candle sc
            WHERE sc.timeframe = 1440
              AND sc.candle_ts >= CURRENT_DATE - INTERVAL '{lookback_days} days'
        ),
        price_changes AS (
            SELECT 
                im.symbol,
                im.sector,
                lc.close as current_close,
                lc.start_close
            FROM latest_candles lc
            JOIN instrument_master im ON lc.instrument_id = im.instrument_id
            WHERE lc.rn = 1
        ),
        latest AS (
            SELECT DISTINCT ON (symbol)
                symbol, sector, current_close, start_close,
                ((current_close - start_close) / start_close * 100) as pct_change
            FROM price_changes
        )
        SELECT 
            sector,
            COUNT(*) as stock_count,
            AVG(pct_change) as avg_return,
            MIN(pct_change) as worst_return,
            MAX(pct_change) as best_return
        FROM latest
        WHERE sector IS NOT NULL
        GROUP BY sector
        ORDER BY avg_return DESC
        """
        return self.query(sql)
    
    def get_support_resistance_levels(self, symbol: str, 
                                        lookback_days: int = 90) -> pd.DataFrame:
        """
        Calculate support and resistance levels using pivot points.
        """
        self._ensure_table_exists('stock_candle')
        self._ensure_table_exists('instrument_master')
        sql = f"""
        WITH daily_data AS (
            SELECT 
                sc.candle_ts::date as date,
                MAX(sc.high) as high,
                MIN(sc.low) as low,
                (array_agg(sc.close ORDER BY sc.candle_ts DESC))[1] as close
            FROM stock_candle sc
            JOIN instrument_master im ON sc.instrument_id = im.instrument_id
            WHERE im.symbol = '{symbol}' AND sc.timeframe = 1440
            AND sc.candle_ts >= CURRENT_DATE - INTERVAL '{lookback_days} days'
            GROUP BY date
        ),
        pivot_calc AS (
            SELECT 
                date,
                (high + low + close) / 3 as pivot,
                high,
                low,
                close
            FROM daily_data
        )
        SELECT 
            MAX(date) as as_of_date,
            ROUND(AVG("pivot")::numeric, 2) as pivot_point,
            ROUND((2 * AVG("pivot") - AVG(low))::numeric, 2) as r1,
            ROUND((AVG("pivot") + (AVG(high) - AVG(low)))::numeric, 2) as r2,
            ROUND((2 * AVG("pivot") - AVG(high))::numeric, 2) as s1,
            ROUND((AVG("pivot") - (AVG(high) - AVG(low)))::numeric, 2) as s2,
            ROUND(MAX(high)::numeric, 2) as resistance_max,
            ROUND(MIN(low)::numeric, 2) as support_min
        FROM pivot_calc
        """
        return self.query(sql)
    
    def export_to_parquet(self, query: str, output_path: str):
        """
        Export query results to Parquet file.
        """
        self._conn.execute(f"""
            COPY ({query}) TO '{output_path}' (FORMAT PARQUET, COMPRESSION ZSTD)
        """)
        logger.info(f"Exported to {output_path}")
    
    def close(self):
        """Close DuckDB connection."""
        if self._conn:
            self._conn.close()
            self._conn = None


# Singleton instance
_analytics_engine: Optional[DuckDBAnalyticsEngine] = None


def get_analytics_engine() -> DuckDBAnalyticsEngine:
    """Get singleton analytics engine instance."""
    global _analytics_engine
    if _analytics_engine is None:
        _analytics_engine = DuckDBAnalyticsEngine()
    return _analytics_engine


# CLI interface
if __name__ == "__main__":
    import sys
    
    engine = get_analytics_engine()
    
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        print(f"Executing: {query}")
        result = engine.query(query)
        print(result)
    else:
        print("DuckDB Analytics Engine ready")
        print("Usage: python analytics_engine.py '<SQL query>'")
