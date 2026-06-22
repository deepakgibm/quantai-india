import sys
from pathlib import Path

# Add backend directory to path
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

from services.cache import get_cache_manager

def seed():
    cache = get_cache_manager()
    if not cache.is_available():
        print("Cache is not available!")
        return

    # mock data structure for option flow
    mock_data = {
        "status": "success",
        "symbol": "RELIANCE",
        "expiry": "2026-05-28",
        "total_call_oi": 15000,
        "total_put_oi": 12000,
        "total_call_volume": 5000,
        "total_put_volume": 4000,
        "total_call_premium": 250000.0,
        "total_put_premium": 180000.0,
        "net_flow": 70000.0,
        "buy_sell_ratio": 1.39,
        "pcr_oi": 0.8,
        "pcr_volume": 0.8,
        "sentiment": "Neutral",
        "strikes": [
            {
                "strike_price": 2400.0,
                "call": {
                    "oi": 5000,
                    "oi_change": 100,
                    "volume": 2000,
                    "ltp": 50.0,
                    "bid": 49.5,
                    "ask": 50.5,
                    "premium": 100000.0,
                    "iv": 15.5
                },
                "put": {
                    "oi": 2000,
                    "oi_change": -50,
                    "volume": 1000,
                    "ltp": 12.0,
                    "bid": 11.5,
                    "ask": 12.5,
                    "premium": 12000.0,
                    "iv": 17.2
                }
            },
            {
                "strike_price": 2500.0,
                "call": {
                    "oi": 10000,
                    "oi_change": 500,
                    "volume": 3000,
                    "ltp": 15.0,
                    "bid": 14.8,
                    "ask": 15.2,
                    "premium": 150000.0,
                    "iv": 14.8
                },
                "put": {
                    "oi": 10000,
                    "oi_change": 800,
                    "volume": 3000,
                    "ltp": 56.0,
                    "bid": 55.5,
                    "ask": 56.5,
                    "premium": 168000.0,
                    "iv": 16.0
                }
            }
        ],
        "block_deals": [
            {
                "strike_price": 2500.0,
                "type": "CE",
                "ltp": 15.0,
                "volume": 3000,
                "premium": 150000.0,
                "oi": 10000
            },
            {
                "strike_price": 2500.0,
                "type": "PE",
                "premium": 168000.0,
                "volume": 3000,
                "ltp": 56.0,
                "oi": 10000
            }
        ]
    }

    cache_key = "option_flow:RELIANCE:2026-05-28:all:fallback"
    print(f"Setting key: {cache_key}")
    cache.set(cache_key, mock_data, ttl=604800)
    print("Verification:")
    val = cache.get(cache_key)
    if val:
        print("Successfully read back from cache! Symbol is:", val.get("symbol"))
    else:
        print("Failed to read back from cache!")

if __name__ == "__main__":
    seed()
