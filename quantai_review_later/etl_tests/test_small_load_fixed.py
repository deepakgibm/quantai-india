'''Test script for Upstox historical data loading (small subset)'''
import asyncio
import os
import sys
from datetime import datetime, timedelta

# Ensure project root is on PYTHONPATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(project_root)

from backend.etl.historical_loader import HistoricalLoader
from backend.database import AsyncSessionLocal

async def main():
    loader = HistoricalLoader()
    # Load all symbols then limit to first 5 for quick test
    await loader.load_symbols()
    loader.symbols = loader.symbols[:5]
    # Short date range: last 7 days
    to_date = datetime.now()
    from_date = to_date - timedelta(days=7)
    async with AsyncSessionLocal() as session:
        for symbol, instrument_key in loader.symbols:
            print(f"Fetching {symbol} from {from_date.date()} to {to_date.date()}")
            await loader.fetch_and_store(symbol, instrument_key, from_date, to_date, session)
            await session.commit()
    print("Test load complete.")

if __name__ == '__main__':
    asyncio.run(main())
