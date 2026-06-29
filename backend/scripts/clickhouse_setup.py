import logging
import os
import sys
from datetime import datetime, timedelta

# Adjust python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.clickhouse_client import ClickHouseClient
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ClickHouseSetup")

def setup_clickhouse():
    logger.info("Initializing ClickHouse Database and Table Setup...")
    
    # Instantiate client
    ch_client = ClickHouseClient()
    
    try:
        # Check connection
        logger.info(f"Connecting to ClickHouse at {settings.CLICKHOUSE_HOST}:{settings.CLICKHOUSE_PORT}...")
        client = ch_client.connect()
        logger.info("Successfully connected to ClickHouse server.")
    except Exception as e:
        logger.error(f"❌ Could not connect to ClickHouse: {e}")
        logger.warning("ClickHouse setup aborted. Ensure ClickHouse server is running locally or in Docker.")
        return False
        
    try:
        # 1. Create database
        logger.info("Creating database 'quantai' if not exists...")
        ch_client.execute("CREATE DATABASE IF NOT EXISTS quantai")
        
        # 2. Create raw ticks table
        logger.info("Creating table 'quantai.market_ticks' if not exists...")
        ticks_ddl = """
        CREATE TABLE IF NOT EXISTS quantai.market_ticks (
            instrument_id UInt64,
            tick_ts DateTime64(6, 'Asia/Kolkata') CODEC(DoubleDelta, LZ4),
            last_price Decimal(12, 4) CODEC(T64, ZSTD),
            volume UInt64 CODEC(T64, LZ4),
            bid_price Decimal(12, 4) CODEC(T64, ZSTD),
            ask_price Decimal(12, 4) CODEC(T64, ZSTD),
            buy_sell_flag Enum8('NEUTRAL' = 0, 'BUY' = 1, 'SELL' = 2) CODEC(LZ4)
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(tick_ts)
        ORDER BY (instrument_id, tick_ts)
        SETTINGS index_granularity = 8192;
        """
        ch_client.execute(ticks_ddl)
        
        # 3. Create stock candles table
        logger.info("Creating table 'quantai.stock_candles' if not exists...")
        candles_ddl = """
        CREATE TABLE IF NOT EXISTS quantai.stock_candles (
            instrument_id UInt64,
            timeframe UInt16 CODEC(LZ4),
            candle_ts DateTime64(0, 'Asia/Kolkata') CODEC(DoubleDelta, LZ4),
            open Decimal(12, 4) CODEC(T64, ZSTD),
            high Decimal(12, 4) CODEC(T64, ZSTD),
            low Decimal(12, 4) CODEC(T64, ZSTD),
            close Decimal(12, 4) CODEC(T64, ZSTD),
            volume UInt64 CODEC(T64, LZ4),
            version DateTime CODEC(LZ4)
        ) ENGINE = ReplacingMergeTree(version)
        PARTITION BY toYYYYMM(candle_ts)
        ORDER BY (instrument_id, timeframe, candle_ts)
        SETTINGS index_granularity = 8192;
        """
        ch_client.execute(candles_ddl)
        logger.info("✅ ClickHouse DDL schema created successfully.")
        
        # 4. Insert mock seeding to verify ingestion
        logger.info("Seeding mock verification data to ClickHouse...")
        now = datetime.now()
        
        # Seed 100 mock ticks
        mock_ticks = []
        for i in range(100):
            mock_ticks.append((
                10001, # Instrument ID
                now - timedelta(seconds=(100 - i)), # Timestamp
                1850.50 + i * 0.15, # Last Price
                100 + i * 10, # Volume
                1850.00 + i * 0.15, # Bid Price
                1851.00 + i * 0.15, # Ask Price
                1 if i % 3 == 0 else 2 if i % 3 == 1 else 0 # Buy/Sell flag
            ))
            
        ch_client.insert(
            "quantai.market_ticks",
            mock_ticks,
            column_names=["instrument_id", "tick_ts", "last_price", "volume", "bid_price", "ask_price", "buy_sell_flag"]
        )
        logger.info(f"✅ Seeding complete. Inserted {len(mock_ticks)} ticks.")
        
        # 5. Verify read query
        df = ch_client.query_as_dataframe(
            "SELECT count() as total_rows, avg(last_price) as avg_price FROM quantai.market_ticks WHERE instrument_id = 10001"
        )
        logger.info(f"Read Verification Result:\n{df.to_string()}")
        return True
        
    except Exception as e:
        logger.error(f"❌ ClickHouse setup failure: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    setup_clickhouse()
