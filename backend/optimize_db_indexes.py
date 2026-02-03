import asyncio
from database import engine
from sqlalchemy import text

async def ensure_indexes():
    indexes = [
        ("idx_indicators_lookup", "CREATE INDEX IF NOT EXISTS idx_indicators_lookup ON precomputed_indicators (symbol, interval, timestamp DESC)"),
        ("idx_indicators_momentum", "CREATE INDEX IF NOT EXISTS idx_indicators_momentum ON precomputed_indicators (momentum_score)"),
        ("idx_indicators_volatility", "CREATE INDEX IF NOT EXISTS idx_indicators_volatility ON precomputed_indicators (volatility_score)"),
        ("idx_candles_lookup", "CREATE INDEX IF NOT EXISTS idx_candles_lookup_fast ON stock_candle (instrument_id, timeframe, candle_ts DESC)")
    ]
    
    async with engine.connect() as conn:
        for name, sql in indexes:
            print(f"Ensuring index: {name}")
            try:
                await conn.execute(text(sql))
                await conn.commit()
                print(f"Success: {name}")
            except Exception as e:
                print(f"Error creating {name}: {e}")

if __name__ == "__main__":
    asyncio.run(ensure_indexes())
