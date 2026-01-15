"""
Comprehensive E2E Backend API Testing
Tests all major API endpoints across the QuantAI backend.
"""
import requests
import time
import json
from datetime import datetime
from typing import Dict, List, Any, Tuple

BASE_URL = "http://localhost:8000"


def test_endpoint(method: str, url: str, data: dict = None, name: str = None) -> Tuple[bool, dict]:
    """Test a single endpoint."""
    try:
        start = time.time()
        if method.upper() == "GET":
            r = requests.get(f"{BASE_URL}{url}", timeout=30)
        elif method.upper() == "POST":
            r = requests.post(f"{BASE_URL}{url}", json=data, timeout=30)
        else:
            return False, {"error": f"Unknown method: {method}"}
        
        elapsed = (time.time() - start) * 1000
        
        return r.status_code in [200, 201, 422], {
            "name": name or url,
            "status_code": r.status_code,
            "time_ms": round(elapsed, 0),
            "success": r.status_code in [200, 201, 422],
            "response_size": len(r.text),
            "sample": str(r.text)[:200] if r.text else None
        }
    except requests.exceptions.Timeout:
        return False, {"name": name or url, "error": "TIMEOUT", "success": False}
    except requests.exceptions.ConnectionError:
        return False, {"name": name or url, "error": "CONNECTION_ERROR", "success": False}
    except Exception as e:
        return False, {"name": name or url, "error": str(e), "success": False}


def run_e2e_tests():
    """Run comprehensive E2E API tests."""
    print("=" * 80)
    print("QUANTAI BACKEND - E2E API TESTING")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 80)
    print()
    
    # Define all test cases by category
    test_cases = {
        "Health & Status": [
            ("GET", "/docs", "API Documentation"),
            ("GET", "/api/v2/scanner/status", "HP Scanner Status"),
        ],
        
        "Scanner API (v1)": [
            ("GET", "/api/scanner/strategies", "Get Strategies"),
            ("GET", "/api/scanner/momentum", "Momentum Data"),
            ("GET", "/api/scanner/presets", "Get Presets"),
        ],
        
        "Scanner API (v2 - High Performance)": [
            ("GET", "/api/v2/scanner/status", "HP Status"),
            ("GET", "/api/v2/scanner/momentum", "HP Momentum"),
            ("GET", "/api/v2/scanner/breakout", "HP Breakout"),
            ("GET", "/api/v2/scanner/reversal", "HP Reversal"),
            ("GET", "/api/v2/scanner/trendfinder", "HP TrendFinder"),
            ("GET", "/api/v2/scanner/signals", "HP Active Signals"),
        ],
        
        "Trading API": [
            ("GET", "/api/trading/market-indices", "Market Indices"),
            ("GET", "/api/trading/positions", "Positions"),
            ("GET", "/api/trading/orders", "Orders"),
            ("GET", "/api/trading/funds", "Funds"),
        ],
        
        "AI Engines": [
            ("GET", "/api/ai/options/trade-signals", "Options Trade Signals"),
            ("GET", "/api/ai/equity/trade-signals", "Equity Trade Signals"),
            ("GET", "/api/ai/momentum/trade-signals", "Momentum Trade Signals"),
        ],
        
        "Quant Bot": [
            ("GET", "/api/quant-bot/strategies", "Quant Strategies"),
            ("GET", "/api/quant-bot/performance", "Quant Performance"),
        ],
        
        "Risk Management": [
            ("GET", "/api/risk/portfolio-risk", "Portfolio Risk"),
            ("GET", "/api/risk/exposure-limits", "Exposure Limits"),
        ],
        
        "Strategy Lab": [
            ("GET", "/api/strategy-lab/strategies", "Lab Strategies"),
            ("GET", "/api/strategy-lab/templates", "Strategy Templates"),
        ],
    }
    
    results = []
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    for category, tests in test_cases.items():
        print(f"\n### {category}")
        print("-" * 60)
        
        for method, url, name in tests:
            total_tests += 1
            success, result = test_endpoint(method, url, name=name)
            results.append(result)
            
            if success:
                passed_tests += 1
                status_icon = "✅"
                status_text = f"{result['status_code']} ({result['time_ms']}ms)"
            else:
                failed_tests += 1
                status_icon = "❌"
                error = result.get('error', f"HTTP {result.get('status_code', 'N/A')}")
                status_text = f"FAILED: {error}"
            
            print(f"  {status_icon} {name:<35} {status_text}")
    
    # Summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total Tests:  {total_tests}")
    print(f"Passed:       {passed_tests} ({100*passed_tests/total_tests:.0f}%)")
    print(f"Failed:       {failed_tests} ({100*failed_tests/total_tests:.0f}%)")
    print()
    
    # Response time analysis
    response_times = [r['time_ms'] for r in results if 'time_ms' in r]
    if response_times:
        avg_time = sum(response_times) / len(response_times)
        min_time = min(response_times)
        max_time = max(response_times)
        print(f"Response Times:")
        print(f"  Average: {avg_time:.0f}ms")
        print(f"  Min:     {min_time:.0f}ms")
        print(f"  Max:     {max_time:.0f}ms")
    
    print()
    print(f"Completed: {datetime.now().isoformat()}")
    
    # Return summary for programmatic use
    return {
        "total": total_tests,
        "passed": passed_tests,
        "failed": failed_tests,
        "pass_rate": round(100 * passed_tests / total_tests, 1),
        "avg_response_ms": round(avg_time, 0) if response_times else None,
        "results": results
    }


if __name__ == "__main__":
    run_e2e_tests()
