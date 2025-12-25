"""Debug Upstox quote response to see what data is returned"""
import asyncio
import sys
sys.path.insert(0, '.')

from services.upstox_client import get_upstox_client

async def main():
    client = get_upstox_client()
    
    indices = [
        ("NIFTY 50", "NSE_INDEX|Nifty 50"),
        ("BANK NIFTY", "NSE_INDEX|Nifty Bank"),
        ("INDIA VIX", "NSE_INDEX|India VIX"),
    ]
    
    for name, key in indices:
        print(f"\n--- {name} ---")
        quote = await client.get_live_quote(key, name)
        if quote:
            print(f"  last_price: {quote.get('last_price')}")
            print(f"  previous_close: {quote.get('previous_close')}")
            print(f"  net_change: {quote.get('net_change')}")
            print(f"  change_percent: {quote.get('change_percent')}")
            print(f"  All data: {quote}")
        else:
            print("  No quote returned!")

if __name__ == "__main__":
    asyncio.run(main())
