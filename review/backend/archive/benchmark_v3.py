"""
Benchmark v3 API Performance
Tests Memcached-backed endpoints for <50ms P95 latency.
"""
import requests
import time

BASE_URL = "http://localhost:8000"

def benchmark(url: str, name: str, iterations: int = 20):
    times = []
    
    for i in range(iterations):
        try:
            start = time.time()
            r = requests.get(f"{BASE_URL}{url}", timeout=30)
            elapsed = (time.time() - start) * 1000
            
            if r.status_code == 200:
                times.append(elapsed)
                data = r.json()
                latency = data.get('latency_ms', 'N/A')
        except Exception as e:
            print(f"  Error: {e}")
        
        time.sleep(0.05)
    
    if times:
        times.sort()
        p50 = times[len(times)//2]
        p95 = times[int(len(times)*0.95)]
        avg = sum(times) / len(times)
        
        status = "✅ PASS" if p95 < 50 else "⚠️ CLOSE" if p95 < 100 else "❌ FAIL"
        print(f"{name:<30} P50: {p50:>6.0f}ms | P95: {p95:>6.0f}ms | Avg: {avg:>6.0f}ms | {status}")
        return p95
    return None


def main():
    print("=" * 80)
    print("MEMCACHED PERFORMANCE BENCHMARK - v3 API")
    print("=" * 80)
    print()
    
    # Wait for server
    time.sleep(5)
    
    # Trigger cache warm
    print("Triggering cache warm-up...")
    try:
        r = requests.post(f"{BASE_URL}/api/v3/scanner/warm", timeout=30)
        print(f"  Warm response: {r.status_code}")
    except:
        print("  Warm-up endpoint not available")
    
    time.sleep(10)  # Wait for warm-up
    
    print()
    print("v3 API Endpoints (Memcached-backed):")
    print("-" * 80)
    
    results = []
    
    # v3 endpoints
    endpoints = [
        ("/api/v3/scanner/momentum", "v3 Momentum"),
        ("/api/v3/scanner/breakout", "v3 Breakout"),
        ("/api/v3/scanner/reversal", "v3 Reversal"),
        ("/api/v3/scanner/signals", "v3 Signals"),
        ("/api/v3/scanner/snapshots", "v3 Snapshots"),
        ("/api/v3/scanner/status", "v3 Status"),
        ("/api/v3/scanner/metrics", "v3 Metrics"),
    ]
    
    for url, name in endpoints:
        p95 = benchmark(url, name)
        if p95:
            results.append((name, p95))
    
    print()
    print("v2 API Endpoints (for comparison):")
    print("-" * 80)
    
    v2_endpoints = [
        ("/api/v2/scanner/momentum", "v2 Momentum"),
        ("/api/v2/scanner/status", "v2 Status"),
    ]
    
    for url, name in v2_endpoints:
        p95 = benchmark(url, name, iterations=10)
        if p95:
            results.append((name, p95))
    
    # Summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    v3_results = [r for r in results if r[0].startswith("v3")]
    v3_p95_avg = sum(r[1] for r in v3_results) / len(v3_results) if v3_results else 0
    
    print(f"v3 Average P95: {v3_p95_avg:.0f}ms")
    print(f"Target: <50ms")
    print(f"Status: {'✅ ACHIEVED' if v3_p95_avg < 50 else '⚠️ NEEDS WORK' if v3_p95_avg < 100 else '❌ NOT MET'}")
    
    # Get metrics
    try:
        r = requests.get(f"{BASE_URL}/api/v3/scanner/metrics")
        if r.status_code == 200:
            metrics = r.json()
            print()
            print("Server-side Metrics:")
            print(f"  Cache Hit Rate: {metrics.get('cache', {}).get('hit_rate', 0)}%")
            print(f"  Latency P50: {metrics.get('latency', {}).get('p50', 'N/A')}ms")
            print(f"  Latency P95: {metrics.get('latency', {}).get('p95', 'N/A')}ms")
    except:
        pass


if __name__ == "__main__":
    main()
