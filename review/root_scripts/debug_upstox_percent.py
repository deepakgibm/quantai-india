
import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")
print(f"Token: {TOKEN[:30]}...")

headers = {
    "Accept": "application/json",
    "Authorization": f"Bearer {TOKEN}"
}

import urllib.parse
instrument_key = "NSE_INDEX|Nifty 50"
encoded_key = urllib.parse.quote(instrument_key, safe='')

url = f"https://api.upstox.com/v2/market-quote/quotes?instrument_key={encoded_key}"
print(f"URL: {url}")

try:
    response = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {response.status_code}")
    data = response.json()
    
    # Extract the quote data
    if data.get("status") == "success" and data.get("data"):
        quote = next(iter(data["data"].values()))
        print("\n=== Key Fields for Percent Calculation ===")
        print(f"last_price: {quote.get('last_price')}")
        print(f"previous_close: {quote.get('previous_close')}")  # OHLC prev close
        print(f"net_change: {quote.get('net_change')}")
        print(f"percentage_change: {quote.get('percentage_change')}")
        
        # Check if ohlc exists
        ohlc = quote.get("ohlc", {})
        print(f"\n=== OHLC Data ===")
        print(f"open: {ohlc.get('open')}")
        print(f"high: {ohlc.get('high')}")
        print(f"low: {ohlc.get('low')}")
        print(f"close: {ohlc.get('close')}")
        
        print("\n=== Full Quote ===")
        print(json.dumps(quote, indent=2, default=str))
except Exception as e:
    print(f"Error: {e}")
