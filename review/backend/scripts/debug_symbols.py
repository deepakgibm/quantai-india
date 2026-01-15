import asyncio
from services.yearly_breakout_engine import YearlyBreakoutEngine

async def debug_symbols():
    engine = YearlyBreakoutEngine()
    symbols = await engine.get_nifty500_symbols()
    print(f"Total symbols: {len(symbols)}")
    print(f"First 10: {[s['symbol'] for s in symbols[:10]]}")
    
    etfs = [s['symbol'] for s in symbols if any(ext in s['symbol'].upper() for ext in ["ETF", "BEES", "GOLD", "SILVER"])]
    print(f"ETFs found: {etfs}")
    
    na_industry = [s['symbol'] for s in symbols if (s.get('industry') or "").strip().upper() in ["N/A", "NULL", "NONE", ""]]
    print(f"N/A Industry found: {len(na_industry)}")

if __name__ == "__main__":
    asyncio.run(debug_symbols())
