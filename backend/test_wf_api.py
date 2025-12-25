"""Test Walk-Forward Backtest API"""
import requests
import json

payload = {
    "symbols": ["RELIANCE"],
    "exchange": "NSE",
    "strategy_type": "RULE_BASED",
    "strategy_name": "trend_finder",
    "timeframe": "1D",
    "trade_style": "SWING",
    "walk_forward": {
        "train_window": 60,
        "test_window": 10,
        "step_size": 10,
        "anchored": False
    },
    "capital": 100000,
    "ml_model": "NONE"
}

print("Testing Walk-Forward Backtest API...")
print(f"Payload: {json.dumps(payload, indent=2)}")

try:
    r = requests.post(
        "http://localhost:8000/api/v1/backtest/walk-forward", 
        json=payload, 
        timeout=120
    )
    print(f"\nStatus Code: {r.status_code}")
    print(f"Content-Type: {r.headers.get('content-type', 'N/A')}")
    print(f"Response Length: {len(r.text)} chars")
    
    if r.text:
        print(f"\nResponse (first 1000 chars):\n{r.text[:1000]}")
    else:
        print("\nResponse: EMPTY")
        
except requests.exceptions.Timeout:
    print("ERROR: Request timed out after 120 seconds")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
