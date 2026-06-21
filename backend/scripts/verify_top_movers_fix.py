import httpx
import asyncio
import json

async def main():
    url = "http://localhost:8000/api/market/nifty100/top-movers?refresh=true"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30)
            if response.status_code == 200:
                data = response.json()
                print("Top Movers Data Fetch Successful")
                print(f"Source: {data.get('source')}")
                
                print("\nTop Gainers (First 3):")
                for g in data.get("gainers", [])[:3]:
                    print(f" - {g['symbol']}: {g['ltp']} (Prev: {g['prev_close']}, Chg: {g['change_pct']}%)")
                
                print("\nTop Losers (First 3):")
                for l in data.get("losers", [])[:3]:
                    print(f" - {l['symbol']}: {l['ltp']} (Prev: {l['prev_close']}, Chg: {l['change_pct']}%)")
                
                # Check for 0.00% issue
                all_raw = data.get("gainers", []) + data.get("losers", [])
                zero_chg = [s['symbol'] for s in all_raw if s['change_pct'] == 0]
                if zero_chg and len(zero_chg) == len(all_raw):
                    print("\nWARNING: All change percentages are still 0.00%")
                else:
                    print(f"\nSUCCESS: {len(all_raw) - len(zero_chg)}/{len(all_raw)} symbols have non-zero change.")
            else:
                print(f"Error: {response.status_code}")
                try:
                    print(f"Detail: {json.dumps(response.json(), indent=2)}")
                except:
                    print(f"Raw Response: {response.text[:200]}")
    except httpx.ConnectError:
        print("Connection failed: Server is not reachable on localhost:8000")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
