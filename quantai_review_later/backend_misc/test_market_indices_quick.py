"""Quick test of market indices endpoint"""
import asyncio
from services.upstox_client import get_upstox_client

async def test_upstox():
    client = get_upstox_client()
    
    # Test NIFTY 50 quote
    print("Testing Upstox API for NIFTY 50...")
    try:
        quote = await client.get_live_quote("NSE_INDEX|Nifty 50", "NIFTY 50")
        if quote and quote.get("last_price", 0) > 0:
            print(f"✓ Upstox working! NIFTY 50 LTP: {quote['last_price']}")
            print(f"  Change: {quote.get('net_change', 0)}, Prev Close: {quote.get('previous_close', 0)}")
            return True
        else:
            print(f"✗ Upstox returned no data: {quote}")
    except Exception as e:
        print(f"✗ Upstox error: {e}")
    
    return False

async def test_yfinance():
    print("\nTesting yfinance fallback...")
    try:
        import yfinance as yf
        ticker = yf.Ticker("^NSEI")
        hist = ticker.history(period="2d")
        if len(hist) >= 2:
            prev_close = hist['Close'].iloc[-2]
            curr_value = hist['Close'].iloc[-1]
            change = curr_value - prev_close
            percent = (change / prev_close) * 100
            print(f"✓ yfinance working! NIFTY 50: {curr_value:.2f}")
            print(f"  Change: {change:.2f} ({percent:.2f}%)")
            return True
        else:
            print(f"✗ yfinance returned insufficient data: {len(hist)} rows")
    except Exception as e:
        print(f"✗ yfinance error: {e}")
    
    return False

if __name__ == "__main__":
    upstox_ok = asyncio.run(test_upstox())
    yf_ok = asyncio.run(test_yfinance())
    
    print("\n" + "="*50)
    if upstox_ok:
        print("✓ Primary data source (Upstox) is working")
    elif yf_ok:
        print("⚠ Upstox failed, but yfinance fallback is working")
    else:
        print("✗ Both data sources failed - will use mock data")
