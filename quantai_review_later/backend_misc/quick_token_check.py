"""Quick token check"""
import os
import base64
import json
from datetime import datetime
from dotenv import load_dotenv
import requests

load_dotenv()

token = os.getenv("UPSTOX_ACCESS_TOKEN", "")

# Decode JWT
parts = token.split('.')
payload_b64 = parts[1]
padding = 4 - len(payload_b64) % 4
if padding != 4:
    payload_b64 += '=' * padding
decoded = base64.urlsafe_b64decode(payload_b64)
payload = json.loads(decoded)

exp_time = datetime.fromtimestamp(payload.get('exp'))
current_time = datetime.now()

print("="*60)
print("TOKEN CHECK")
print("="*60)
print(f"Current time: {current_time}")
print(f"Expires at: {exp_time}")

if current_time > exp_time:
    print(f"STATUS: EXPIRED ({current_time - exp_time} ago)")
else:
    print(f"STATUS: VALID ({exp_time - current_time} remaining)")

# Quick API test
print("\n" + "="*60)
print("API TEST")
print("="*60)

headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}

# Test Profile
resp = requests.get("https://api.upstox.com/v2/user/profile", headers=headers, timeout=10)
print(f"User Profile API: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    print(f"  - User: {data.get('data', {}).get('user_name', 'N/A')}")
    print(f"  - Email: {data.get('data', {}).get('email', 'N/A')}")

# Test Market Quote
resp = requests.get("https://api.upstox.com/v2/market-quote/quotes?instrument_key=NSE_EQ%7CINE002A01018", 
                   headers=headers, timeout=10)
print(f"Market Quote API (RELIANCE): {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    quote = list(data.get('data', {}).values())[0] if data.get('data') else {}
    print(f"  - LTP: {quote.get('last_price', 'N/A')}")

print("\n" + "="*60)
