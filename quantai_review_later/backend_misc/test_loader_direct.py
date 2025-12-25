
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent))

from services.intraday_loader import IntradayDataLoader

async def test():
    print("Initializing Loader...")
    loader = IntradayDataLoader()
    symbols = loader.get_nifty500_symbols()
    if not symbols:
        print("No symbols found in database!")
        return
        
    sym, key = symbols[0]
    print(f"Testing connectivity for {sym} ({key})...")
    
    try:
        # Test just 1 minute of data to check connectivity
        to_date = datetime.now()
        from_date = to_date - timedelta(days=2)
        
        print(f"Fetching data from {from_date} to {to_date}...")
        count = await loader.fetch_symbol_data(sym, key, from_date, to_date)
        print(f"Success! Inserted {count} records for {sym}")
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
