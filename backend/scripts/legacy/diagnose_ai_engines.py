import asyncio
from services.mean_reversion_scanner import MeanReversionScanner
from services.top5_buysell import Top5BuySellEngine
from database import SessionLocal
from sqlalchemy import text

async def diagnose_engines():
    print("--- 1. Database Connectivity & Table Check ---")
    session = SessionLocal()
    try:
        # Check Nifty100Daily
        res_nifty = session.execute(text("SELECT COUNT(*) FROM nifty100_daily")).scalar()
        print(f"Nifty100Daily count: {res_nifty}")
        
        # Check StockCandle for 1d timeframe
        res_candle = session.execute(text("SELECT COUNT(*) FROM stock_candle WHERE timeframe = 1440")).scalar()
        print(f"StockCandle (1d) count: {res_candle}")
        
        # Check InstrumentMaster
        res_inst = session.execute(text("SELECT COUNT(*) FROM instrument_master")).scalar()
        print(f"InstrumentMaster count: {res_inst}")
    except Exception as e:
        print(f"DB Error: {e}")
    finally:
        session.close()

    print("\n--- 2. Testing MeanReversionScanner ---")
    try:
        mr_scanner = MeanReversionScanner()
        results = mr_scanner.scan_all(limit=5)
        print(f"MeanReversion results found: {len(results)}")
        for r in results:
            print(f"  - {r['symbol']}: {r['signal']} (Price: {r['current_price']})")
    except Exception as e:
        print(f"MeanReversion Error: {e}")

    print("\n--- 3. Testing Top5BuySellEngine ---")
    try:
        top_engine = Top5BuySellEngine()
        results = top_engine.scan_all(limit=5)
        buy_count = len(results.get('buy', []))
        sell_count = len(results.get('sell', []))
        print(f"Top5BuySell results found: {buy_count} BUY, {sell_count} SELL")
        for r in results.get('buy', []):
            print(f"  - [BUY] {r['symbol']}: {r['confidence']}% (Price: {r['current_price']})")
        for r in results.get('sell', []):
            print(f"  - [SELL] {r['symbol']}: {r['confidence']}% (Price: {r['current_price']})")
    except Exception as e:
        print(f"Top5BuySell Error: {e}")

if __name__ == "__main__":
    asyncio.run(diagnose_engines())
