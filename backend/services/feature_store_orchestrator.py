import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy import text
from database import get_db, engine
from backend.services.feature_store import get_feature_store
from backend.services.feature_pipeline import get_feature_pipeline
from models_alpha import TimeframeMapper, StockCandle, InstrumentMaster
import pandas as pd

logger = logging.getLogger(__name__)

class FeatureStoreOrchestrator:
    """
    Orchestrates the data flow:
    PostgreSQL (Hot) -> Feature Pipeline -> Feature Store (Parquet) -> PostgreSQL Pruning
    """
    
    def __init__(self, feature_version: str = "v1"):
        self.feature_version = feature_version
        self.store = get_feature_store()
        self.pipeline = get_feature_pipeline(feature_version)
        
    async def process_incremental_updates(self, timeframes: List[str] = ["1d", "15m", "5m"]):
        """
        Main entry point for incremental feature generation.
        """
        logger.info(f"Starting incremental feature updates for version {self.feature_version}")
        
        async for db in get_db():
            # 1. Get all active symbols
            res = await db.execute(text("SELECT symbol, instrument_id FROM instrument_master WHERE is_active = TRUE"))
            symbols = res.fetchall()
            
            for symbol, instrument_id in symbols:
                for tf in timeframes:
                    try:
                        await self.process_symbol_timeframe(db, symbol, instrument_id, tf)
                    except Exception as e:
                        logger.error(f"Error processing {symbol} {tf}: {e}")
            
            # 2. Prune PostgreSQL (Keep only recent data)
            await self.prune_hot_layer(db)
            break # Exit after one DB session

    async def process_symbol_timeframe(self, db, symbol: str, instrument_id: int, timeframe: str):
        """
        Processes a single symbol/timeframe pair.
        """
        # 1. Find last timestamp in Feature Store
        last_ts = self.store.get_latest_timestamp(symbol, timeframe, self.feature_version)
        
        # 2. Determine fetch window
        # We need a lookback window for indicator computation (e.g., 50-100 candles)
        lookback_requirement = 100 
        
        if last_ts:
            # Fetch from last_ts - lookback to ensure continuous indicator calculation
            fetch_start = last_ts - timedelta(days=5) # Heuristic for daily, adjust for intraday
            if timeframe != "1d":
                fetch_start = last_ts - timedelta(hours=48)
        else:
            # Initial load - fetch all
            fetch_start = datetime(2020, 1, 1)
            
        # 3. Fetch from PostgreSQL
        tf_minutes = TimeframeMapper.to_minutes(timeframe)
        query = text("""
            SELECT candle_ts as timestamp, open, high, low, close, volume
            FROM stock_candle
            WHERE instrument_id = :inst_id AND timeframe = :tf
            AND candle_ts >= :start
            ORDER BY candle_ts ASC
        """)
        
        res = await db.execute(query, {
            "inst_id": instrument_id,
            "tf": tf_minutes,
            "start": fetch_start
        })
        rows = res.fetchall()
        
        if not rows or len(rows) < 50:
            return
            
        df = pd.DataFrame(rows, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        # Convert numeric columns from Decimal to float
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce').astype(float)
            
        df['symbol'] = symbol
        df['timeframe'] = timeframe
        
        # 4. Run Pipeline
        features_df = self.pipeline.build_features(df)
        
        if features_df.empty:
            return
            
        # 5. Filter for only NEW records to avoid duplication in Parquet
        if last_ts:
            # DuckDB might return datetime with tz, handle it
            last_ts_naive = pd.to_datetime(last_ts).replace(tzinfo=None)
            features_df = features_df[features_df['timestamp'] > last_ts_naive]
            
        if features_df.empty:
            return
            
        # 6. Save to Store
        self.store.save_features(features_df, self.feature_version)
        logger.info(f"Updated {len(features_df)} features for {symbol} {timeframe}")

    async def prune_hot_layer(self, db, retention_days: int = 7):
        """
        Deletes old candles from PostgreSQL after they've been archived to Parquet.
        Keep 7 days for safety/live inference.
        """
        cutoff = datetime.now() - timedelta(days=retention_days)
        
        # IMPORTANT: Only prune if we are sure the data is archived.
        # For now, we use a simple time-based retention as requested.
        
        query = text("DELETE FROM stock_candle WHERE candle_ts < :cutoff")
        res = await db.execute(query, {"cutoff": cutoff})
        await db.commit()
        
        logger.info(f"Pruned {res.rowcount} old candles from PostgreSQL hot layer.")

# Singleton
_orchestrator: Optional[FeatureStoreOrchestrator] = None

def get_feature_orchestrator(version: str = "v1") -> FeatureStoreOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = FeatureStoreOrchestrator(version)
    return _orchestrator
