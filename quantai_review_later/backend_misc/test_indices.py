
import asyncio
from services.upstox_client import get_upstox_client

async def test_indices():
    client = get_upstox_client()
    indices = [
        ("Nifty 50", "NSE_INDEX|Nifty 50"),
        ("Nifty Bank", "NSE_INDEX|Nifty Bank"),
        ("Nifty IT", "NSE_INDEX|Nifty IT"),
        ("Nifty Auto", "NSE_INDEX|Nifty Auto"),
        ("Nifty FMCG", "NSE_INDEX|Nifty FMCG"),
        ("Nifty Pharma", "NSE_INDEX|Nifty Pharma"),
        ("Nifty Metal", "NSE_INDEX|Nifty Metal"),
        ("Nifty Realty", "NSE_INDEX|Nifty Realty"),
        ("Nifty Energy", "NSE_INDEX|Nifty Energy"),
        ("Nifty Infra", "NSE_INDEX|Nifty Infra"),
        ("Nifty Media", "NSE_INDEX|Nifty Media"),
    ]
    
    print(f"Testing {len(indices)} indices...")
    for name, key in indices:
        try:
            quote = await client.get_live_quote(key, name)
            if quote:
                cp = quote.get('last_price')
                op = quote.get('open')
                if cp and op:
                    change = ((cp - op) / op) * 100
                    print(f"✅ {name:15}: {cp:8.2f} ({change:+.2f}%)")
                else:
                    print(f"⚠️ {name:15}: {cp} (Missing open/close)")
            else:
                print(f"❌ {name:15}: No quote returned")
        except Exception as e:
            print(f"❌ {name:15}: Error {e}")

if __name__ == "__main__":
    asyncio.run(test_indices())
