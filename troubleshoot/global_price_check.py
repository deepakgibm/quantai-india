import asyncio
import sys
import os
import yfinance as yf

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from data.nifty500_instruments import NIFTY_500_MAPPING

async def check():
    target_price = 308.5
    symbols = list(NIFTY_500_MAPPING.keys())
    print(f"Checking {len(symbols)} symbols for price {target_price}...")
    
    # Batch check in chunks of 50
    batch_size = 50
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i+batch_size]
        tickers = " ".join([f"{s}.NS" for s in batch])
        try:
            data = yf.download(tickers, period="2d", interval="1m", progress=False, group_by='ticker')
            for s in batch:
                ticker = f"{s}.NS"
                try:
                    price = data[ticker]['Close'].iloc[-1]
                    if abs(price - target_price) < 0.5:
                        print(f"MATCH FOUND: {s} Price: {price}")
                except:
                    pass
        except:
            pass
    print("Check complete.")

if __name__ == "__main__":
    asyncio.run(check())
