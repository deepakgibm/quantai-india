import duckdb
import os
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class DuckDBEngine:
    def __init__(self, data_dir: str = "data/parquet"):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        # In-memory database, handles parquet reads blazingly fast
        self.conn = duckdb.connect(database=":memory:")

    def save_to_parquet(self, symbol: str, interval: str, df: pd.DataFrame):
        """
        Saves a DataFrame to Parquet file partitioned by symbol and interval.
        Using Snappy compression for high speed / good ratio.
        """
        if df.empty:
            return
            
        file_name = f"{self.data_dir}/{symbol}_{interval}.parquet"
        
        # We can directly use Pandas to_parquet, or duckdb
        # But pandas to_parquet is straightforward with fastparquet or pyarrow
        try:
            # Assumes pyarrow is installed
            df.to_parquet(file_name, engine="pyarrow", compression="snappy")
            logger.info(f"Saved {symbol} {interval} to Parquet at {file_name}")
        except Exception as e:
            logger.error(f"Error saving Parquet for {symbol}: {e}")

    def query_candles(self, symbol: str, interval: str) -> pd.DataFrame:
        """
        Query candles from Parquet directly via DuckDB.
        """
        file_name = f"{self.data_dir}/{symbol}_{interval}.parquet"
        if not os.path.exists(file_name):
            return pd.DataFrame()
            
        query = f"SELECT * FROM read_parquet('{file_name}') ORDER BY timestamp ASC"
        try:
            return self.conn.execute(query).df()
        except Exception as e:
            logger.error(f"DuckDB query error for {symbol}: {e}")
            return pd.DataFrame()

    def calculate_indicators_in_db(self, symbol: str, interval: str) -> pd.DataFrame:
        """
        Uses DuckDB SQL window functions to rapidly calculate basic indicators 
        (like SMA) directly on the parquet without moving into Python memory.
        """
        file_name = f"{self.data_dir}/{symbol}_{interval}.parquet"
        if not os.path.exists(file_name):
            return pd.DataFrame()
            
        # Example of moving computation to DB (SMA 14 and 50)
        query = f"""
        SELECT 
            *,
            AVG(close) OVER (
                ORDER BY timestamp ASC ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
            ) AS sma_14,
            AVG(close) OVER (
                ORDER BY timestamp ASC ROWS BETWEEN 49 PRECEDING AND CURRENT ROW
            ) AS sma_50
        FROM read_parquet('{file_name}')
        ORDER BY timestamp ASC
        """
        try:
            return self.conn.execute(query).df()
        except Exception as e:
            logger.error(f"DuckDB indicator calc error for {symbol}: {e}")
            return pd.DataFrame()

# Singleton instance
engine = DuckDBEngine()
