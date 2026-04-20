import os
import polars as pl
import duckdb
import logging
from typing import List, Optional, Union
from pathlib import Path
from datetime import datetime
from config import settings

logger = logging.getLogger(__name__)

class LakeDAL:
    """
    Unified Data Access Layer for the Parquet-based Data Lake.
    Optimized for vectorized processing using Polars and DuckDB.
    """
    
    def __init__(self, lake_root: str = None):
        """
        Initialize LakeDAL.
        
        Args:
            lake_root: Root directory of the Data Lake.
        """
        self.lake_root = Path(lake_root or os.path.join(
            os.path.dirname(__file__), '..', '..', 'data', 'parquet'
        ))
        
        # Mapping UI timeframe names to minutes (as used in folder names)
        self.tf_map = {
            "1m": "1", "3m": "3", "5m": "5", "15m": "15", 
            "30m": "30", "1h": "60", "1d": "1440", "1w": "10080"
        }
        
        self.db = duckdb.connect(database=':memory:')
        logger.info(f"LakeDAL initialized at {self.lake_root}")

    def get_candle_path(self, symbol: str, timeframe: str) -> Path:
        """Get the base path for a specific symbol/timeframe in Hive structure."""
        tf_mins = self.tf_map.get(timeframe.lower(), timeframe)
        return self.lake_root / f"symbol={symbol}" / f"timeframe={tf_mins}"

    def write_candles(self, symbol: str, timeframe: str, df: Union[pl.DataFrame, pl.LazyFrame]):
        """
        Write candles to the Data Lake (Hive Partitioned).
        """
        tf_mins = self.tf_map.get(timeframe.lower(), timeframe)
        output_dir = self.get_candle_path(symbol, timeframe)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if isinstance(df, pl.LazyFrame):
            df = df.collect()
            
        # Add year/month if not present for partitioning
        if "timestamp" in df.columns:
            df = df.with_columns([
                pl.col("timestamp").dt.year().alias("year"),
                pl.col("timestamp").dt.month().alias("month")
            ])
            
        # Write using Polars' delta/parquet partitioning (simplified for this context)
        # In this specific case, we'll write one file per month or similar
        # For now, we'll just use a generic filename within the bucket
        output_path = output_dir / "data.parquet"
        df.write_parquet(output_path, compression="zstd")
        logger.debug(f"Wrote {len(df)} candles for {symbol} ({timeframe}) to {output_path}")

    def load_candles(self, symbol: str, timeframe: str, 
                     start_date: Optional[datetime] = None, 
                     end_date: Optional[datetime] = None,
                     lazy: bool = True) -> Union[pl.DataFrame, pl.LazyFrame]:
        """
        Load candles for a symbol and timeframe from Hive partitions.
        Standardizes 'candle_ts' to 'timestamp' and casts decimals to floats.
        """
        input_dir = self.get_candle_path(symbol, timeframe)
        if not input_dir.exists():
            logger.warning(f"Candle directory not found: {input_dir}")
            return pl.DataFrame() if not lazy else pl.LazyFrame()

        # Using recursive search to capture all nested parquet files (year/month)
        # We use DuckDB as the engine for loading because it handles Decimal-to-Double 
        # unification much better than Polars native scanner when partitions mismatch.
        parquet_glob = str(input_dir / "**" / "*.parquet").replace("\\", "/")
        logger.info(f"🔍 Attempting to load {symbol} ({timeframe}) from {parquet_glob}")
        
        try:
            # 1. Attempt DuckDB (Robust)
            logger.debug("Trying DuckDB read_parquet...")
            sql = f"SELECT * FROM read_parquet('{parquet_glob}', hive_partitioning=1) LIMIT 0"
            self.db.execute(sql) # Check schema
            
            sql_full = f"""
                SELECT 
                    instrument_id, 
                    timeframe, 
                    candle_ts, 
                    CAST(open AS DOUBLE) as open, 
                    CAST(high AS DOUBLE) as high, 
                    CAST(low AS DOUBLE) as low, 
                    CAST(close AS DOUBLE) as close, 
                    volume
                FROM read_parquet('{parquet_glob}', hive_partitioning=1)
            """
            df = self.db.execute(sql_full).pl()
            lf = df.lazy()
            logger.info(f"✅ Success: Loaded {len(df)} rows via DuckDB engine")
            
        except Exception as e:
            logger.warning(f"⚠️ DuckDB scan failed: {e}")
            try:
                # 2. Attempt Polars (Native)
                logger.debug("Trying Polars scan_parquet...")
                lf = pl.scan_parquet(str(input_dir / "**" / "*.parquet"), hive_partitioning=True)
                # Test schema access which triggers partition unification
                schema = lf.collect_schema()
                logger.info(f"✅ Success: Loaded schema via Polars native: {schema}")
            except Exception as e2:
                logger.error(f"❌ Critical: Polars scan also failed: {e2}")
                return pl.DataFrame() if not lazy else pl.LazyFrame()
        
        # Standardize column naming if necessary
        schema = lf.collect_schema()
        if 'candle_ts' in schema and 'timestamp' not in schema:
            lf = lf.with_columns(pl.col('candle_ts').alias('timestamp'))
        elif 'timestamp' in schema and 'candle_ts' not in schema:
            lf = lf.with_columns(pl.col('timestamp').alias('candle_ts'))
            
        if start_date:
            lf = lf.filter(pl.col("timestamp") >= start_date)
        if end_date:
            lf = lf.filter(pl.col("timestamp") <= end_date)
            
        return lf if lazy else lf.collect()

    def query_lake(self, sql_query: str) -> pl.DataFrame:
        """
        Execute a DuckDB SQL query against the Parquet files in the lake.
        
        Example:
            dal.query_lake("SELECT * FROM read_parquet('data/lake/raw/1d/*.parquet') WHERE close > 2000")
        """
        return self.db.execute(sql_query).pl()

    def list_symbols(self, timeframe: str) -> List[str]:
        """List all symbols available for a given timeframe."""
        tf_path = self.raw_path / timeframe
        if not tf_path.exists():
            return []
        return [f.stem for f in tf_path.glob("*.parquet")]

# Singleton instance
_lake_dal = None

def get_lake_dal() -> LakeDAL:
    global _lake_dal
    if _lake_dal is None:
        _lake_dal = LakeDAL()
    return _lake_dal
