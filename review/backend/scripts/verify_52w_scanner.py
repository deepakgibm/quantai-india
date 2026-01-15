import asyncio
import logging
from services.yearly_breakout_engine import YearlyBreakoutEngine

async def verify_scanner():
    logging.basicConfig(level=logging.INFO)
    engine = YearlyBreakoutEngine()
    
    print("\n[1] Verifying NIFTY 500 Universe Enforcement...")
    symbols = await engine.get_nifty500_symbols()
    print(f"Total symbols after strict filtering: {len(symbols)}")
    
    if not symbols:
        print("❌ FAILED: No symbols returned. Check if DB is populated and fetcher is working.")
        return

    # Specific check for user reported ETFs
    reported_etfs = ["VAL30IETF", "MIDCAPADD", "EGOLD", "METALIETF", "AUTOIETF", "LICMFGOLD"]
    found_etfs = [s for s in symbols if s['symbol'] in reported_etfs]
    print(f"Reported ETFs found in filtered list: {len(found_etfs)} ({found_etfs})")
    
    # Check for N/A industry
    invalid_industry = [s for s in symbols if (s.get('industry') or "").strip().upper() in ["N/A", "NULL", "NONE", ""]]
    print(f"Symbols with N/A industry found: {len(invalid_industry)}")
    
    # Check for non-EQ instruments
    non_eq = [s for s in symbols if not s['instrument_key'].startswith("NSE_EQ|")]
    print(f"Non-EQ instruments found: {len(non_eq)}")
    
    if symbols:
        print(f"\n[2] Testing Bucketing Logic for sample: {symbols[0]['symbol']}...")
        result = await engine.process_stock(symbols[0])
        if result:
            print(f"Result symbol: {result.symbol}, industry: {result.industry}")
            print(f"Bucket: {result.bucket_type}")
        else:
            print("Stock did not qualify for any bucket.")

if __name__ == "__main__":
    asyncio.run(verify_scanner())
