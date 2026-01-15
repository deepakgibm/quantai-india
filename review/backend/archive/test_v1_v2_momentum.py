"""Test v1 momentum endpoint with HP scanner source"""
import requests
import time

print("Testing v1 Momentum Endpoint (with HP Scanner integration)")
print("=" * 60)

# Wait for server to fully start
time.sleep(5)

# Multiple requests to test caching
for i in range(5):
    start = time.time()
    r = requests.get('http://localhost:8000/api/scanner/momentum')
    elapsed = (time.time() - start) * 1000
    
    if r.status_code == 200:
        data = r.json()
        source = data.get('status', {}).get('source', 'UNKNOWN')
        count = data.get('status', {}).get('stock_count', 0) or len(data.get('data', []))
        print(f"Request {i+1}: {elapsed:.0f}ms | Source: {source} | Stocks: {count}")
    else:
        print(f"Request {i+1}: ERROR {r.status_code}")
    
    time.sleep(0.5)

# Test v2 endpoint for comparison
print()
print("Testing v2 Momentum Endpoint (direct HP scanner)")
print("=" * 60)

for i in range(3):
    start = time.time()
    r = requests.get('http://localhost:8000/api/v2/scanner/momentum')
    elapsed = (time.time() - start) * 1000
    
    if r.status_code == 200:
        data = r.json()
        source = data.get('status', {}).get('source', 'UNKNOWN')
        count = data.get('count', 0)
        print(f"Request {i+1}: {elapsed:.0f}ms | Source: {source} | Stocks: {count}")
    else:
        print(f"Request {i+1}: ERROR {r.status_code}")
    
    time.sleep(0.5)
