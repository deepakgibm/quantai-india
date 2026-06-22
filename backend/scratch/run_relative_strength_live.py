import asyncio
import sys
import logging
import traceback
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from config import settings

logging.basicConfig(level=logging.INFO)

async def main():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        print("Executing compute_relative_strength_analytics for RELIANCE...")
        try:
            cutoff = datetime.now() - timedelta(days=45)
            from sqlalchemy import text
            import pandas as pd
            
            # Stock
            stock_query = text("""
                SELECT sc.candle_ts as timestamp, sc.close
                FROM stock_candle sc
                JOIN instrument_master im ON sc.instrument_id = im.instrument_id
                WHERE im.symbol = 'RELIANCE' AND sc.timeframe = 1440 AND sc.candle_ts >= :cutoff
                ORDER BY sc.candle_ts ASC
            """)
            stock_res = await db.execute(stock_query, {"cutoff": cutoff})
            stock_rows = stock_res.fetchall()
            
            # Nifty
            nifty_query = text("""
                SELECT sc.candle_ts as timestamp, sc.close
                FROM stock_candle sc
                JOIN instrument_master im ON sc.instrument_id = im.instrument_id
                WHERE im.symbol = 'NIFTY 50' AND sc.timeframe = 1440 AND sc.candle_ts >= :cutoff
                ORDER BY sc.candle_ts ASC
            """)
            nifty_res = await db.execute(nifty_query, {"cutoff": cutoff})
            nifty_rows = nifty_res.fetchall()
            
            stock_df = pd.DataFrame(stock_rows, columns=["timestamp", "stock_close"])
            nifty_df = pd.DataFrame(nifty_rows, columns=["timestamp", "nifty_close"])
            
            # CONVERSION TO FLOAT FIX:
            stock_df["stock_close"] = stock_df["stock_close"].astype(float)
            nifty_df["nifty_close"] = nifty_df["nifty_close"].astype(float)
            
            merged = pd.merge(stock_df, nifty_df, on="timestamp")
            
            print("Running pct_change...")
            merged["stock_ret"] = merged["stock_close"].pct_change()
            merged["nifty_ret"] = merged["nifty_close"].pct_change()
            
            print("Dropping NaNs...")
            merged = merged.dropna()
            
            print("Computing corr...")
            correlation = float(merged["stock_ret"].corr(merged["nifty_ret"]))
            
            print("Computing cov...")
            cov = merged["stock_ret"].cov(merged["nifty_ret"])
            
            print("Computing var...")
            nifty_var = merged["nifty_ret"].var()
            
            print("Computing beta...")
            beta = float(cov / nifty_var) if nifty_var > 0 else 1.0
            
            print("Success! beta =", beta, "correlation =", correlation)
            
        except Exception as e:
            traceback.print_exc()

if __name__ == "__main__":
    from datetime import datetime, timedelta
    asyncio.run(main())
