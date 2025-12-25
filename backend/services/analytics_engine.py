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
            return result.df()
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
    
    def get_top_momentum_stocks(self, n: int = 10, 
                                 lookback_days: int = 20) -> pd.DataFrame:
        """
        Get top N stocks by momentum (ROC).
        Uses DuckDB window functions for efficient computation.
        """
        sql = f"""
        WITH latest_prices AS (
            SELECT 
                symbol,
                close,
                LAG(close, {lookback_days}) OVER (PARTITION BY symbol ORDER BY timestamp) as prev_close,
                timestamp,
                ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY timestamp DESC) as rn
            FROM stock_data
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
        sql = f"""
        WITH daily_returns AS (
            SELECT 
                symbol,
                timestamp::date as date,
                close,
                (close - LAG(close) OVER (ORDER BY timestamp)) / LAG(close) OVER (ORDER BY timestamp) as daily_return
            FROM stock_data
            WHERE symbol = '{symbol}'
            ORDER BY timestamp DESC
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
    
    def get_correlation_matrix(self, symbols: List[str], 
                                lookback_days: int = 60) -> pd.DataFrame:
        """
        Calculate correlation matrix between symbols.
        """
        # Get returns for all symbols
        sql = f"""
        WITH returns AS (
            SELECT 
                symbol,
                timestamp::date as date,
                (close - LAG(close) OVER (PARTITION BY symbol ORDER BY timestamp)) / 
                LAG(close) OVER (PARTITION BY symbol ORDER BY timestamp) as ret
            FROM stock_data
            WHERE symbol IN ({','.join([f"'{s}'" for s in symbols])})
            AND timestamp >= CURRENT_DATE - INTERVAL '{lookback_days} days'
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
        # Create temp table with sector mapping
        mapping_df = pd.DataFrame([
            {'symbol': k, 'sector': v} for k, v in sector_mapping.items()
        ])
        self.load_dataframe(mapping_df, 'sector_map')
        
        sql = f"""
        WITH price_changes AS (
            SELECT 
                s.symbol,
                m.sector,
                s.close as current_close,
                FIRST_VALUE(s.close) OVER (
                    PARTITION BY s.symbol 
                    ORDER BY s.timestamp ASC
                ) as start_close
            FROM stock_data s
            JOIN sector_map m ON s.symbol = m.symbol
            WHERE s.timestamp >= CURRENT_DATE - INTERVAL '{lookback_days} days'
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
        GROUP BY sector
        ORDER BY avg_return DESC
        """
        return self.query(sql)
    
    def get_support_resistance_levels(self, symbol: str, 
                                        lookback_days: int = 90) -> pd.DataFrame:
        """
        Calculate support and resistance levels using pivot points.
        """
        sql = f"""
        WITH daily_data AS (
            SELECT 
                timestamp::date as date,
                MAX(high) as high,
                MIN(low) as low,
                (array_agg(close ORDER BY timestamp DESC))[1] as close
            FROM stock_data
            WHERE symbol = '{symbol}'
            AND timestamp >= CURRENT_DATE - INTERVAL '{lookback_days} days'
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
            ROUND(AVG(pivot)::numeric, 2) as pivot_point,
            ROUND((2 * AVG(pivot) - AVG(low))::numeric, 2) as r1,
            ROUND((AVG(pivot) + (AVG(high) - AVG(low)))::numeric, 2) as r2,
            ROUND((2 * AVG(pivot) - AVG(high))::numeric, 2) as s1,
            ROUND((AVG(pivot) - (AVG(high) - AVG(low)))::numeric, 2) as s2,
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
