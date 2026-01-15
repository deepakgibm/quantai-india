
import requests
import json
import sys

BASE_URL = "http://localhost:8000/api/ai"

def test_market_analysis():
    print("\n--- Testing Market Analysis ---")
    try:
        response = requests.get(f"{BASE_URL}/market-analysis")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("Success!")
            print(json.dumps(response.json(), indent=2)[:500] + "...")
            return True
        else:
            print(f"Failed: {response.text}")
            return False
    except Exception as e:
        print(f"Exception: {e}")
        return False

def test_prompt():
    print("\n--- Testing AI Prompt ---")
    payload = {"prompt": "Suggest 3 conservative stocks for long term"}
    try:
        response = requests.post(f"{BASE_URL}/prompt", json=payload)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("Success!")
            data = response.json()
            print(f"Stocks suggested: {len(data.get('suggested_stocks', []))}")
            print(json.dumps(data, indent=2)[:500] + "...")
            return True
        else:
            print(f"Failed: {response.text}")
            return False
    except Exception as e:
        print(f"Exception: {e}")
        return False

if __name__ == "__main__":
    print("Verifying AI Endpoints...")
    s1 = test_market_analysis()
    s2 = test_prompt()
    
    if s1 and s2:
        print("\n✅ All AI Tests Passed")
        sys.exit(0)
    else:
        print("\n❌ Some Tests Failed")
        sys.exit(1)
