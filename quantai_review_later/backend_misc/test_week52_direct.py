import sys
import time

# Test the service directly
start = time.time()
print("Importing service...")

try:
    from services.week52_breakout_service import get_week52_breakout_service
    print(f"Import took {time.time()-start:.2f}s")
    
    print("Getting service...")
    service = get_week52_breakout_service()
    print(f"Service initialized in {time.time()-start:.2f}s")
    
    print("Detecting breakouts...")
    data = service.detect_breakouts()
    print(f"Detection took {time.time()-start:.2f}s total")
    
    print(f"\n====== RESULTS ======")
    print(f"High Breakouts: {len(data.get('high_breakouts', []))}")
    print(f"Low Breakdowns: {len(data.get('low_breakdowns', []))}")
    
    if data.get('high_breakouts'):
        print("\n=== 52-Week HIGH BREAKOUTS ===")
        for stock in data['high_breakouts'][:5]:
            print(f"  {stock['symbol']}: LTP={stock['ltp']}, 52W High={stock['high_52w']}, Breakout%={stock['breakout_pct']}%, Vol Ratio={stock['volume_ratio']}x")
    
    if data.get('low_breakdowns'):
        print("\n=== 52-Week LOW BREAKDOWNS ===")
        for stock in data['low_breakdowns'][:5]:
            print(f"  {stock['symbol']}: LTP={stock['ltp']}, 52W Low={stock['low_52w']}, Breakdown%={stock['breakout_pct']}%, Vol Ratio={stock['volume_ratio']}x")
    
    print("\n====== SUCCESS ======")

except Exception as e:
    import traceback
    print(f"Error: {e}")
    traceback.print_exc()
