import asyncio
import logging
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

INDEXES_TO_CREATE = [
    # Stock Candle Performance
    {
        "name": "idx_candle_ts_brin",
        "table": "stock_candle",
        "sql": "CREATE INDEX IF NOT EXISTS idx_candle_ts_brin ON stock_candle USING BRIN (candle_ts);"
    },
    # Instrument Master composite lookup
    {
        "name": "idx_instrument_exchange_symbol",
        "table": "instrument_master",
        "sql": "CREATE INDEX IF NOT EXISTS idx_instrument_exchange_symbol ON instrument_master (exchange, symbol);"
    },
    # Alpha Signals - temporal queries and leaderboard
    {
        "name": "idx_alpha_score_ts",
        "table": "alpha_signals",
        "sql": "CREATE INDEX IF NOT EXISTS idx_alpha_score_ts ON alpha_signals (alpha_score DESC, timestamp DESC);"
    },
    # Trade Decisions - user history
    {
        "name": "idx_trade_user_ts",
        "table": "trade_decisions",
        "sql": "CREATE INDEX IF NOT EXISTS idx_trade_user_ts ON trade_decisions (user_id, timestamp DESC);"
    },
    # Daily Top Gainers Snapshot - lookup
    {
        "name": "idx_top_gainers_date_cat",
        "table": "daily_top_gainers_snapshot",
        "sql": "CREATE INDEX IF NOT EXISTS idx_top_gainers_date_cat ON daily_top_gainers_snapshot (trade_date DESC, category);"
    }
]

async def apply_indexes():
    from database import engine
    
    logger.info("Starting performance index migration...")
    
    async with engine.connect() as conn:
        # Set isolation level to AUTOCOMMIT for index creation
        await conn.execution_options(isolation_level="AUTOCOMMIT")
        
        for idx in INDEXES_TO_CREATE:
            logger.info(f"Applying: {idx['name']} on {idx['table']}...")
            try:
                await conn.execute(text(idx['sql']))
                logger.info(f"Successfully applied {idx['name']}")
            except Exception as e:
                logger.warning(f"Failed to apply {idx['name']} (might already exist): {str(e)[:100]}")

if __name__ == "__main__":
    asyncio.run(apply_indexes())
