import requests
import json

try:
    print("Testing 52-Week Breakout API...")
    resp = requests.get('http://localhost:8000/api/scanner/week52-breakouts', timeout=60)
    print(f"Status Code: {resp.status_code}\n")
    
    data = resp.json()
    print(f"Status: {data.get('status')}")
    print(f"Total High Breakouts: {len(data.get('high_breakouts', []))}")
    print(f"Total Low Breakdowns: {len(data.get('low_breakdowns', []))}")
    print(f"Summary: {json.dumps(data.get('summary', {}), indent=2)}")
    
    if data.get('high_breakouts'):
        print("\n" + "="*50)
        print("52-WEEK HIGH BREAKOUTS (New Yearly Highs)")
        print("="*50)
        for i, stock in enumerate(data['high_breakouts'], 1):
            print(f"{i}. {stock['symbol']}")
            print(f"   LTP: ₹{stock['ltp']:,.2f} | 52W High: ₹{stock['high_52w']:,.2f}")
            print(f"   Breakout: +{stock['breakout_pct']:.2f}% | Volume Ratio: {stock['volume_ratio']}x")
            print()
    
    if data.get('low_breakdowns'):
        print("\n" + "="*50)
        print("52-WEEK LOW BREAKDOWNS (New Yearly Lows)")  
        print("="*50)
        for i, stock in enumerate(data['low_breakdowns'], 1):
            print(f"{i}. {stock['symbol']}")
            print(f"   LTP: ₹{stock['ltp']:,.2f} | 52W Low: ₹{stock['low_52w']:,.2f}")
            print(f"   Breakdown: -{stock['breakout_pct']:.2f}% | Volume Ratio: {stock['volume_ratio']}x")
            print()

    print("\n✅ API Test PASSED!")
    
except Exception as e:
    print(f"❌ Error: {e}")
