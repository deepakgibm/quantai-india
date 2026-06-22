import asyncio
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from services.upstox_client import get_upstox_client

async def main():
    client = get_upstox_client()
    intervals = ['1minute', '5minute', '15minute', '30minute', '1hour', 'day', 'week', 'month']
    
    # Audit 90-day availability
    to_date = datetime.now()
    from_date = to_date - timedelta(days=90)
    
    print("=== Phase 1: 90 Days Lookback Audit ===")
    for inter in intervals:
        try:
            df = await client.get_historical_data('RELIANCE', 'NSE_EQ|INE002A01018', from_date, to_date, inter)
            if df.empty:
                print(f"{inter:<10}: Returned EMPTY dataframe (or was caught as error/unsupported by wrapper).")
            else:
                print(f"{inter:<10}: SUCCESS. len={len(df)}, earliest={df['timestamp'].min()}, latest={df['timestamp'].max()}")
        except Exception as e:
            print(f"{inter:<10}: FAILED with exception: {e}")

    # Audit maximum lookback supported for each interval by pushing from_date back to 10 years
    print("\n=== Phase 2: Maximum Supported Range Probing ===")
    lookbacks = [30, 90, 365, 365*2, 365*5]
    for inter in ['1minute', '30minute', 'day']:
        print(f"\nProbing limits for interval: {inter}")
        for days in lookbacks:
            probe_from = to_date - timedelta(days=days)
            try:
                # We bypass the chunking in get_historical_data to see what a single raw API request supports
                df = await client._get_historical_data_single('RELIANCE', 'NSE_EQ|INE002A01018', probe_from, to_date, inter)
                if df.empty:
                    print(f"  lookback={days:<5} days: FAILED (Returned empty)")
                else:
                    print(f"  lookback={days:<5} days: SUCCESS. len={len(df)}, earliest={df['timestamp'].min()}")
            except Exception as e:
                print(f"  lookback={days:<5} days: FAILED with exception: {e}")

if __name__ == "__main__":
    asyncio.run(main())
