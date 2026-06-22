import os
import sys
import logging
import asyncio
import polars as pl
from sqlalchemy import create_engine, text

# Add backend to path to import core/services
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.lake_dal import get_lake_dal
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_candles():
    """Migrate stock_candle data from PG to Parquet Lake."""
    dal = get_lake_dal()
    engine = create_engine(settings.SYNC_DATABASE_URL)
    
    logger.info("Starting migration of stock_candle table...")
    
    with engine.connect() as conn:
        # Get active instruments and their symbols
        instr_query = text("SELECT instrument_id, symbol FROM instrument_master WHERE is_active = TRUE")
        instruments = conn.execute(instr_query).fetchall()
        
        # Get unique timeframes
        tf_query = text("SELECT DISTINCT timeframe FROM stock_candle")
        timeframes = [r[0] for r in conn.execute(tf_query).fetchall()]
        
        total_symbols = len(instruments)
        for i, (instr_id, symbol) in enumerate(instruments):
            logger.info(f"[{i+1}/{total_symbols}] Processing {symbol} (ID: {instr_id})")
            
            for tf_mins in timeframes:
                # Map minutes back to UI timeframe strings for directory structure
                # This is a simplified mapping, we can refine it
                tf_str = f"{tf_mins}m" if tf_mins < 1440 else "1d"
                
                query = text("""
                    SELECT candle_ts as timestamp, open, high, low, close, volume
                    FROM stock_candle
                    WHERE instrument_id = :instr_id AND timeframe = :tf
                    ORDER BY candle_ts ASC
                """)
                
                # Fetch as Pandas then convert to Polars for ease with SQLAlchemy results
                result = conn.execute(query, {"instr_id": instr_id, "tf": tf_mins})
                rows = result.fetchall()
                
                if not rows:
                    continue
                
                df = pl.from_dicts([
                    {
                        "timestamp": r[0],
                        "open": float(r[1]),
                        "high": float(r[2]),
                        "low": float(r[3]),
                        "close": float(r[4]),
                        "volume": int(r[5])
                    } for r in rows
                ])
                
                dal.write_candles(symbol, tf_str, df)
                logger.info(f"  Exported {len(df)} candles for {symbol} ({tf_str})")

    logger.info("Migration of stock_candle completed.")

async def migrate_alpha_signals():
    """Migrate alpha_signals data from PG to Parquet Lake."""
    dal = get_lake_dal()
    engine = create_engine(settings.SYNC_DATABASE_URL)
    
    logger.info("Starting migration of alpha_signals table...")
    
    with engine.connect() as conn:
        symbols_query = text("SELECT DISTINCT symbol FROM alpha_signals")
        symbols = [r[0] for r in conn.execute(symbols_query).fetchall()]
        
        for symbol in symbols:
            logger.info(f"Processing signals for {symbol}")
            
            query = text("""
                SELECT timestamp, rsi, macd, macd_signal, macd_divergence, 
                       atr, bollinger_upper, bollinger_lower, bollinger_position,
                       vwap, volume_sma, vwap_ratio, volume_ratio, 
                       alpha_score, alpha_rank
                FROM alpha_signals
                WHERE symbol = :symbol
                ORDER BY timestamp ASC
            """)
            
            result = conn.execute(query, {"symbol": symbol})
            rows = result.fetchall()
            
            if not rows:
                continue
                
            df = pl.DataFrame([dict(zip(result.keys(), r)) for r in rows])
            
            # Save to processed/indicators
            output_path = dal.processed_path / "indicators" / "daily" / f"{symbol}.parquet"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            df.write_parquet(output_path, compression="zstd")
            logger.info(f"  Exported {len(df)} signals for {symbol}")

    logger.info("Migration of alpha_signals completed.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(migrate_candles())
    asyncio.run(migrate_alpha_signals())
