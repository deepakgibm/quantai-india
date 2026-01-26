
import httpx
import asyncio
from datetime import datetime

BASE_URL = "http://localhost:8000"

# Official EOD Prices for Jan 13 (verified from ETL logs/Redis)
OFFICIAL_PRICES = {
    "ADANIENSOL": 932.5,
    "RELIANCE": 1452.8,
    "HDFCBANK": 1437.35,
    "INFY": 1599.0
}

async def check_endpoint(client, path, description, samples=None):
    print(f"Testing {description} ({path})...")
    try:
        response = await client.get(f"{BASE_URL}{path}")
        if response.status_code != 200:
            print(f"  FAILED: Status {response.status_code}")
            return False
        
        data = response.json()
        print(f"  SUCCESS: Status 200")
        
        if samples:
            # Check for specific prices in the response
            # Note: The structure varies between endpoints
            found_all = True
            for symbol, expected_price in samples.items():
                price_found = None
                
                # Check top-level list (common for scanner/ai)
                stocks = data.get("stocks", data.get("data", []))
                if isinstance(stocks, list):
                    for s in stocks:
                        s_sym = s.get("symbol", "").upper()
                        if s_sym == symbol:
                            price_found = s.get("current_price", s.get("ltp", s.get("price")))
                            break
                
                # Check sector heatmap structure
                elif isinstance(data.get("heatmap"), dict):
                     # Logic for complex heatmap dict if needed
                     pass

                if price_found is not None:
                    if abs(float(price_found) - expected_price) < 0.01:
                        print(f"    v {symbol}: {price_found} matches official EOD price.")
                    else:
                        print(f"    FAILED: {symbol}: {price_found} DOES NOT match expected {expected_price}!")
                        found_all = False
                else:
                    print(f"    WARNING: {symbol}: Not present in this response.")
            
            return found_all
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        return False

async def main():
    print(f"Comprehensive Backend Verification - {datetime.now().isoformat()}")
    print("Compare API output with official market close data.\n")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. AI Trend Finder (The specific fix target)
        await check_endpoint(client, "/api/ai/trend-finder", "AI Trend Finder", OFFICIAL_PRICES)
        
        # 2. Trading Top Gainers
        await check_endpoint(client, "/api/trading/top-gainers", "Trading Top Gainers", OFFICIAL_PRICES)
        
        # 3. HP Scanner v3 Snapshots
        await check_endpoint(client, "/api/v3/scanner/snapshots", "HP Scanner Snapshots", OFFICIAL_PRICES)
        
        # 4. Market Top Movers
        await check_endpoint(client, "/api/market/nifty100/top-movers", "Market Top Movers", OFFICIAL_PRICES)
        
        # 5. Sector Heatmap (Sample sector: Energy)
        # Note: Heatmap usually uses symbols but might use names in some views
        # We'll just check if it's reachable for now
        await check_endpoint(client, "/api/heatmap/sector/Energy", "Energy Sector Heatmap", OFFICIAL_PRICES)

    print("\nVerification process complete.")

if __name__ == "__main__":
    asyncio.run(main())
