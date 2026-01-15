"""
Direct Cache Read Test
Tests v3 API without triggering any warm-up.
The standalone worker should have already populated the cache.
"""
import requests
import time


def test():
    # Direct cache reads - no warm-up
    print("Direct Cache Read Test (v3 API)")
    print("=" * 60)
    
    base_url = "http://localhost:8000"
    
    endpoints = [
        "/api/v3/scanner/momentum",
        "/api/v3/scanner/breakout",
        "/api/v3/scanner/reversal",
        "/api/v3/scanner/signals",
        "/api/v3/scanner/status",
    ]
    
    for _ in range(3):  # 3 rounds
        for url in endpoints:
            try:
                start = time.time()
                r = requests.get(f"{base_url}{url}", timeout=5)
                elapsed = (time.time() - start) * 1000
                
                if r.status_code == 200:
                    data = r.json()
                    internal = data.get('latency_ms', 'N/A')
                    count = data.get('count', len(data.get('data', [])))
                    source = data.get('source', 'N/A')
                    
                    status = "✅" if elapsed < 50 else "⚠️" if elapsed < 100 else "❌"
                    print(f"{status} {url.split('/')[-1]:<15} {elapsed:>6.0f}ms (internal: {internal}ms) | count: {count}")
                else:
                    print(f"❌ {url.split('/')[-1]:<15} HTTP {r.status_code}")
            except Exception as e:
                print(f"❌ {url.split('/')[-1]:<15} Error: {e}")
        
        print("-" * 60)
        time.sleep(0.5)


if __name__ == "__main__":
    test()
