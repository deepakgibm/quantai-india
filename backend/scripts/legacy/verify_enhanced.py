import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from services.upstox_price_resolver import get_upstox_price_resolver
from services.live_price_enricher import get_live_ltp

async def verify_enhanced_consistency():
    symbol = "RELIANCE"
    print(f"--- Verifying Enhanced Price Consistency for {symbol} ---")
    
    resolver = get_upstox_price_resolver()
    
    # 1. Direct Resolver call
    res_data = await resolver.get_price(symbol)
    print(f"RESOLVER: {res_data['price']} | CHANGE: {res_data['change_pct']}% | PREV: {res_data['prev_close']}")
    
    # 2. Legacy individual call (refactored)
    legacy = await get_live_ltp(symbol)
    print(f"LEGACY: {legacy['ltp']} | SOURCE: {legacy['source']} | P_SOURCE: {legacy.get('price_source')}")
    
    # Simple check for field presence
    if 'change_pct' in res_data and 'prev_close' in res_data:
        print("\n✅ SUCCESS: Enhanced contract (change_pct, prev_close) is active.")
    else:
        print("\n❌ FAILURE: Missing performance metrics in Resolver contract!")

if __name__ == "__main__":
    asyncio.run(verify_enhanced_consistency())
