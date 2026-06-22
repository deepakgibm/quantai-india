import sys
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

from sqlalchemy import create_engine, text
from config import settings

def main():
    engine = create_engine(settings.SYNC_DATABASE_URL)
    cutoff = datetime.now() - timedelta(days=45)
    
    with engine.connect() as conn:
        # Stock
        stock_query = text("""
            SELECT sc.candle_ts as timestamp, sc.close
            FROM stock_candle sc
            JOIN instrument_master im ON sc.instrument_id = im.instrument_id
            WHERE im.symbol = 'RELIANCE' AND sc.timeframe = 1440 AND sc.candle_ts >= :cutoff
            ORDER BY sc.candle_ts ASC
        """)
        stock_rows = conn.execute(stock_query, {"cutoff": cutoff}).fetchall()
        
        # Nifty
        nifty_query = text("""
            SELECT sc.candle_ts as timestamp, sc.close
            FROM stock_candle sc
            JOIN instrument_master im ON sc.instrument_id = im.instrument_id
            WHERE im.symbol = 'NIFTY 50' AND sc.timeframe = 1440 AND sc.candle_ts >= :cutoff
            ORDER BY sc.candle_ts ASC
        """)
        nifty_rows = conn.execute(nifty_query, {"cutoff": cutoff}).fetchall()
        
        stock_df = pd.DataFrame(stock_rows, columns=["timestamp", "stock_close"])
        nifty_df = pd.DataFrame(nifty_rows, columns=["timestamp", "nifty_close"])
        
        print("Stock DF timestamp type:", stock_df["timestamp"].dtype)
        print("Nifty DF timestamp type:", nifty_df["timestamp"].dtype)
        
        merged = pd.merge(stock_df, nifty_df, on="timestamp")
        print("Merged length:", len(merged))
        if not merged.empty:
            print("Merged DF Head:")
            print(merged.head())
            print("Merged DF Tail:")
            print(merged.tail())
            
            merged["stock_ret"] = merged["stock_close"].pct_change()
            merged["nifty_ret"] = merged["nifty_close"].pct_change()
            print("\nafter pct_change:")
            print(merged[["timestamp", "stock_close", "stock_ret", "nifty_close", "nifty_ret"]].tail())
            
            merged_clean = merged.dropna()
            print(f"\nmerged_clean length: {len(merged_clean)}")
            
            stock_change_pct = float(merged_clean["stock_ret"].iloc[-1] * 100) if not merged_clean.empty else 0.0
            nifty_change_pct = float(merged_clean["nifty_ret"].iloc[-1] * 100) if not merged_clean.empty else 0.0
            print(f"stock_change_pct (iloc[-1] * 100): {stock_change_pct}")
            print(f"nifty_change_pct (iloc[-1] * 100): {nifty_change_pct}")

if __name__ == "__main__":
    main()
