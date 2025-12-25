import sys
sys.path.insert(0, '.')

from services.db_data_fetcher import get_db_data_fetcher

fetcher = get_db_data_fetcher()
print("Testing database fetcher...")

data = fetcher.fetch_latest_data()
print(f"Got {len(data)} results")

if data:
    # Print first 3
    for i, (symbol, tick) in enumerate(list(data.items())[:3]):
        print(f"  {symbol}: ltp={tick.ltp}, change={tick.change_pct}%")
else:
    print("No data returned!")
