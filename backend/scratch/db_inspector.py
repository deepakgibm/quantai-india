import asyncio
import sys
from sqlalchemy import text
from database import AsyncSessionLocal

async def inspect():
    async with AsyncSessionLocal() as session:
        queries = {
            "instrument_master_count": "SELECT COUNT(*) FROM instrument_master",
            "active_instruments": "SELECT COUNT(*) FROM instrument_master WHERE is_active = TRUE",
            "distinct_sectors": "SELECT DISTINCT sector FROM instrument_master",
            "stock_candle_count": "SELECT COUNT(*) FROM stock_candle",
            "stock_candle_timeframes": "SELECT DISTINCT timeframe FROM stock_candle",
            "fundamental_metrics_count": "SELECT COUNT(*) FROM fundamental_metrics",
            "screener_financials_count": "SELECT COUNT(*) FROM screener_financials",
            "screener_stock_score_count": "SELECT COUNT(*) FROM screener_stock_score",
            "upstox_tokens": "SELECT COUNT(*) FROM auth_token"
        }
        for name, query in queries.items():
            try:
                res = await session.execute(text(query))
                if "distinct" in name:
                    rows = res.fetchall()
                    sectors = [r[0] for r in rows if r[0]]
                    print(f"{name}: {len(sectors)} items -> {sectors[:10]}")
                else:
                    print(f"{name}: {res.scalar()}")
            except Exception as e:
                print(f"Error executing {name}: {e}")

if __name__ == "__main__":
    asyncio.run(inspect())
