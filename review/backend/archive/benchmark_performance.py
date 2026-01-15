"""
Performance Benchmark - Before vs After Comparison
Measures response times for v1 and v2 scanner endpoints.
"""
import requests
import time
import statistics

def benchmark_endpoint(url: str, name: str, iterations: int = 10) -> dict:
    """Benchmark an endpoint over multiple iterations."""
    times = []
    errors = 0
    
    for i in range(iterations):
        try:
            start = time.time()
            r = requests.get(url, timeout=60)
            elapsed = (time.time() - start) * 1000
            
            if r.status_code == 200:
                times.append(elapsed)
            else:
                errors += 1
        except Exception as e:
            errors += 1
        
        time.sleep(0.1)
    
    if times:
        return {
            "name": name,
            "iterations": iterations,
            "errors": errors,
            "min_ms": round(min(times), 0),
            "max_ms": round(max(times), 0),
            "avg_ms": round(statistics.mean(times), 0),
            "p50_ms": round(sorted(times)[len(times)//2], 0),
            "p95_ms": round(sorted(times)[int(len(times)*0.95)], 0) if len(times) > 1 else round(times[0], 0)
        }
    else:
        return {"name": name, "errors": errors}


def main():
    print("=" * 70)
    print("HIGH-PERFORMANCE SCANNER REFACTOR - PERFORMANCE BENCHMARK")
    print("=" * 70)
    print()
    
    # Wait for server to be ready
    print("Waiting for server...")
    time.sleep(3)
    
    base_url = "http://localhost:8000"
    
    # Endpoints to benchmark
    endpoints = [
        # v1 endpoints (existing)
        (f"{base_url}/api/scanner/momentum", "v1 Momentum (rewired)"),
        (f"{base_url}/api/scanner/strategies", "v1 Strategies"),
        
        # v2 endpoints (new HP scanner)
        (f"{base_url}/api/v2/scanner/momentum", "v2 Momentum (HP)"),
        (f"{base_url}/api/v2/scanner/breakout", "v2 Breakout (HP)"),
        (f"{base_url}/api/v2/scanner/reversal", "v2 Reversal (HP)"),
        (f"{base_url}/api/v2/scanner/signals", "v2 Active Signals (HP)"),
        (f"{base_url}/api/v2/scanner/status", "v2 Status"),
    ]
    
    results = []
    
    for url, name in endpoints:
        print(f"Benchmarking: {name}...")
        result = benchmark_endpoint(url, name, iterations=5)
        results.append(result)
        
        if "avg_ms" in result:
            status = "✅ FAST" if result["avg_ms"] < 100 else "⚠️ SLOW" if result["avg_ms"] < 1000 else "❌ BLOCKED"
            print(f"  → Avg: {result['avg_ms']}ms | Min: {result['min_ms']}ms | Max: {result['max_ms']}ms | {status}")
        else:
            print(f"  → FAILED ({result['errors']} errors)")
        print()
    
    # Summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()
    print(f"{'Endpoint':<30} {'Avg (ms)':<12} {'Min (ms)':<12} {'Max (ms)':<12} {'Status'}")
    print("-" * 70)
    
    for r in results:
        if "avg_ms" in r:
            status = "✅ PASSED" if r["avg_ms"] < 100 else "⚠️ NEEDS WORK" if r["avg_ms"] < 1000 else "❌ FAILED"
            print(f"{r['name']:<30} {r['avg_ms']:<12} {r['min_ms']:<12} {r['max_ms']:<12} {status}")
        else:
            print(f"{r['name']:<30} {'ERROR':<12}")
    
    print()
    print("Target: <50ms for all HP (v2) endpoints")
    print()


if __name__ == "__main__":
    main()
