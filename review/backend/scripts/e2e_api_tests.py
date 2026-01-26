"""
QuantAI India Trading Bot - Comprehensive E2E API Testing Script
=====================================================================
Tests all API endpoints across all modules with detailed reporting.
"""

import requests
import json
import time
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List, Dict
from collections import defaultdict

# Configuration
BASE_URL = "http://127.0.0.1:8000"
TIMEOUT = 30  # seconds

# Test Results Collector
@dataclass
class TestResult:
    endpoint: str
    method: str
    description: str
    status: str  # PASSED, FAILED, SKIPPED
    status_code: Optional[int] = None
    expected_code: int = 200
    response_time_ms: float = 0
    response_sample: str = ""
    error: str = ""
    module: str = ""

class TestRunner:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.results: List[TestResult] = []
        self.session = requests.Session()
        self.auth_token = None
        
    def authenticate(self) -> bool:
        """Try to login and get auth token"""
        try:
            # Try login with admin credentials
            response = self.session.post(
                f"{self.base_url}/api/auth/login",
                json={"email": "kumar@gmail.com", "password": "admin123"},
                timeout=TIMEOUT
            )
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})
                return True
        except Exception as e:
            print(f"Auth failed: {e}")
        return False
    
    def test_endpoint(
        self,
        method: str,
        endpoint: str,
        description: str,
        module: str,
        expected_code: int = 200,
        data: Optional[Dict] = None,
        skip_reason: str = "",
        requires_auth: bool = False
    ) -> TestResult:
        """Test a single endpoint"""
        result = TestResult(
            endpoint=endpoint,
            method=method,
            description=description,
            module=module,
            expected_code=expected_code,
            status="SKIPPED"
        )
        
        if skip_reason:
            result.status = "SKIPPED"
            result.error = skip_reason
            self.results.append(result)
            return result
        
        if requires_auth and not self.auth_token:
            result.status = "SKIPPED"
            result.error = "Authentication required but not available"
            self.results.append(result)
            return result
        
        try:
            start_time = time.time()
            
            url = f"{self.base_url}{endpoint}"
            if method == "GET":
                response = self.session.get(url, timeout=TIMEOUT)
            elif method == "POST":
                response = self.session.post(url, json=data or {}, timeout=TIMEOUT)
            elif method == "PUT":
                response = self.session.put(url, json=data or {}, timeout=TIMEOUT)
            elif method == "DELETE":
                response = self.session.delete(url, timeout=TIMEOUT)
            else:
                raise ValueError(f"Unknown method: {method}")
            
            end_time = time.time()
            result.response_time_ms = (end_time - start_time) * 1000
            result.status_code = response.status_code
            
            # Capture response sample
            try:
                resp_json = response.json()
                result.response_sample = json.dumps(resp_json, indent=2)[:500]
            except:
                result.response_sample = response.text[:500]
            
            if response.status_code == expected_code:
                result.status = "PASSED"
            else:
                result.status = "FAILED"
                result.error = result.response_sample[:200]
                
        except requests.exceptions.Timeout:
            result.status = "FAILED"
            result.error = "Request timed out"
        except requests.exceptions.ConnectionError:
            result.status = "FAILED"
            result.error = "Connection refused - is the server running?"
        except Exception as e:
            result.status = "FAILED"
            result.error = str(e)
        
        self.results.append(result)
        return result
    
    def run_all_tests(self):
        """Run all API endpoint tests"""
        print("=" * 80)
        print("QuantAI India - Comprehensive E2E API Testing")
        print("=" * 80)
        print(f"Base URL: {self.base_url}")
        print(f"Started: {datetime.now().isoformat()}")
        print()
        
        # Check server availability
        print("Checking server availability...")
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=30)
            if resp.status_code != 200:
                print("ERROR: Server health check failed!")
                return
        except:
            print("ERROR: Cannot connect to server. Please start the backend first.")
            return
        print("Server is up and running!\n")
        
        # Authenticate
        print("Authenticating...")
        if self.authenticate():
            print(f"Authenticated successfully! Token: {self.auth_token[:20]}...\n")
        else:
            print("Warning: Running tests without authentication\n")
        
        # ============================================
        # Core Endpoints
        # ============================================
        print("Testing Core Endpoints...")
        self.test_endpoint("GET", "/", "Root endpoint", "Core")
        self.test_endpoint("GET", "/health", "Health check", "Core")
        
        # ============================================
        # Authentication Module
        # ============================================
        print("Testing Authentication Module...")
        self.test_endpoint("GET", "/api/auth/me", "Get current user", "Auth", requires_auth=True)
        
        # ============================================
        # Trading Module
        # ============================================
        print("Testing Trading Module...")
        self.test_endpoint("GET", "/api/trading/health", "Trading health check", "Trading")
        self.test_endpoint("GET", "/api/trading/market-indices", "Market indices", "Trading")
        self.test_endpoint("GET", "/api/trading/instruments", "Trading instruments", "Trading")
        self.test_endpoint("GET", "/api/trading/dashboard", "Dashboard stats", "Trading", requires_auth=True)
        self.test_endpoint("GET", "/api/trading/top-gainers", "Top gainers", "Trading", requires_auth=True)
        self.test_endpoint("GET", "/api/trading/gainers-losers", "Gainers and losers", "Trading", requires_auth=True)
        
        # ============================================
        # Upstox Module
        # ============================================
        print("Testing Upstox Module...")
        self.test_endpoint("GET", "/api/upstox/status", "Upstox connection status", "Upstox")
        self.test_endpoint("GET", "/api/upstox/portfolio", "Portfolio data", "Upstox")
        self.test_endpoint("GET", "/api/upstox/user-profile", "User profile", "Upstox")
        
        # ============================================
        # Scanner Module
        # ============================================
        print("Testing Scanner Module...")
        self.test_endpoint("GET", "/api/scanner/strategies", "Scanner strategies", "Scanner")
        self.test_endpoint("GET", "/api/scanner/indices", "Available indices", "Scanner")
        self.test_endpoint("GET", "/api/scanner/timeframes", "Available timeframes", "Scanner")
        self.test_endpoint("GET", "/api/scanner/momentum", "Momentum scanner", "Scanner")
        self.test_endpoint("GET", "/api/scanner/breakout", "Breakout scanner", "Scanner")
        self.test_endpoint("GET", "/api/scanner/reversal", "Reversal scanner", "Scanner")
        self.test_endpoint("GET", "/api/scanner/trendfinder", "TrendFinder AI scanner", "Scanner")
        self.test_endpoint("GET", "/api/scanner/week52-breakouts", "52-week breakouts", "Scanner")
        self.test_endpoint("GET", "/api/scanner/presets", "Scanner presets", "Scanner")
        self.test_endpoint("GET", "/api/scanner/momentum/status", "Momentum status", "Scanner")
        
        # ============================================
        # AI Module
        # ============================================
        print("Testing AI Module...")
        self.test_endpoint("GET", "/api/ai/strategies", "AI strategies list", "AI")
        self.test_endpoint("GET", "/api/ai/trend-finder", "Trend Finder AI", "AI")
        self.test_endpoint("GET", "/api/ai/breakout-detector", "Breakout Detector", "AI")
        self.test_endpoint("GET", "/api/ai/top5-picks", "Top 5 stock picks", "AI")
        self.test_endpoint("GET", "/api/ai/momentum", "Momentum scanner", "AI")
        self.test_endpoint("GET", "/api/ai/mean-reversion", "Mean reversion scanner", "AI")
        self.test_endpoint("GET", "/api/ai/gap-scanner", "Gap scanner", "AI")
        self.test_endpoint("GET", "/api/ai/relative-strength", "Relative strength", "AI")
        self.test_endpoint("GET", "/api/ai/vwap", "VWAP scanner", "AI")
        self.test_endpoint("GET", "/api/ai/sr-bounce", "Support/Resistance bounce", "AI")
        self.test_endpoint("GET", "/api/ai/market-analysis", "Market analysis", "AI")
        self.test_endpoint("GET", "/api/ai/sentiment?symbol=RELIANCE", "AI sentiment analysis", "AI")
        
        # ============================================
        # Quant Bot Module
        # ============================================
        print("Testing Quant Bot Module...")
        self.test_endpoint("GET", "/api/quant/strategies", "Quant strategies", "Quant")
        self.test_endpoint("GET", "/api/quant/symbols", "Available symbols for backtesting", "Quant")
        self.test_endpoint(
            "POST", "/api/quant/backtest/run", "Run backtest", "Quant",
            data={
                "symbol": "RELIANCE",
                "strategy": "ma_crossover",
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
                "initial_capital": 1000000
            }
        )
        
        # ============================================
        # Walk-Forward Backtest Module
        # ============================================
        print("Testing Walk-Forward Backtest Module...")
        self.test_endpoint("GET", "/api/v1/walk-forward/strategies", "WF strategies", "WalkForward")
        self.test_endpoint("GET", "/api/v1/walk-forward/presets", "WF presets", "WalkForward")
        
        # ============================================
        # Experiment Lab Module
        # ============================================
        print("Testing Experiment Lab Module...")
        self.test_endpoint("GET", "/api/v1/experiment-lab/strategies", "Lab strategies", "ExperimentLab")
        self.test_endpoint("GET", "/api/v1/experiment-lab/symbols", "Lab symbols", "ExperimentLab")
        
        # ============================================
        # Backtest Strategies Module
        # ============================================
        print("Testing Backtest Strategies Module...")
        self.test_endpoint("GET", "/api/v1/backtest/strategies/list", "Backtest strategy list", "BacktestStrategies")
        
        # ============================================
        # Market Module
        # ============================================
        print("Testing Market Module...")
        self.test_endpoint("GET", "/api/market/orchestrator/status", "Orchestrator status", "Market")
        self.test_endpoint("GET", "/api/market/health", "Market health", "Market")
        self.test_endpoint("GET", "/api/market/top-movers", "Top movers", "Market")
        self.test_endpoint("GET", "/api/market/heatmap", "Sector heatmap", "Market")
        
        # ============================================
        # Heatmap Module
        # ============================================
        print("Testing Heatmap Module...")
        self.test_endpoint("GET", "/api/heatmap/sectors", "Sector heatmap data", "Heatmap")
        
        # ============================================
        # Engine Performance Module
        # ============================================
        print("Testing Engine Performance Module...")
        self.test_endpoint("GET", "/api/engines/performance", "Engine performance metrics", "Engines")
        
        # ============================================
        # Analytics Module
        # ============================================
        print("Testing Analytics Module...")
        self.test_endpoint("GET", "/api/analytics/overview", "Analytics overview", "Analytics")
        self.test_endpoint("GET", "/api/analytics/momentum/top?n=10", "Top momentum stocks", "Analytics")
        self.test_endpoint("GET", "/api/analytics/archive/list", "List archives", "Analytics")
        self.test_endpoint("GET", "/api/analytics/archive/stats", "Archive stats", "Analytics")
        
        # ============================================
        # Algorithms Module
        # ============================================
        print("Testing Algorithms Module...")
        self.test_endpoint("GET", "/api/algorithms", "List algorithms", "Algorithms")
        
        # ============================================
        # Orders Module
        # ============================================
        print("Testing Orders Module...")
        self.test_endpoint("GET", "/api/orders", "List orders", "Orders")
        
        # ============================================
        # Risk Module
        # ============================================
        print("Testing Risk Module...")
        self.test_endpoint("GET", "/api/risk/", "Risk settings", "Risk")
        
        # ============================================
        # Settings Module
        # ============================================
        print("Testing Settings Module...")
        self.test_endpoint("GET", "/api/settings", "User settings", "Settings")
        
        # ============================================
        # Agentic Bot Module
        # ============================================
        print("Testing Agentic Bot Module...")
        self.test_endpoint(
            "POST", "/api/agentic-bot/process", "Process agentic request", "AgenticBot",
            skip_reason="Requires complex authentication and input"
        )
        
        print("\nAll tests completed!")
        
    def generate_report(self) -> str:
        """Generate detailed test report"""
        report_lines = []
        
        # Calculate statistics
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == "PASSED")
        failed = sum(1 for r in self.results if r.status == "FAILED")
        skipped = sum(1 for r in self.results if r.status == "SKIPPED")
        success_rate = (passed / (total - skipped) * 100) if (total - skipped) > 0 else 0
        
        # Calculate per-module stats
        module_stats = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0, "skipped": 0})
        for r in self.results:
            module_stats[r.module]["total"] += 1
            if r.status == "PASSED":
                module_stats[r.module]["passed"] += 1
            elif r.status == "FAILED":
                module_stats[r.module]["failed"] += 1
            else:
                module_stats[r.module]["skipped"] += 1
        
        # Calculate average response time for passed tests
        passed_times = [r.response_time_ms for r in self.results if r.status == "PASSED"]
        avg_response_time = sum(passed_times) / len(passed_times) if passed_times else 0
        
        # Header
        report_lines.append("")
        report_lines.append("=" * 100)
        report_lines.append("  QUANTAI INDIA - COMPREHENSIVE E2E API TEST REPORT")
        report_lines.append("=" * 100)
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Base URL: {self.base_url}")
        report_lines.append("")
        
        # Overall Statistics
        report_lines.append("┌" + "─" * 50 + "┐")
        report_lines.append("│  OVERALL STATISTICS" + " " * 30 + "│")
        report_lines.append("├" + "─" * 50 + "┤")
        report_lines.append(f"│  Total Tests:        {total:>6}" + " " * 22 + "│")
        report_lines.append(f"│  Passed:             {passed:>6} ✓" + " " * 20 + "│")
        report_lines.append(f"│  Failed:             {failed:>6} ✗" + " " * 20 + "│")
        report_lines.append(f"│  Skipped:            {skipped:>6} ⊘" + " " * 20 + "│")
        report_lines.append(f"│  Success Rate:       {success_rate:>5.1f}%" + " " * 21 + "│")
        report_lines.append(f"│  Avg Response Time:  {avg_response_time:>6.0f}ms" + " " * 18 + "│")
        report_lines.append("└" + "─" * 50 + "┘")
        report_lines.append("")
        
        # Module-wise Statistics
        report_lines.append("=" * 100)
        report_lines.append("  MODULE-WISE BREAKDOWN")
        report_lines.append("=" * 100)
        report_lines.append("")
        report_lines.append(f"{'Module':<20} {'Total':>8} {'Passed':>8} {'Failed':>8} {'Skipped':>8} {'Rate':>10}")
        report_lines.append("-" * 62)
        
        for module, stats in sorted(module_stats.items()):
            rate = (stats["passed"] / (stats["total"] - stats["skipped"]) * 100) if (stats["total"] - stats["skipped"]) > 0 else 0
            status_icon = "✓" if stats["failed"] == 0 else "✗"
            report_lines.append(f"{module:<20} {stats['total']:>8} {stats['passed']:>8} {stats['failed']:>8} {stats['skipped']:>8} {rate:>8.1f}% {status_icon}")
        
        report_lines.append("")
        
        # Detailed Results - Passed
        passed_results = [r for r in self.results if r.status == "PASSED"]
        if passed_results:
            report_lines.append("=" * 100)
            report_lines.append(f"  PASSED TESTS ({len(passed_results)})")
            report_lines.append("=" * 100)
            report_lines.append("")
            
            for r in passed_results:
                report_lines.append(f"[PASSED] {r.method} {r.endpoint}")
                report_lines.append(f"  Module: {r.module}")
                report_lines.append(f"  Description: {r.description}")
                report_lines.append(f"  Status Code: {r.status_code} (Expected: {r.expected_code})")
                report_lines.append(f"  Response Time: {r.response_time_ms:.0f}ms")
                if r.response_sample:
                    report_lines.append(f"  Response Sample: {r.response_sample[:300]}...")
                report_lines.append("")
        
        # Detailed Results - Failed
        failed_results = [r for r in self.results if r.status == "FAILED"]
        if failed_results:
            report_lines.append("=" * 100)
            report_lines.append(f"  FAILED TESTS ({len(failed_results)})")
            report_lines.append("=" * 100)
            report_lines.append("")
            
            for r in failed_results:
                report_lines.append(f"[FAILED] {r.method} {r.endpoint}")
                report_lines.append(f"  Module: {r.module}")
                report_lines.append(f"  Description: {r.description}")
                report_lines.append(f"  Expected Code: {r.expected_code}")
                report_lines.append(f"  Actual Code: {r.status_code}")
                report_lines.append(f"  Error: {r.error}")
                report_lines.append("")
        
        # Detailed Results - Skipped
        skipped_results = [r for r in self.results if r.status == "SKIPPED"]
        if skipped_results:
            report_lines.append("=" * 100)
            report_lines.append(f"  SKIPPED TESTS ({len(skipped_results)})")
            report_lines.append("=" * 100)
            report_lines.append("")
            
            for r in skipped_results:
                report_lines.append(f"[SKIPPED] {r.method} {r.endpoint}")
                report_lines.append(f"  Module: {r.module}")
                report_lines.append(f"  Description: {r.description}")
                report_lines.append(f"  Reason: {r.error}")
                report_lines.append("")
        
        # Performance Analysis
        report_lines.append("=" * 100)
        report_lines.append("  PERFORMANCE ANALYSIS")
        report_lines.append("=" * 100)
        report_lines.append("")
        
        # Slowest endpoints
        slow_tests = sorted([r for r in self.results if r.status == "PASSED"], key=lambda x: x.response_time_ms, reverse=True)[:10]
        if slow_tests:
            report_lines.append("Top 10 Slowest Endpoints:")
            report_lines.append("-" * 60)
            for i, r in enumerate(slow_tests, 1):
                report_lines.append(f"  {i}. {r.endpoint:<45} {r.response_time_ms:>7.0f}ms")
            report_lines.append("")
        
        # Fastest endpoints
        fast_tests = sorted([r for r in self.results if r.status == "PASSED"], key=lambda x: x.response_time_ms)[:10]
        if fast_tests:
            report_lines.append("Top 10 Fastest Endpoints:")
            report_lines.append("-" * 60)
            for i, r in enumerate(fast_tests, 1):
                report_lines.append(f"  {i}. {r.endpoint:<45} {r.response_time_ms:>7.0f}ms")
            report_lines.append("")
        
        # Recommendations
        report_lines.append("=" * 100)
        report_lines.append("  RECOMMENDATIONS")
        report_lines.append("=" * 100)
        report_lines.append("")
        
        if failed_results:
            report_lines.append("⚠️  Issues to Address:")
            for r in failed_results:
                report_lines.append(f"  - Fix {r.endpoint}: {r.error[:100]}")
            report_lines.append("")
        
        slow_endpoints = [r for r in self.results if r.status == "PASSED" and r.response_time_ms > 5000]
        if slow_endpoints:
            report_lines.append("🐢 Performance Improvements Needed:")
            for r in slow_endpoints:
                report_lines.append(f"  - Optimize {r.endpoint}: {r.response_time_ms:.0f}ms (>5s)")
            report_lines.append("")
        
        if success_rate >= 95:
            report_lines.append("✅ Excellent! API is in great shape with {:.1f}% success rate.".format(success_rate))
        elif success_rate >= 80:
            report_lines.append("👍 Good! API is mostly working but needs some attention.")
        else:
            report_lines.append("❌ Critical! Many endpoints are failing. Immediate attention required.")
        
        report_lines.append("")
        report_lines.append("=" * 100)
        report_lines.append("  END OF REPORT")
        report_lines.append("=" * 100)
        
        return "\n".join(report_lines)


def main():
    runner = TestRunner(BASE_URL)
    runner.run_all_tests()
    
    # Generate report
    report = runner.generate_report()
    print(report)
    
    # Save report to file
    report_path = "e2e_test_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    main()
