import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.rest_data_fetcher import get_rest_data_fetcher

async def test_indices():
    fetcher = get_rest_data_fetcher()
    # Indices are now in self._symbols
    symbols = [s for s in fetcher._symbols if s[0] in ["NIFTY 50", "BANK NIFTY", "INDIA VIX"]]
    print(f"Polling symbols: {symbols}")
    results = await fetcher.fetch_quotes(symbols)
    for symbol, tick in results.items():
        print(f"{symbol}: {tick.ltp} ({tick.change_pct}%) [Source: {tick.source}]")

if __name__ == "__main__":
    asyncio.run(test_indices())
