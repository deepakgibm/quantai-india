"""
Test Upstox connection and token validity
"""
import asyncio
from services.upstox_client import get_upstox_client

async def test_connection():
    print("\n" + "="*60)
    print("Testing Upstox API Connection")
    print("="*60)
    
    client = get_upstox_client()
    
    try:
        # Test 1: Get Nifty 200 symbols
        print("\n1. Fetching Nifty 200 symbols...")
        symbols = await client.get_nifty_200_symbols()
        print(f"✓ Retrieved {len(symbols)} symbols")
        print(f"  First 5: {[s[0] for s in symbols[:5]]}")
        
        # Test 2: Test API with one stock
        if symbols:
            symbol, instrument_key = symbols[0]
            print(f"\n2. Testing data fetch for {symbol}...")
            
            from datetime import datetime, timedelta
            to_date = datetime.now()
            from_date = to_date - timedelta(days=7)
            
            df = await client.get_historical_data(
                symbol=symbol,
                instrument_key=instrument_key,
                from_date=from_date,
                to_date=to_date,
                interval="1day"
            )
            
            print(f"✓ Retrieved {len(df)} data points")
            print(f"  Columns: {list(df.columns)}")
            if not df.empty:
                print(f"  Latest close: ₹{df.iloc[-1]['close']:.2f}")
        
        print("\n" + "="*60)
        print("✅ Upstox connection successful!")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        print("\nPlease check:")
        print("1. UPSTOX_ACCESS_TOKEN is correct in .env")
        print("2. Token hasn't expired")
        print("3. Network connection")
        return False

if __name__ == "__main__":
    asyncio.run(test_connection())
