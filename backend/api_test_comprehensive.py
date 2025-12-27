"""
Comprehensive API Testing Script for QuantAI Backend
Tests all major API endpoints and generates a detailed test summary
"""
import requests
import json
from datetime import datetime
from typing import Dict, List, Any

BASE_URL = "http://localhost:8000"

class APITester:
    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
        self.skipped = 0
    
    def test_endpoint(self, method: str, endpoint: str, description: str, 
                     expected_status: int = 200, data: Dict = None, 
                     headers: Dict = None, skip_reason: str = None):
        """Test a single endpoint and record results"""
        
        if skip_reason:
            self.results.append({
                "endpoint": endpoint,
                "method": method,
                "description": description,
                "status": "SKIPPED",
                "reason": skip_reason
            })
            self.skipped += 1
            return
        
        try:
            url = f"{BASE_URL}{endpoint}"
            
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method.upper() == "PUT":
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            success = response.status_code == expected_status
            
            result = {
                "endpoint": endpoint,
                "method": method,
                "description": description,
                "status": "PASSED" if success else "FAILED",
                "expected_code": expected_status,
                "actual_code": response.status_code,
                "response_time_ms": int(response.elapsed.total_seconds() * 1000)
            }
            
            # Try to capture response body (limit size)
            try:
                response_body = response.json()
                # Limit response data for readability
                if isinstance(response_body, dict):
                    result["response_sample"] = {k: v for k, v in list(response_body.items())[:5]}
                elif isinstance(response_body, list):
                    result["response_sample"] = response_body[:3]
                else:
                    result["response_sample"] = response_body
            except:
                result["response_text"] = response.text[:200]
            
            if success:
                self.passed += 1
            else:
                self.failed += 1
                result["error"] = response.text[:500]
            
            self.results.append(result)
            
        except Exception as e:
            self.results.append({
                "endpoint": endpoint,
                "method": method,
                "description": description,
                "status": "ERROR",
                "error": str(e)
            })
            self.failed += 1
    
    def run_all_tests(self):
        """Run all API endpoint tests"""
        
        print("Starting comprehensive API tests...\n")
        
        # ========== Basic Health Checks ==========
        print("Testing: Basic Health Checks")
        self.test_endpoint("GET", "/", "Root endpoint")
        self.test_endpoint("GET", "/health", "Health check endpoint")
        
        # ========== Trading Endpoints ==========
        print("Testing: Trading Endpoints")
        self.test_endpoint("GET", "/api/trading/market-indices", "Market indices data")
        self.test_endpoint("GET", "/api/trading/portfolio", "Portfolio data", 
                          skip_reason="Requires authentication")
        self.test_endpoint("GET", "/api/trading/instruments", "Get instruments list")
        
        # ========== Upstox Integration ==========
        print("Testing: Upstox Integration")
        self.test_endpoint("GET", "/api/upstox/status", "Upstox connection status")
        self.test_endpoint("GET", "/api/upstox/user-profile", "User profile",
                          skip_reason="Requires Upstox authentication")
        
        # ========== Scanner Endpoints ==========
        print("Testing: Scanner Endpoints")
        self.test_endpoint("GET", "/api/scanner/momentum", "Momentum scanner")
        self.test_endpoint("GET", "/api/scanner/breakout", "Breakout scanner")
        self.test_endpoint("GET", "/api/scanner/reversal", "Reversal scanner")
        self.test_endpoint("GET", "/api/scanner/trendfinder", "TrendFinder AI scanner")
        
        # ========== Market Data ==========
        print("Testing: Market Data")
        self.test_endpoint("GET", "/api/market/orchestrator/status", "Market data orchestrator status")
        self.test_endpoint("GET", "/api/market/health", "Market service health")
        
        # ========== Quant/Backtest Endpoints ==========
        print("Testing: Quant/Backtest Endpoints")
        self.test_endpoint("GET", "/api/quant/symbols", "Get available symbols for backtesting")
        self.test_endpoint("GET", "/api/quant/strategies", "Get available strategies")
        self.test_endpoint("POST", "/api/quant/backtest", "Run backtest",
                          skip_reason="Requires valid backtest parameters",
                          data={
                              "symbol": "RELIANCE",
                              "strategy": "ma_crossover",
                              "start_date": "2024-01-01",
                              "end_date": "2024-12-01"
                          })
        
        # ========== Walk-Forward Backtest ==========
        print("Testing: Walk-Forward Backtest")
        self.test_endpoint("GET", "/api/v1/walk-forward/symbols", "Get WF backtest symbols")
        self.test_endpoint("POST", "/api/v1/walk-forward/backtest", "Run WF backtest",
                          skip_reason="Requires valid WF parameters")
        
        # ========== Strategy Experiment Lab ==========
        print("Testing: Strategy Experiment Lab")
        self.test_endpoint("GET", "/api/v1/experiment-lab/strategies", "Get lab strategies")
        self.test_endpoint("POST", "/api/v1/experiment-lab/backtest", "Run lab backtest",
                          skip_reason="Requires valid lab parameters")
        
        # ========== AI Endpoints ==========
        print("Testing: AI Endpoints")
        self.test_endpoint("POST", "/api/ai/prompt", "AI strategy prompt",
                          skip_reason="Requires authentication and valid prompt")
        self.test_endpoint("GET", "/api/ai/strategies", "Get AI strategies",
                          skip_reason="Requires authentication")
        
        # ========== AlphaPrime Config ==========
        print("Testing: AlphaPrime")
        self.test_endpoint("GET", "/api/alpha/config", "Get AlphaPrime config",
                          skip_reason="Requires authentication")
        
        # ========== Agentic Bot ==========
        print("Testing: Agentic Bot")
        self.test_endpoint("POST", "/api/agentic-bot/process", "Process agentic bot request",
                          skip_reason="Requires authentication and valid request")
        
        # ========== Alerts ==========
        print("Testing: Alerts")
        self.test_endpoint("GET", "/api/alerts", "Get alerts",
                          skip_reason="Requires authentication")
        
        # ========== Algorithms ==========
        print("Testing: Algorithms")
        self.test_endpoint("GET", "/api/algorithms", "Get algorithms")
        self.test_endpoint("POST", "/api/algorithms/execute", "Execute algorithm",
                          skip_reason="Requires valid algorithm parameters")
        
        # ========== Orders ==========
        print("Testing: Orders")
        self.test_endpoint("GET", "/api/orders", "Get orders",
                          skip_reason="Requires authentication")
        
        # ========== Risk Management ==========
        print("Testing: Risk Management")
        self.test_endpoint("GET", "/api/risk/profile", "Get risk profile",
                          skip_reason="Requires authentication")
        
        # ========== Engine Performance ==========
        print("Testing: Engine Performance")
        self.test_endpoint("GET", "/api/engines/performance", "Get engine performance metrics")
        
        # ========== Settings ==========
        print("Testing: Settings")
        self.test_endpoint("GET", "/api/settings", "Get user settings",
                          skip_reason="Requires authentication")
        
        # ========== Analytics ==========
        print("Testing: Analytics")
        self.test_endpoint("GET", "/api/analytics/overview", "Get analytics overview",
                          skip_reason="Requires authentication")
        
        print("\nAll tests completed!\n")
    
    def generate_summary(self) -> str:
        """Generate a formatted test summary"""
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        summary = f"""
{'='*80}
API TEST SUMMARY REPORT
{'='*80}
Generated: {timestamp}
Base URL: {BASE_URL}

OVERALL STATISTICS:
  Total Tests:   {len(self.results)}
  Passed:        {self.passed} ✓
  Failed:        {self.failed} ✗
  Skipped:       {self.skipped} ⊘
  Success Rate:  {(self.passed/(len(self.results)-self.skipped)*100) if (len(self.results)-self.skipped) > 0 else 0:.1f}%

{'='*80}
DETAILED RESULTS:
{'='*80}

"""
        
        # Group results by status
        for status in ["PASSED", "FAILED", "ERROR", "SKIPPED"]:
            tests = [t for t in self.results if t["status"] == status]
            if not tests:
                continue
            
            summary += f"\n{status} TESTS ({len(tests)}):\n"
            summary += "-" * 80 + "\n"
            
            for test in tests:
                summary += f"\n[{test['status']}] {test['method']} {test['endpoint']}\n"
                summary += f"  Description: {test['description']}\n"
                
                if status == "PASSED":
                    summary += f"  Status Code: {test['actual_code']} (Expected: {test['expected_code']})\n"
                    summary += f"  Response Time: {test['response_time_ms']}ms\n"
                    if "response_sample" in test:
                        summary += f"  Response Sample: {json.dumps(test['response_sample'], indent=4)[:300]}...\n"
                
                elif status == "FAILED":
                    summary += f"  Expected Code: {test['expected_code']}\n"
                    summary += f"  Actual Code: {test.get('actual_code', 'N/A')}\n"
                    if "error" in test:
                        summary += f"  Error: {test['error'][:200]}...\n"
                
                elif status == "ERROR":
                    summary += f"  Error: {test.get('error', 'Unknown error')}\n"
                
                elif status == "SKIPPED":
                    summary += f"  Reason: {test.get('reason', 'No reason provided')}\n"
                
                summary += "\n"
        
        summary += "=" * 80 + "\n"
        summary += "END OF REPORT\n"
        summary += "=" * 80 + "\n"
        
        return summary
    
    def save_summary(self, filename: str = "api_test_summary.txt"):
        """Save the test summary to a file"""
        summary = self.generate_summary()
        with open(filename, "w", encoding="utf-8") as f:
            f.write(summary)
        print(f"Test summary saved to: {filename}")
        return summary

if __name__ == "__main__":
    tester = APITester()
    tester.run_all_tests()
    summary = tester.save_summary()
    print(summary)
