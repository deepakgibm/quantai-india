import sys
import os
sys.path.append(os.getcwd())

from services.top5_buysell import Top5BuySellEngine
from datetime import datetime, timedelta

def verify_top5():
    print("Initializing Engine...")
    engine = Top5BuySellEngine()
    
    # Manually run the query part to see data count
    session = engine._Session()
    try:
        cutoff = datetime.now() - timedelta(days=100)
        print(f"Querying data since {cutoff}...")
        
        # Check raw count
        from models import StockCandle
        count = session.query(StockCandle).filter(
            StockCandle.timeframe == 1440,
            StockCandle.candle_ts >= cutoff
        ).count()
        print(f"Row count in window: {count}")
        
        if count == 0:
            print("[WARN] No data in window.")
            return

        # Run vectorized scan
        print("\nRunning vectorized scan...")
        results = engine.scan_all()
        print(f"Results: {len(results.get('buy', []))} BUY, {len(results.get('sell', []))} SELL")
        
        if not results['buy'] and not results['sell']:
            print("[INFO] 0 Results returned (Likely due to score filtering on limited data).")
            
    except Exception as e:
        print(f"[ERROR] Exception during verification: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    verify_top5()
