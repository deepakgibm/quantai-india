"""
QuantAI Backend API Test Runner
Runs comprehensive API tests and generates a summary report.
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple

BASE_URL = "http://localhost:8000"
TIMEOUT = 30  # 30 second timeout

# API Endpoints to test (based on Postman collection)
API_ENDPOINTS = [
    # Health & Status
    ("Health & Status", "Root", "GET", "/"),
    ("Health & Status", "Health Check", "GET", "/health"),
    ("Health & Status", "Readiness Check", "GET", "/ready"),
    
    # Trading
    ("Trading", "Trading Health", "GET", "/api/trading/health"),
    ("Trading", "Market Indices", "GET", "/api/trading/market-indices"),
    ("Trading", "Instruments", "GET", "/api/trading/instruments"),
    
    # AI Strategies
    ("AI Strategies", "Get AI Strategies", "GET", "/api/ai/strategies"),
    ("AI Strategies", "Market Analysis", "GET", "/api/ai/market-analysis"),
    ("AI Strategies", "Trend Finder", "GET", "/api/ai/trend-finder"),
    ("AI Strategies", "Breakout Stocks", "GET", "/api/ai/breakout-stocks"),
    ("AI Strategies", "Top 5 Picks", "GET", "/api/ai/top5-picks"),
    ("AI Strategies", "Momentum Scanner", "GET", "/api/ai/momentum-scanner"),
    ("AI Strategies", "Mean Reversion", "GET", "/api/ai/mean-reversion"),
    ("AI Strategies", "Gap Scanner", "GET", "/api/ai/gap-scanner"),
    ("AI Strategies", "Relative Strength", "GET", "/api/ai/relative-strength"),
    ("AI Strategies", "VWAP Scanner", "GET", "/api/ai/vwap-scanner"),
    ("AI Strategies", "S/R Bounce", "GET", "/api/ai/sr-bounce"),
    
    # Scanner
    ("Scanner", "Get Strategies", "GET", "/api/scanner/strategies"),
    ("Scanner", "Get Indices", "GET", "/api/scanner/indices"),
    ("Scanner", "Get Timeframes", "GET", "/api/scanner/timeframes"),
    ("Scanner", "Presets", "GET", "/api/scanner/presets"),
    ("Scanner", "Momentum Data", "GET", "/api/scanner/momentum"),
    ("Scanner", "Breakout Data", "GET", "/api/scanner/breakout"),
    ("Scanner", "Reversal Data", "GET", "/api/scanner/reversal"),
    ("Scanner", "TrendFinder Data", "GET", "/api/scanner/trendfinder"),
    ("Scanner", "52-Week Breakouts", "GET", "/api/scanner/52week-breakouts"),
    ("Scanner", "Momentum Status", "GET", "/api/scanner/momentum-status"),
    
    # HP Scanner v3
    ("HP Scanner v3", "Momentum", "GET", "/api/v3/scanner/momentum"),
    ("HP Scanner v3", "Breakout", "GET", "/api/v3/scanner/breakout"),
    ("HP Scanner v3", "Reversal", "GET", "/api/v3/scanner/reversal"),
    ("HP Scanner v3", "Signals", "GET", "/api/v3/scanner/signals"),
    ("HP Scanner v3", "Snapshots", "GET", "/api/v3/scanner/snapshots"),
    ("HP Scanner v3", "Status", "GET", "/api/v3/scanner/status"),
    ("HP Scanner v3", "Metrics", "GET", "/api/v3/scanner/metrics"),
    
    # Market
    ("Market", "NIFTY 100 Top Movers", "GET", "/api/market/nifty100/top-movers"),
    ("Market", "NIFTY 100 Status", "GET", "/api/market/nifty100/status"),
    ("Market", "Top Movers (Alias)", "GET", "/api/market/top-movers"),
    ("Market", "Orchestrator Status", "GET", "/api/market/orchestrator/status"),
    ("Market", "Market Health", "GET", "/api/market/health"),
    ("Market", "Sector Heatmap", "GET", "/api/market/sector-heatmap"),
    
    # Heatmap
    ("Heatmap", "Get Sectors", "GET", "/api/heatmap/sectors"),
    
    # Upstox
    ("Upstox", "Status", "GET", "/api/upstox/status"),
    ("Upstox", "User Profile", "GET", "/api/upstox/user-profile"),
    ("Upstox", "Portfolio", "GET", "/api/upstox/portfolio"),
    
    # Orders
    ("Orders", "Get Orders", "GET", "/api/orders/"),
    
    # Algorithms
    ("Algorithms", "Get Algorithms", "GET", "/api/algorithms/"),
    
    # Risk Management
    ("Risk Management", "Get Risk Settings", "GET", "/api/risk/"),
    
    # Settings
    ("Settings", "Get Settings", "GET", "/api/settings/"),
    
    # User Config
    ("User Config", "Get User Config", "GET", "/api/user-config/"),
    
    # Engines
    ("Engines", "Analytics Engine Status", "GET", "/api/engines/analytics/status"),
    ("Engines", "Paper Trading Status", "GET", "/api/engines/paper-trading/status"),
    
    # Strategy Lab
    ("Strategy Lab", "Get Strategies", "GET", "/api/strategy-lab/strategies"),
    ("Strategy Lab", "Strategy Status", "GET", "/api/strategy-lab/status"),
    
    # Quant
    ("Quant", "Backtest Status", "GET", "/api/quant/backtest/status"),
    ("Quant", "ML Models", "GET", "/api/quant/ml/models"),
    
    # Portfolio
    ("Portfolio", "Get Portfolio", "GET", "/api/portfolio/"),
]


def test_endpoint(category: str, name: str, method: str, path: str) -> Dict:
    """Test a single API endpoint and return results."""
    url = f"{BASE_URL}{path}"
    start_time = time.time()
    result = {
        "category": category,
        "name": name,
        "method": method,
        "path": path,
        "url": url,
        "status": "UNKNOWN",
        "status_code": None,
        "response_time_ms": None,
        "error": None,
        "response_preview": None
    }
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=TIMEOUT)
        elif method == "POST":
            response = requests.post(url, json={}, timeout=TIMEOUT)
        else:
            response = requests.request(method, url, timeout=TIMEOUT)
        
        elapsed = (time.time() - start_time) * 1000
        result["status_code"] = response.status_code
        result["response_time_ms"] = round(elapsed, 2)
        
        if response.status_code < 400:
            result["status"] = "PASS"
        elif response.status_code == 401:
            result["status"] = "AUTH_REQUIRED"
        elif response.status_code == 404:
            result["status"] = "NOT_FOUND"
        elif response.status_code == 422:
            result["status"] = "VALIDATION_ERROR"
        else:
            result["status"] = "FAIL"
        
        # Get response preview (first 200 chars)
        try:
            resp_text = response.text[:200]
            result["response_preview"] = resp_text
        except:
            pass
            
    except requests.exceptions.Timeout:
        result["status"] = "TIMEOUT"
        result["error"] = "Request timed out"
        result["response_time_ms"] = TIMEOUT * 1000
    except requests.exceptions.ConnectionError as e:
        result["status"] = "CONNECTION_ERROR"
        result["error"] = str(e)[:100]
    except Exception as e:
        result["status"] = "ERROR"
        result["error"] = str(e)[:100]
    
    return result


def run_all_tests() -> Tuple[List[Dict], Dict]:
    """Run all API tests and return results with summary."""
    print(f"\n{'='*60}")
    print(f"QuantAI Backend API Test Suite")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE_URL}")
    print(f"{'='*60}\n")
    
    results = []
    summary = {
        "total": 0,
        "pass": 0,
        "fail": 0,
        "timeout": 0,
        "connection_error": 0,
        "auth_required": 0,
        "not_found": 0,
        "validation_error": 0,
        "error": 0,
        "categories": {}
    }
    
    current_category = None
    
    for endpoint in API_ENDPOINTS:
        category, name, method, path = endpoint
        
        if category != current_category:
            current_category = category
            print(f"\n[{category}]")
        
        result = test_endpoint(category, name, method, path)
        results.append(result)
        
        # Update summary
        summary["total"] += 1
        status_lower = result["status"].lower().replace(" ", "_")
        if status_lower == "pass":
            summary["pass"] += 1
            status_icon = "✓"
        elif status_lower == "timeout":
            summary["timeout"] += 1
            status_icon = "⧖"
        elif status_lower == "connection_error":
            summary["connection_error"] += 1
            status_icon = "✗"
        elif status_lower == "auth_required":
            summary["auth_required"] += 1
            status_icon = "🔒"
        elif status_lower == "not_found":
            summary["not_found"] += 1
            status_icon = "?"
        elif status_lower == "validation_error":
            summary["validation_error"] += 1
            status_icon = "!"
        else:
            summary["fail"] += 1
            status_icon = "✗"
        
        # Category summary
        if category not in summary["categories"]:
            summary["categories"][category] = {"pass": 0, "fail": 0, "total": 0}
        summary["categories"][category]["total"] += 1
        if result["status"] == "PASS":
            summary["categories"][category]["pass"] += 1
        else:
            summary["categories"][category]["fail"] += 1
        
        # Print result
        time_str = f"{result['response_time_ms']}ms" if result['response_time_ms'] else "N/A"
        code_str = str(result['status_code']) if result['status_code'] else "N/A"
        print(f"  {status_icon} {name}: {result['status']} ({code_str}) - {time_str}")
        
        # Small delay between requests
        time.sleep(0.1)
    
    return results, summary


def generate_report(results: List[Dict], summary: Dict) -> str:
    """Generate a markdown report of the test results."""
    report = []
    
    report.append("# QuantAI Backend API Test Summary")
    report.append(f"\n**Test Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"**Base URL:** {BASE_URL}")
    report.append("")
    
    # Overall Summary
    report.append("## 📊 Overall Summary")
    report.append("")
    report.append("| Metric | Count |")
    report.append("|--------|-------|")
    report.append(f"| Total Tests | {summary['total']} |")
    report.append(f"| ✅ Passed | {summary['pass']} |")
    report.append(f"| ❌ Failed | {summary['fail']} |")
    report.append(f"| ⏱️ Timeout | {summary['timeout']} |")
    report.append(f"| 🔌 Connection Error | {summary['connection_error']} |")
    report.append(f"| 🔒 Auth Required | {summary['auth_required']} |")
    report.append(f"| ❓ Not Found | {summary['not_found']} |")
    report.append(f"| ⚠️ Validation Error | {summary['validation_error']} |")
    report.append("")
    
    pass_rate = (summary['pass'] / summary['total'] * 100) if summary['total'] > 0 else 0
    report.append(f"**Pass Rate:** {pass_rate:.1f}%")
    report.append("")
    
    # Category Summary
    report.append("## 📁 Results by Category")
    report.append("")
    report.append("| Category | Passed | Failed | Total | Pass Rate |")
    report.append("|----------|--------|--------|-------|-----------|")
    for cat, stats in summary["categories"].items():
        rate = (stats['pass'] / stats['total'] * 100) if stats['total'] > 0 else 0
        report.append(f"| {cat} | {stats['pass']} | {stats['fail']} | {stats['total']} | {rate:.0f}% |")
    report.append("")
    
    # Detailed Results
    report.append("## 📋 Detailed Results")
    report.append("")
    
    current_category = None
    for result in results:
        if result["category"] != current_category:
            current_category = result["category"]
            report.append(f"\n### {current_category}")
            report.append("")
            report.append("| Endpoint | Method | Status | Code | Time |")
            report.append("|----------|--------|--------|------|------|")
        
        status_emoji = {
            "PASS": "✅",
            "FAIL": "❌",
            "TIMEOUT": "⏱️",
            "CONNECTION_ERROR": "🔌",
            "AUTH_REQUIRED": "🔒",
            "NOT_FOUND": "❓",
            "VALIDATION_ERROR": "⚠️",
            "ERROR": "💥"
        }.get(result["status"], "❓")
        
        time_str = f"{result['response_time_ms']}ms" if result['response_time_ms'] else "N/A"
        code_str = str(result['status_code']) if result['status_code'] else "N/A"
        
        report.append(f"| {result['name']} | {result['method']} | {status_emoji} {result['status']} | {code_str} | {time_str} |")
    
    report.append("")
    
    # Failed Tests Details
    failed = [r for r in results if r["status"] not in ["PASS", "AUTH_REQUIRED"]]
    if failed:
        report.append("## ⚠️ Failed/Error Endpoints")
        report.append("")
        for result in failed:
            report.append(f"- **{result['name']}** (`{result['path']}`)")
            report.append(f"  - Status: {result['status']}")
            if result.get('error'):
                report.append(f"  - Error: {result['error']}")
        report.append("")
    
    # Recommendations
    report.append("## 💡 Recommendations")
    report.append("")
    
    if summary['connection_error'] > 0 or summary['timeout'] > 0:
        report.append("- ⚠️ **Connection Issues Detected**: Multiple timeouts or connection errors suggest the backend may be overloaded or not fully started.")
    
    if summary['auth_required'] > 0:
        report.append("- 🔐 **Authentication Required**: Some endpoints require authentication. Consider testing with a valid JWT token.")
    
    if summary['not_found'] > 0:
        report.append("- 🔍 **Not Found**: Some endpoints returned 404. Verify the API routes are correctly registered.")
    
    if pass_rate >= 80:
        report.append("- ✅ **Good Health**: The API is responding well to most requests.")
    elif pass_rate >= 50:
        report.append("- ⚡ **Moderate Health**: Some endpoints are working but issues exist.")
    else:
        report.append("- 🚨 **Critical Issues**: Many endpoints are failing. Investigate backend logs.")
    
    return "\n".join(report)


if __name__ == "__main__":
    try:
        results, summary = run_all_tests()
        
        # Generate report
        report = generate_report(results, summary)
        
        # Save report
        report_path = "api_test_summary.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        
        # Save JSON results
        json_path = "api_test_results.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({
                "results": results,
                "summary": summary,
                "timestamp": datetime.now().isoformat()
            }, f, indent=2)
        
        print(f"\n{'='*60}")
        print(f"Test Summary")
        print(f"{'='*60}")
        print(f"Total: {summary['total']}")
        print(f"Passed: {summary['pass']}")
        print(f"Failed: {summary['fail']}")
        print(f"Timeout: {summary['timeout']}")
        print(f"Connection Error: {summary['connection_error']}")
        print(f"Auth Required: {summary['auth_required']}")
        print(f"{'='*60}")
        print(f"\nReports saved to:")
        print(f"  - {report_path}")
        print(f"  - {json_path}")
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
    except Exception as e:
        print(f"\n\nError running tests: {e}")
