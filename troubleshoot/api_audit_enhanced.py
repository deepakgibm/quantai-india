"""
Enhanced API Audit Runner with Proper Payloads
Tests all 122 APIs with appropriate request bodies for each endpoint.
"""

import requests
import json
import time
import os
from datetime import datetime
import statistics

BASE_URL = "http://localhost:8000"
INVENTORY_FILE = r"c:\Users\Deepak Kumar\Downloads\quantai-india\docs\api_inventory.json"
RESULTS_DIR = r"c:\Users\Deepak Kumar\Downloads\quantai-india\tests\api_results_final"
SUMMARY_FILE = r"c:\Users\Deepak Kumar\Downloads\quantai-india\tests\api_final_summary.md"

os.makedirs(RESULTS_DIR, exist_ok=True)

# Proper payloads for each API type
PAYLOADS = {
    # Agentic Bot
    "agentic_bot_run_agent_analysis": {"prompt": "Analyze RELIANCE stock", "symbol": "RELIANCE"},
    "agentic_bot_process_agent_request": {"prompt": "What is the trend for TCS?"},
    
    # AI
    "ai_process_ai_prompt": {"prompt": "Analyze market sentiment"},
    "ai_process_command": {"command": "analyze RELIANCE"},
    "ai_get_ai_sentiment": None,  # GET with query param
    
    # Algorithms - FIXED: Added config field
    "algorithms_create_algorithm": {"name": "Test Strategy", "description": "Test", "config": {"rsi_period": 14, "threshold": 70}},
    "algorithms_get_algorithm": None,  # Path param - skip
    "algorithms_update_algorithm": {"name": "Updated Strategy", "config": {"rsi_period": 21}},
    "algorithms_delete_algorithm": None,  # Path param - skip
    
    # Analytics
    "analytics_get_correlation_matrix": ["RELIANCE", "TCS", "INFY"],
    "analytics_execute_custom_query": {"sql": "SELECT * FROM stock_candles LIMIT 5"},
    "analytics_archive_month": {"year": 2025, "month": 12},
    "analytics_restore_from_archive": {"year": 2025, "month": 12},
    
    # Auth - FIXED: Added username and full_name
    "auth_signup": {"email": "test@example.com", "password": "test123", "username": "testuser", "full_name": "Test User"},
    "auth_login": {"email": "dthat53@gmail.com", "password": "admin1243"},
    "auth_firebase_login": {"id_token": "test_token"},
    
    # Orders
    "orders_create_order": {"symbol": "RELIANCE", "quantity": 10, "side": "BUY", "order_type": "MARKET"},
    
    # Quant Bot - FIXED: Added start_date and end_date
    "quant_bot_run_backtest": {"symbol": "RELIANCE", "strategy_id": 1, "start_date": "2024-01-01", "end_date": "2024-12-31"},
    "quant_bot_run_walkforward": {"symbol": "RELIANCE", "strategy_id": 1, "start_date": "2024-01-01", "end_date": "2024-12-31"},
    
    # Scanner
    "scanner_run_scan": {"indices": ["NIFTY50"], "strategies": ["momentum"], "timeframe": "1d"},
    "scanner_save_preset": {"name": "Test Preset", "indices": ["NIFTY50"], "timeframe": "1d", "strategies": ["momentum"]},
    
    # Upstox
    "upstox_upstox_callback": {"code": "test_code"},
    
    # Backtest
    "backtest_strategies_search_strategies": None,  # Query param
    
    # Experiment Lab
    "experiment_lab_get_strategy": None,  # Path param
    "experiment_lab_run_backtest": {"symbol": "RELIANCE", "strategy_ids": [1, 2], "timeframe": "1D"},
    "experiment_lab_compare_strategies": {"symbol": "RELIANCE", "strategy_ids": [1, 2, 3]},
    
    # ML Forecast
    "ml_forecast_predict_price": None,  # Query param
}

# Query parameters for GET endpoints
QUERY_PARAMS = {
    "ai_get_ai_sentiment": {"symbol": "RELIANCE"},
    "backtest_strategies_search_strategies": {"query": "momentum"},
    "ml_forecast_predict_price": {"symbol": "RELIANCE"},
    "analytics_get_volatility_analysis": {"symbol": "RELIANCE"},
    "analytics_get_latest_indicators": {"symbol": "RELIANCE"},
}

def login():
    print("Logging in...")
    url = f"{BASE_URL}/api/auth/login"
    payload = {"email": "dthat53@gmail.com", "password": "admin1243"}
    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json().get("access_token")
    except Exception as e:
        print(f"Login failed: {e}")
    return None

def run_audit():
    token = login()
    if not token:
        print("Auth failed. Exiting.")
        return

    headers = {"Authorization": f"Bearer {token}"}
    
    with open(INVENTORY_FILE, 'r') as f:
        inventory = json.load(f)

    results = []
    print(f"Starting Enhanced Audit of {len(inventory)} APIs...")

    for i, api in enumerate(inventory):
        method = api["method"]
        path = api["path"]
        name = api["api_name"]
        
        url = f"{BASE_URL}{path}"
        
        # Handle path parameters
        if "{" in path:
            url = url.replace("{symbol}", "RELIANCE")
            url = url.replace("{algorithm_id}", "1")
            url = url.replace("{order_id}", "1")
            url = url.replace("{preset_id}", "1")
            url = url.replace("{strategy_id}", "1")
            url = url.replace("{strategy_name}", "momentum_rsi")
            url = url.replace("{scan_id}", "1")
        
        # Add query params
        if name in QUERY_PARAMS:
            params = "&".join([f"{k}={v}" for k, v in QUERY_PARAMS[name].items()])
            url = f"{url}?{params}"
        
        print(f"[{i+1}/{len(inventory)}] {method} {path}...", end="", flush=True)
        
        start_time = time.perf_counter()
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=60)
            elif method == "POST":
                payload = PAYLOADS.get(name, {})
                if payload is None:
                    payload = {}
                response = requests.post(url, headers=headers, json=payload, timeout=60)
            elif method == "PUT":
                payload = PAYLOADS.get(name, {})
                response = requests.put(url, headers=headers, json=payload, timeout=60)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=60)
            else:
                response = requests.request(method, url, headers=headers, timeout=60)
            
            end_time = time.perf_counter()
            duration_ms = int((end_time - start_time) * 1000)
            
            status_code = response.status_code
            try:
                payload_resp = response.json()
            except:
                payload_resp = {"raw": response.text[:200]}

            result = {
                "api_name": name,
                "method": method,
                "path": path,
                "status_code": status_code,
                "response_time_ms": duration_ms,
                "response_payload": payload_resp
            }
            results.append(result)
            
            with open(os.path.join(RESULTS_DIR, f"api_{i+1:03d}_{name}.json"), 'w') as f:
                json.dump(result, f, indent=2)
            
            status_icon = "✓" if 200 <= status_code < 300 else "✗"
            print(f" {status_icon} {status_code} ({duration_ms}ms)")
            
        except Exception as e:
            print(f" ERROR: {e}")
            results.append({
                "api_name": name,
                "method": method,
                "path": path,
                "status_code": 0,
                "response_time_ms": 0,
                "error": str(e)
            })

    # Generate Summary
    passed = [r for r in results if 200 <= r["status_code"] < 300]
    failed = [r for r in results if not (200 <= r["status_code"] < 300)]
    times = [r["response_time_ms"] for r in results if r["response_time_ms"] > 0]
    
    avg_time = statistics.mean(times) if times else 0
    p95_time = statistics.quantiles(times, n=20)[18] if len(times) >= 20 else max(times) if times else 0

    with open(SUMMARY_FILE, 'w') as f:
        f.write("# API Final Summary (With Proper Payloads)\n\n")
        f.write(f"- **Verification Date**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        f.write(f"- **Total APIs Tested**: {len(inventory)}\n")
        f.write(f"- **APIs Passed**: {len(passed)}\n")
        f.write(f"- **APIs Failed**: {len(failed)}\n")
        f.write(f"- **Pass Rate**: {len(passed)/len(inventory)*100:.1f}%\n")
        f.write(f"- **Average Response Time**: {avg_time:.2f} ms\n")
        f.write(f"- **P95 Response Time**: {p95_time:.2f} ms\n\n")
        
        if failed:
            f.write("## Remaining Failures\n")
            f.write("| API Name | Status | Error |\n")
            f.write("|---|---|---|\n")
            for r in failed[:20]:  # Show first 20
                error = str(r.get("response_payload", {}).get("error", {}).get("message", r.get("error", "Unknown")))[:50]
                f.write(f"| {r['api_name']} | {r['status_code']} | {error} |\n")

    print(f"\n✅ Verification Complete: {len(passed)}/{len(inventory)} passed ({len(passed)/len(inventory)*100:.1f}%)")

if __name__ == "__main__":
    run_audit()
