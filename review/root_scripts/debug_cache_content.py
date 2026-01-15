import asyncio
import sys
import os
import json

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from services.memcached_client import get_cache, CacheKeys

async def main():
    try:
        cache = get_cache()
        key = CacheKeys.all_snapshots()
        print(f"Checking Cache Key: {key}")
        
        data = cache.get(key)
        
        if not data:
            print("❌ Cache is EMPTY for 'all_snapshots'")
            # Check if any keys exist
            print("Checking if any 'qai:*' keys exist (requires Redis client)...")
            # This simple client might not support 'keys', so we trust the 'get'.
        else:
            print(f"✅ Cache found! Type: {type(data)}")
            if isinstance(data, list):
                print(f"Count: {len(data)}")
                if len(data) > 0:
                    print("First item sample:")
                    print(json.dumps(data[0], indent=2))
                    
                    # Check for critical fields required by TopMoversService
                    # symbol, ltp, prev_close OR change_percent
                    sample = data[0]
                    missing = []
                    if 'symbol' not in sample: missing.append('symbol')
                    if 'ltp' not in sample: missing.append('ltp')
                    if 'change_percent' not in sample and 'prev_close' not in sample: missing.append('change_percent OR prev_close')
                    
                    if missing:
                        print(f"⚠️ Critical fields missing in snapshot: {missing}")
                    else:
                        print("✅ Snapshot structure looks valid for TopMoversService")
            else:
                print(f"⚠️ Unknown data format: {data}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
