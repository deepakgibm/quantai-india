import asyncio
import sys
import os
import json

sys.path.append(os.path.abspath("backend"))

from dotenv import load_dotenv
load_dotenv("backend/.env")

from services.nifty100_ranking_service import get_nifty100_ranking_service
from services.upstox_price_resolver import get_upstox_price_resolver
from utils.symbol_utils import get_nifty_symbols

async def main():
    service = get_nifty100_ranking_service()
    resolver = get_upstox_price_resolver()
    symbols = get_nifty_symbols()
    
    print(f"Total symbols from get_nifty_symbols(): {len(symbols)}")
    print(f"Sample symbols: {symbols[:5]}")
    
    print("\n--- Testing Resolver Bulk Prices ---")
    try:
        indices = ["NIFTY 50", "NIFTY BANK", "INDIA VIX", "FINNIFTY", "NIFTY NEXT 50", "MIDCPNIFTY"]
        symbols_to_fetch = list(set([s.upper() for s in (symbols + indices)]))
        prices = await resolver.get_prices_bulk(symbols_to_fetch)
        print(f"Resolver returned {len(prices)} symbols")
        non_zero_prices = {k: v for k, v in prices.items() if v.get("price", 0) > 0}
        print(f"Symbols with price > 0: {len(non_zero_prices)}")
        sample_keys = list(non_zero_prices.keys())[:5]
        for k in sample_keys:
            print(f"  {k}: {non_zero_prices[k]}")
    except Exception as e:
        print(f"Resolver test failed: {e}")
        
    print("\n--- Testing fetch_from_rest directly ---")
    try:
        rest_result = await service._fetch_from_rest()
        if rest_result:
            print(f"Source: {rest_result.source}")
            print(f"Gainers count: {len(rest_result.gainers)}")
            print(f"Losers count: {len(rest_result.losers)}")
            for g in rest_result.gainers[:3]:
                print(f"  Gainer {g['symbol']}: ltp={g['ltp']}, prev_close={g['prev_close']}, change_pct={g['change_pct']}")
            for l in rest_result.losers[:3]:
                print(f"  Loser {l['symbol']}: ltp={l['ltp']}, prev_close={l['prev_close']}, change_pct={l['change_pct']}")
        else:
            print("fetch_from_rest returned None")
    except Exception as e:
        print(f"fetch_from_rest failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
