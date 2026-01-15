"""Test v2 scanner performance - multiple requests"""
import requests
import time

print("Testing v2 Scanner Performance")
print("=" * 50)

# Multiple requests to test caching
for i in range(5):
    start = time.time()
    r = requests.get('http://localhost:8000/api/v2/scanner/momentum')
    elapsed = (time.time() - start) * 1000
    
    if r.status_code == 200:
        data = r.json()
        print(f"Request {i+1}: {elapsed:.0f}ms | Stocks: {data.get('count', 0)} | Source: {data.get('status', {}).get('source', 'N/A')}")
    else:
        print(f"Request {i+1}: ERROR {r.status_code}")
    
    time.sleep(0.5)

print()
print("Testing other v2 endpoints:")

# Breakout
start = time.time()
r = requests.get('http://localhost:8000/api/v2/scanner/breakout')
print(f"Breakout: {(time.time()-start)*1000:.0f}ms | Count: {r.json().get('count', 0)}")

# Reversal
start = time.time()
r = requests.get('http://localhost:8000/api/v2/scanner/reversal')
print(f"Reversal: {(time.time()-start)*1000:.0f}ms | Count: {r.json().get('count', 0)}")

# TrendFinder
start = time.time()
r = requests.get('http://localhost:8000/api/v2/scanner/trendfinder')
print(f"TrendFinder: {(time.time()-start)*1000:.0f}ms | Count: {r.json().get('count', 0)}")

# Active Signals
start = time.time()
r = requests.get('http://localhost:8000/api/v2/scanner/signals')
print(f"Signals: {(time.time()-start)*1000:.0f}ms | Count: {r.json().get('count', 0)}")
