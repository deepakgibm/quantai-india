import requests
import os
import json
from config import settings

def get_real_time_price(symbol: str, access_token: str = None) -> float:
    """Fetch real-time price from Upstox API"""
    if not access_token:
        access_token = settings.UPSTOX_ACCESS_TOKEN
    
    print(f"Using Token: {access_token[:10]}...")
    
    if not access_token:
        print("No access token provided.")
        return None
    
    # Comprehensive Nifty 200 symbol to instrument key mapping
    symbol_mapping = {
        "RELIANCE": "NSE_EQ|INE002A01018",
        "TCS": "NSE_EQ|INE467B01029",
        "HDFCBANK": "NSE_EQ|INE040A01034",
        "ICICIBANK": "NSE_EQ|INE090A01021",
        "BAJFINANCE": "NSE_EQ|INE296A01024",
    }
    
    instrument_key = symbol_mapping.get(symbol, f"NSE_EQ|{symbol}")
    print(f"Fetching price for {symbol} using key: {instrument_key}")
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    
    try:
        url = f"https://api.upstox.com/v2/market-quote/ltp?symbol={instrument_key}"
        print(f"Request URL: {url}")
        response = requests.get(url, headers=headers, timeout=5)
        
        print(f"Response Status: {response.status_code}")
        try:
            print(f"Response Body: {json.dumps(response.json(), indent=2)}")
        except:
            print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success" and data.get("data"):
                # Upstox might return a different key than requested (e.g. NSE_EQ:RELIANCE vs NSE_EQ|INE...)
                # Since we request one symbol, we can just take the first item.
                first_value = next(iter(data['data'].values()))
                print(f"Using Data: {first_value}")
                return first_value.get("last_price")
            else:
                print(f"API Error: {data.get('errors')}")
        return None

    except Exception as e:
        print(f"Error fetching price for {symbol}: {str(e)}")
        return None

if __name__ == "__main__":
    key = "NSE_EQ|INE296A01024"
    print(f"\nTesting OHLC for: {key}")
    access_token = settings.UPSTOX_ACCESS_TOKEN
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    # OHLC API
    url = f"https://api.upstox.com/v2/market-quote/ohlc?symbol={key}&interval=1d"
    try:
        resp = requests.get(url, headers=headers)
        print(f"Status: {resp.status_code}")
        print(f"Body: {json.dumps(resp.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")
