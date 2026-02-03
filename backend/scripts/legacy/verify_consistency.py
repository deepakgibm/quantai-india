import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from services.upstox_price_resolver import get_upstox_price_resolver
from services.live_price_enricher import get_live_ltp, get_ltp_bulk

async def verify_consistency():
    symbol = "RELIANCE"
    print(f"--- Verifying Price Consistency for {symbol} ---")
    
    resolver = get_upstox_price_resolver()
    
    # 1. Direct Resolver call
    res_data = await resolver.get_price(symbol)
    print(f"RESOLVER: {res_data['price']} | SOURCE: {res_data['price_source']} | TS: {res_data['timestamp']}")
    
    # 2. Legacy individual call (now refactored)
    legacy_individual = await get_live_ltp(symbol)
    print(f"LEGACY_INDIVIDUAL: {legacy_individual['ltp']} | SOURCE: {legacy_individual['source']} | PRICE_SOURCE: {legacy_individual.get('price_source')}")
    
    # 3. Legacy bulk call (now refactored)
    legacy_bulk = await get_ltp_bulk([symbol])
    bulk_data = legacy_bulk.get(symbol, {})
    print(f"LEGACY_BULK: {bulk_data.get('ltp')} | SOURCE: {bulk_data.get('source')} | PRICE_SOURCE: {bulk_data.get('price_source')}")
    
    # Check for drift
    prices = [res_data['price'], legacy_individual['ltp'], bulk_data.get('ltp')]
    if len(set(prices)) == 1:
        print("\n✅ SUCCESS: 100% Price Consistency achieved across all layers.")
    else:
        print("\n❌ FAILURE: Price drift detected!")
        print(f"Prices: {prices}")

if __name__ == "__main__":
    asyncio.run(verify_consistency())
