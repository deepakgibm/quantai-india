import requests
import json
import time
import os
from datetime import datetime
import statistics

BASE_URL = "http://localhost:8000"
INVENTORY_FILE = r"c:\Users\Deepak Kumar\Downloads\quantai-india\docs\api_inventory.json"
RESULTS_DIR = r"c:\Users\Deepak Kumar\Downloads\quantai-india\tests\api_results_after_fix"
SUMMARY_FILE = r"c:\Users\Deepak Kumar\Downloads\quantai-india\tests\api_fix_summary.md"

os.makedirs(RESULTS_DIR, exist_ok=True)

def login():
    print("Logging in...")
    url = f"{BASE_URL}/api/auth/login"
    payload = {"email": "dthat53@gmail.com", "password": "admin1243"}
    try:
        response = requests.post(url, json=payload)
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
    print(f"Starting Audit of {len(inventory)} APIs...")

    for i, api in enumerate(inventory):
        method = api["method"]
        path = api["path"]
        name = api["api_name"]
        
        url = f"{BASE_URL}{path}"
        print(f"[{i+1}/{len(inventory)}] Testing {method} {path}...", end="", flush=True)
        
        start_time = time.perf_counter()
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif method == "POST":
                # Use some dummy data for POSTs if needed, or empty dict
                payload = {"symbol": "RELIANCE", "test": "data"} if "process" in path or "analyze" in path or "prompt" in path else {}
                response = requests.post(url, headers=headers, json=payload, timeout=30)
            else:
                response = requests.request(method, url, headers=headers, timeout=30)
            
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
            
            print(f" {status_code} ({duration_ms}ms)")
            
        except Exception as e:
            print(f" ERROR: {e}")
            results.append({
                "api_name": name,
                "method": method,
                "path": path,
                "status_code": 500,
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
        f.write("# API Fix Summary (Post-Hardening)\n\n")
        f.write(f"- **Verification Date**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        f.write(f"- **Total APIs Tested**: {len(inventory)}\n")
        f.write(f"- **APIs Passed**: {len(passed)}\n")
        f.write(f"- **APIs Failed**: {len(failed)}\n")
        f.write(f"- **Average Response Time**: {avg_time:.2f} ms\n")
        f.write(f"- **P95 Response Time**: {p95_time:.2f} ms\n\n")
        
        f.write("## Major Latency Improvements\n")
        f.write("| API Name | Before (ms) | After (ms) | Status |\n")
        f.write("|---|---|---|---|\n")
        # Hardcoded baseline from audit for comparison in summary
        baselines = {
            "ai_get_trend_finder_stocks": 7785,
            "ai_get_breakout_stocks": 6130,
            "ai_get_top5_picks": 5080,
            "ai_get_momentum_stocks": 2249
        }
        for r in results:
            if r["api_name"] in baselines:
                f.write(f"| {r['api_name']} | {baselines[r['api_name']]} | {r['response_time_ms']} | {r['status_code']} |\n")

    print("\nVerification Complete.")

if __name__ == "__main__":
    run_audit()
