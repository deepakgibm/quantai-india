import asyncio
import time
from datetime import timedelta
from sqlalchemy import text
from database import AsyncSessionLocal

async def test_heatmap_query():
    target_rn = 2  # 1D timeframe
    calendar_days = max(25, int(target_rn * 1.6) + 20)
    
    async with AsyncSessionLocal() as session:
        # Find latest candle timestamp in the DB
        start_time = time.time()
        max_ts_res = await session.execute(text("SELECT MAX(candle_ts) FROM stock_candle WHERE timeframe = 1440"))
        max_ts = max_ts_res.scalar()
        print(f"Max candle_ts in DB: {max_ts} (fetched in {time.time() - start_time:.4f}s)")
        
        if not max_ts:
            print("No candles found in database.")
            return
            
        cutoff_date = max_ts - timedelta(days=calendar_days)
        print(f"Computed cutoff_date: {cutoff_date}")
        
        sql = text("""
            WITH candle_ranks AS (
                SELECT 
                    instrument_id,
                    candle_ts,
                    close,
                    volume,
                    ROW_NUMBER() OVER (PARTITION BY instrument_id ORDER BY candle_ts DESC) as rn,
                    COUNT(*) OVER (PARTITION BY instrument_id) as total_candles
                FROM stock_candle
                WHERE timeframe = 1440 AND candle_ts >= :cutoff_date
            ),
            latest_candles AS (
                SELECT instrument_id, close, volume, candle_ts FROM candle_ranks WHERE rn = 1
            ),
            prev_candles AS (
                SELECT instrument_id, close FROM candle_ranks WHERE rn = LEAST(:target_rn, total_candles)
            ),
            prev_10_candles AS (
                SELECT instrument_id, close FROM candle_ranks WHERE rn = 11
            )
            SELECT 
                im.symbol,
                im.company_name,
                im.sector,
                lc.close as latest_close,
                pc.close as prev_close,
                p10.close as prev_10_close,
                lc.volume as latest_volume,
                fm.market_cap as market_cap
            FROM instrument_master im
            JOIN latest_candles lc ON im.instrument_id = lc.instrument_id
            LEFT JOIN prev_candles pc ON im.instrument_id = pc.instrument_id
            LEFT JOIN prev_10_candles p10 ON im.instrument_id = p10.instrument_id
            LEFT JOIN fundamental_metrics fm ON im.symbol = fm.symbol
            WHERE im.is_active = TRUE
        """)
        
        start_time = time.time()
        result = await session.execute(sql, {"target_rn": target_rn, "cutoff_date": cutoff_date})
        rows = result.fetchall()
        duration = time.time() - start_time
        
    print(f"Heatmap query completed in: {duration:.4f} seconds")
    print(f"Number of rows fetched: {len(rows)}")
    if rows:
        print("Sample row:", rows[0])

if __name__ == "__main__":
    asyncio.run(test_heatmap_query())
