
import requests
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")
if not TOKEN:
    print("ERROR: UPSTOX_ACCESS_TOKEN not found in environment")
    exit(1)

print(f"Using token: {TOKEN[:20]}...{TOKEN[-10:]}")

headers = {
    "Accept": "application/json",
    "Authorization": f"Bearer {TOKEN}"
}

# Test with NIFTY 50 index
import urllib.parse
instrument_key = "NSE_INDEX|Nifty 50"
encoded_key = urllib.parse.quote(instrument_key, safe='')

url = f"https://api.upstox.com/v2/market-quote/quotes?instrument_key={encoded_key}"
print(f"Requesting: {url}")

try:
    response = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"Error: {e}")
