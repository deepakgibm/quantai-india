import asyncio
import sys
from database import SessionLocal
from services.auth.token_manager import TokenManagerService
from services.upstox_client import get_upstox_client

async def validate_token():
    token = sys.argv[1]
    
    # 1. Store the token using our TokenManagerService
    db = SessionLocal()
    try:
        manager = TokenManagerService(db)
        # set_analytics_token handles system user and encryption internaly
        success = manager.set_analytics_token(plaintext_token=token)
        if success:
            print("Token stored in PostgreSQL vault successfully.")
        else:
            print("Failed to store token.")
            sys.exit(1)
    except Exception as e:
        print(f"Error storing token: {e}")
        sys.exit(1)

    # 2. Re-fetch via upstox client to validate it works
    print("Testing token against Upstox Market Data endpoints...")
    client = get_upstox_client()
    try:
        # Analytics tokens are often restricted to market data, so we test an index quote
        symbol = "NSE_INDEX|Nifty 50"
        data = await client.get_live_quotes([symbol])
        if data and symbol in data:
            print(f"Successfully validated Analytics Token with {symbol} endpoint!")
            quote = data[symbol]
            print(f"LTP: {quote.get('last_price')} (Prev Close: {quote.get('previous_close')})")
        else:
            print(f"Upstox API returned no data for {symbol}. Check if market is open or token scope.")
            print(f"Raw API Response: {data}")
    except Exception as e:
        print(f"Failed to query Upstox using new token. Error: {e}")

if __name__ == "__main__":
    asyncio.run(validate_token())
