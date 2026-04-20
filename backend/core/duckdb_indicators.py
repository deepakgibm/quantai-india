import duckdb
import pandas as pd
from typing import Dict, Any
from core.duckdb_engine import engine
import logging

logger = logging.getLogger(__name__)

class DuckDBIndicatorEngine:
    """
    Computes technical indicators natively inside DuckDB using Parquet files,
    bypassing the need to pull large datasets into Python Pandas memory,
    thus dramatically decreasing CPU and memory footprint for analytical operations.
    """
    def __init__(self, duckdb_engine):
        self.engine = duckdb_engine

    def get_indicators(self, symbol: str, interval: str) -> pd.DataFrame:
        """
        Extremely fast calculation of RSI, ATR, and MACD inside DuckDB.
        """
        file_name = f"{self.engine.data_dir}/{symbol}_{interval}.parquet"
        
        # Test if file exists before running the complex query
        import os
        if not os.path.exists(file_name):
            return pd.DataFrame()
            
        # DuckDB massive window function calculation
        query = f"""
        WITH basic_calc AS (
            SELECT 
                timestamp,
                close,
                high,
                low,
                volume,
                close - LAG(close) OVER (ORDER BY timestamp) as change,
                GREATEST(
                    high - low,
                    ABS(high - LAG(close) OVER (ORDER BY timestamp)),
                    ABS(low - LAG(close) OVER (ORDER BY timestamp))
                ) as tr
            FROM read_parquet('{file_name}')
        ),
        gains_losses AS (
            SELECT 
                *,
                CASE WHEN change > 0 THEN change ELSE 0 END as gain,
                CASE WHEN change < 0 THEN ABS(change) ELSE 0 END as loss
            FROM basic_calc
        ),
        moving_avgs AS (
            SELECT
                timestamp,
                close,
                AVG(gain) OVER w14 AS avg_gain,
                AVG(loss) OVER w14 AS avg_loss,
                AVG(tr) OVER w14 AS atr_14,
                AVG(close) OVER w12 AS ema_12,
                AVG(close) OVER w26 AS ema_26
            FROM gains_losses
            WINDOW 
                w14 AS (ORDER BY timestamp ROWS BETWEEN 13 PRECEDING AND CURRENT ROW),
                w12 AS (ORDER BY timestamp ROWS BETWEEN 11 PRECEDING AND CURRENT ROW),
                w26 AS (ORDER BY timestamp ROWS BETWEEN 25 PRECEDING AND CURRENT ROW)
        )
        SELECT 
            timestamp,
            close,
            atr_14,
            -- Rough approximation of RSI since standard RSI needs recursive EMA
            100.0 - (100.0 / (1.0 + NULLIF(avg_gain / NULLIF(avg_loss, 0), 0))) AS rsi_14,
            (ema_12 - ema_26) AS macd_line
        FROM moving_avgs
        ORDER BY timestamp DESC
        """
        try:
            return self.engine.conn.execute(query).df()
        except Exception as e:
            logger.error(f"DuckDB Indicator Calculation Error: {e}")
            return pd.DataFrame()

indicator_engine = DuckDBIndicatorEngine(engine)
