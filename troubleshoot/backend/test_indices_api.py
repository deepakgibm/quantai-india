
import requests
import json

def test_api():
    url = "http://localhost:8000/api/trading/market-indices"
    print(f"Fetching from {url}...")
    try:
        # We might need auth if it's protected, but let's try without first as trading.py 
        # specific endpoint definition doesn't show explicit Depends(get_current_user) 
        # ACTUALLY looks like it NO Depends on the router level but let's check.
        # Looking at trading.py: @router.get("/market-indices", response_model=List[MarketIndex])
        # It does NOT have Depends(get_current_user).
        
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(json.dumps(data, indent=2))
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_api()
