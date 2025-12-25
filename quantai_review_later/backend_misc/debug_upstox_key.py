"""
Debug script to test Upstox instrument key formats
"""
import sys
from pathlib import Path
import asyncio
import requests
from datetime import datetime, timedelta

# Add project root to sys.path
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from backend.config import settings

def test_key_format(symbol, key, interval="1minute"):
    print(f"\nTesting {symbol} with key: {key} (Interval: {interval})")
    
    to_date = datetime.now().strftime('%Y-%m-%d')
    from_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
    
    base_url = "https://api.upstox.com/v2"
    endpoint = f"/historical-candle/{key}/{interval}/{to_date}/{from_date}"
    url = f"{base_url}{endpoint}"
    
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {settings.UPSTOX_ACCESS_TOKEN}"
    }
    
    print(f"Request URL: {url}")
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success" and data.get("data", {}).get("candles"):
                print("✅ SUCCESS!")
                return True
    except Exception as e:
        print(f"Error: {e}")
    
    return False

def main():
    # Test AUBANK
    symbol = "AUBANK"
    raw_key = "NSE_EQ|INE949L01017"
    
    print(f"--- Testing {symbol} ---")
    
    print("\n1. Raw Key, 1minute")
    test_key_format(symbol, raw_key, "1minute")

if __name__ == "__main__":
    main()
