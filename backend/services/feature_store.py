import os
import pandas as pd
import numpy as np
import logging
import duckdb
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
from config import settings

logger = logging.getLogger(__name__)

class FeatureStoreService:
    """
    Manages the persistent Feature Store using Parquet files.
    
    Partitioning: data/feature_store/feature_version={v}/timeframe={tf}/symbol={sym}/year={y}/month={m}.parquet
    
    Uses DuckDB for high-performance analytical queries.
    """
    
    def __init__(self, base_path: str = None):
        self.base_path = base_path or os.path.join(settings.BASE_DIR, "data", "feature_store")
        Path(self.base_path).mkdir(parents=True, exist_ok=True)
        self.db = duckdb.connect(database=':memory:') # Use DuckDB for querying Parquet files
        self._warm_cache()
        
    def _warm_cache(self):
        """Creates a view for faster access across partitions."""
        parquet_path = os.path.join(self.base_path, "**", "*.parquet")
        try:
            # Check if any parquet files exist before creating view
            if any(Path(self.base_path).rglob("*.parquet")):
                self.db.execute(f"CREATE OR REPLACE VIEW features AS SELECT * FROM read_parquet('{parquet_path}', hive_partitioning=1)")
                logger.info("🔥 Feature Store Cache Warmed.")
        except Exception as e:
            logger.warning(f"Could not warm feature cache: {e}")

    def save_features(self, df: pd.DataFrame, feature_version: str = "v1"):
        """
        Saves features to partitioned Parquet files.
        df must contain: symbol, timeframe, timestamp (datetime)
        """
        if df.empty:
            return
            
        # Ensure timestamp is datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['year'] = df['timestamp'].dt.year
        df['month'] = df['timestamp'].dt.month
        
        # We partition by version, timeframe, symbol, year, month
        # Path: base/version=v1/timeframe=1d/symbol=RELIANCE/year=2024/month=10.parquet
        
        # Iterate through partitions to save
        for (timeframe, symbol, year, month), group in df.groupby(['timeframe', 'symbol', 'year', 'month']):
            partition_dir = os.path.join(
                self.base_path, 
                f"feature_version={feature_version}",
                f"timeframe={timeframe}",
                f"symbol={symbol}",
                f"year={year}"
            )
            Path(partition_dir).mkdir(parents=True, exist_ok=True)
            
            file_path = os.path.join(partition_dir, f"month={month}.parquet")
            
            # Write to Parquet (append if exists or overwrite for current month)
            # For simplicity in this first version, we overwrite the specific month partition
            # Incremental updates will handle partial month logic
            group.to_parquet(file_path, index=False, compression='zstd')
            
        logger.info(f"Saved {len(df)} feature rows to {self.base_path}")

    def query_features(self, 
                       symbols: List[str] = None, 
                       timeframes: List[str] = None, 
                       feature_version: str = "v1",
                       start_date: str = None,
                       end_date: str = None) -> pd.DataFrame:
        """
        Queries features across Parquet files using DuckDB.
        """
        # Try to use the view first
        try:
            self.db.execute("SELECT 1 FROM features LIMIT 1")
            query = "SELECT * FROM features"
        except:
            parquet_path = os.path.join(self.base_path, f"feature_version={feature_version}", "**", "*.parquet")
            query = f"SELECT * FROM read_parquet('{parquet_path}', hive_partitioning=1)"
        
        conditions = [f"feature_version = '{feature_version}'"]
        if symbols:
            sym_list = "', '".join(symbols)
            conditions.append(f"symbol IN ('{sym_list}')")
        if timeframes:
            tf_list = "', '".join(timeframes)
            conditions.append(f"timeframe IN ('{tf_list}')")
        if start_date:
            conditions.append(f"timestamp >= '{start_date}'")
        if end_date:
            conditions.append(f"timestamp <= '{end_date}'")
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        query += " ORDER BY timestamp ASC"
        
        try:
            return self.db.execute(query).df()
        except Exception as e:
            logger.error(f"Feature Store query failed: {e}")
            return pd.DataFrame()

    def get_latest_timestamp(self, symbol: str, timeframe: str, feature_version: str = "v1") -> Optional[datetime]:
        """
        Utility to find the last updated timestamp for a symbol to facilitate incremental updates.
        """
        parquet_path = os.path.join(self.base_path, f"feature_version={feature_version}", f"timeframe={timeframe}", f"symbol={symbol}", "**", "*.parquet")
        
        if not any(Path(self.base_path).rglob("*.parquet")): # Check if any files exist
            return None
            
        query = f"SELECT MAX(timestamp) as last_ts FROM read_parquet('{parquet_path}', hive_partitioning=1)"
        try:
            res = self.db.execute(query).fetchone()
            return res[0] if res and res[0] else None
        except Exception:
            return None

# Singleton
_feature_store: Optional[FeatureStoreService] = None

def get_feature_store() -> FeatureStoreService:
    global _feature_store
    if _feature_store is None:
        _feature_store = FeatureStoreService()
    return _feature_store
