
import asyncio
import logging
import sys

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock environment/modules if needed
sys.path.append("/app")

async def test_yfinance():
    print("\n--- Testing yFinance ---")
    try:
        from utils.market_fallback import fetch_live_indices_yfinance
        data = await fetch_live_indices_yfinance()
        print(f"yFinance Result: {data}")
    except Exception as e:
        print(f"yFinance Failed: {e}")

async def test_db_fallback():
    print("\n--- Testing Database Fallback ---")
    try:
        from database import AsyncSessionLocal
        from sqlalchemy import text
        
        INDEX_MAPPINGS = [
            ("NIFTY 50", "NSE_INDEX|Nifty 50"),
            ("BANK NIFTY", "NSE_INDEX|Nifty Bank"),
            ("INDIA VIX", "NSE_INDEX|India VIX"),
        ]
        
        async with AsyncSessionLocal() as session:
            for name, _ in INDEX_MAPPINGS:
                query = text("""
                    SELECT sc.close, sc.candle_ts 
                    FROM stock_candle sc
                    JOIN instrument_master im ON sc.instrument_id = im.instrument_id
                    WHERE im.symbol = :symbol AND sc.timeframe = 1440
                    ORDER BY sc.candle_ts DESC LIMIT 1
                """)
                res = await session.execute(query, {"symbol": name})
                row = res.first()
                print(f"DB Check for {name}: {row}")
    except Exception as e:
        print(f"DB Fallback Failed: {e}")

async def run_debug():
    await test_yfinance()
    await test_db_fallback()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_debug())
