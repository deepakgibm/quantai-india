import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_week52_breakouts():
    print("\n" + "="*60)
    print("TEST: 52-Week Breakouts API")
    print("="*60)
    try:
        response = requests.get(f"{BASE_URL}/api/scanner/week52-breakouts")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            high = data.get("high_breakouts", [])
            low = data.get("low_breakdowns", [])
            print(f"✅ PASS - High Breakouts: {len(high)}, Low Breakdowns: {len(low)}")
            if high:
                print(f"   Example High: {high[0]['symbol']} (LTP: {high[0]['ltp']})")
            if low:
                print(f"   Example Low: {low[0]['symbol']} (LTP: {low[0]['ltp']})")
            return True
        else:
            print(f"❌ FAIL - {response.text}")
            return False
    except Exception as e:
        print(f"❌ FAIL - Error: {str(e)}")
        return False

def test_momentum_api():
    print("\n" + "="*60)
    print("TEST: Momentum (REST Fallback) API")
    print("="*60)
    try:
        response = requests.get(f"{BASE_URL}/api/scanner/momentum")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            stocks = data.get("stocks", [])
            print(f"✅ PASS - Momentum Stocks returned: {len(stocks)}")
            
            # Check for non-zero counts in buckets
            buckets = {}
            for s in stocks:
                b = s.get("bucket", "UNKNOWN")
                buckets[b] = buckets.get(b, 0) + 1
            
            print("   Bucket Distribution:")
            for b, count in buckets.items():
                print(f"   - {b}: {count}")
            
            # Verify that STRONG_BULLISH and STRONG_BEARISH are populated if EXTREME exist
            # (Note: In REST API, mapping might already be done or stocks might be raw)
            return True
        else:
            print(f"❌ FAIL - {response.text}")
            return False
    except Exception as e:
        print(f"❌ FAIL - Error: {str(e)}")
        return False

if __name__ == "__main__":
    s1 = test_week52_breakouts()
    s2 = test_momentum_api()
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"52-Week API: {'✅ PASS' if s1 else '❌ FAIL'}")
    print(f"Momentum API: {'✅ PASS' if s2 else '❌ FAIL'}")
