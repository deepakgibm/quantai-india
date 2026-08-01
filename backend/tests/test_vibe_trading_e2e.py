"""
E2E Integration Verification for Vibe Trading / Coding - Backend & Frontend.
"""
import requests
import json
import sys
import time
import subprocess

BASE_URL_BACKEND = "http://localhost:8000"
BASE_URL_FRONTEND = "http://localhost:3000"

def get_auth_token():
    """Obtain auth token for protected API requests."""
    try:
        resp = requests.post(
            f"{BASE_URL_BACKEND}/api/auth/login",
            json={"email": "test@quantai.com", "password": "test123"},
            timeout=10
        )
        if resp.status_code == 200:
            return resp.json().get("access_token")
    except Exception as e:
        print(f"Login connection failed: {e}")
    return None

def test_backend_endpoint(endpoint, payload, token):
    """Hits an SSE streaming endpoint and reads the events."""
    url = f"{BASE_URL_BACKEND}/api/ai/{endpoint}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"\n---> Testing backend endpoint: /api/ai/{endpoint}")
    start_time = time.time()
    
    decision_task_verified = False
    decision_summary = None
    
    try:
        response = requests.post(url, json=payload, headers=headers, stream=True, timeout=30)
        if response.status_code != 200:
            print(f"  [FAIL] /api/ai/{endpoint} returned status code {response.status_code}: {response.text}")
            return False
            
        print("  [OK] SSE stream connected successfully. Reading chunks:")
        chunk_count = 0
        received_text = False
        
        for line in response.iter_lines():
            if not line:
                continue
            decoded_line = line.decode('utf-8').strip()
            if decoded_line.startswith("data:"):
                data_str = decoded_line.replace("data:", "").strip()
                if data_str == ": keepalive":
                    continue
                try:
                    event = json.loads(data_str)
                    chunk_count += 1
                    received_text = True
                    if endpoint == "committee" and event.get("type") == "task_completed" and event.get("task_id") == "task-decision":
                        decision_task_verified = True
                        decision_summary = event.get("data", {}).get("summary")
                    if chunk_count <= 2 or event.get("type") in ["worker_failed", "run_completed"]:
                        print(f"    Event: {event}")
                except json.JSONDecodeError:
                    received_text = True
                    if chunk_count <= 2:
                        print(f"    Raw chunk: {data_str[:100]}")
                        
        duration = time.time() - start_time
        print(f"  [PASS] Received {chunk_count} chunks in {duration:.2f} seconds.")
        
        if endpoint == "committee":
            if not decision_task_verified:
                print("  [FAIL] Swarm Committee failed regression test: 'task-decision' task_completed event not found in stream.")
                return False
            if not decision_summary or len(decision_summary) < 50:
                print(f"  [FAIL] Swarm Committee failed regression test: 'task-decision' summary is missing or too short: {decision_summary}")
                return False
            print("  [PASS] Swarm Committee regression test passed: 'task-decision' completed with rich consensus summary.")
            
        return received_text
    except Exception as e:
        print(f"  [FAIL] Exception occurred: {e}")
        return False

def test_frontend_routes():
    """Verify that the frontend web server responds correctly."""
    print("\n---> Testing frontend web server routing...")
    try:
        # Check /vibe-trading endpoint (Nginx should fall back to index.html and return 200)
        resp = requests.get(f"{BASE_URL_FRONTEND}/vibe-trading", timeout=10)
        if resp.status_code == 200 and "<div id=\"root\">" in resp.text:
            print("  [PASS] GET /vibe-trading returned 200 OK and valid index.html template.")
            return True
        else:
            print(f"  [FAIL] GET /vibe-trading returned status {resp.status_code}: {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"  [FAIL] Frontend connection failed: {e}")
        return False

def validate_compiled_bundle():
    """Inspects the compiled JS bundle in the frontend container to verify VibeTrading component inclusion."""
    print("\n---> Validating compiled assets inside the frontend container...")
    try:
        # Get the name of the bundle file
        cmd_find = "docker compose exec -T frontend sh -c \"ls /usr/share/nginx/html/assets/index-*.js\""
        output = subprocess.check_output(cmd_find, shell=True).decode('utf-8').strip()
        print(f"  Found frontend bundle file: {output}")
        
        # Read the file and check for key component terms
        cmd_cat = f"docker compose exec -T frontend sh -c \"cat {output}\""
        bundle_content = subprocess.check_output(cmd_cat, shell=True).decode('utf-8')
        
        required_terms = [
            "Vibe Trading / Coding",
            "Swarm DAG Execution Monitor",
            "Investment Verdict",
            "Bull Analyst",
            "Bear Analyst"
        ]
        
        all_present = True
        for term in required_terms:
            if term in bundle_content:
                print(f"  [PASS] Verified compiled JS bundle contains term: '{term}'")
            else:
                print(f"  [FAIL] Compiled JS bundle is missing term: '{term}'")
                all_present = False
                
        return all_present
    except Exception as e:
        print(f"  [FAIL] Bundle validation failed: {e}")
        return False

def main():
    print("=" * 80)
    print("           VIBE TRADING / CODING FULL-STACK E2E INTEGRATION TEST")
    print("=" * 80)
    
    # 1. Test Backend Endpoints
    token = get_auth_token()
    if not token:
        print("[CRITICAL] Could not obtain auth token from backend. Exiting.")
        sys.exit(1)
        
    print("[OK] Auth token acquired successfully.")
    
    backend_tests = [
        ("chat", {"message": "Is TCS showing mean reversion signs?"}),
        ("portfolio", {}),
        ("backtest", {"symbol": "RELIANCE", "strategy": "RSI Mean Reversion"}),
        ("scanner", {"scanner_id": "trend-finder"}),
        ("committee", {"symbol": "RELIANCE"})
    ]
    
    backend_ok = True
    for endpoint, payload in backend_tests:
        if not test_backend_endpoint(endpoint, payload, token):
            backend_ok = False
            
    # 2. Test Frontend Server
    frontend_ok = test_frontend_routes()
    
    # 3. Validate Frontend Bundle
    bundle_ok = validate_compiled_bundle()
    
    print("\n" + "=" * 80)
    print("E2E VERIFICATION REPORT SUMMARY:")
    print("-" * 80)
    print(f"  Backend Streaming Endpoints:  {'[PASS]' if backend_ok else '[FAIL]'}")
    print(f"  Frontend Server Routing:      {'[PASS]' if frontend_ok else '[FAIL]'}")
    print(f"  Frontend Production Bundle:   {'[PASS]' if bundle_ok else '[FAIL]'}")
    print("=" * 80)
    
    if backend_ok and frontend_ok and bundle_ok:
        print("          ALL VERIFICATION TESTS COMPLETED SUCCESSFULLY! E2E RUN PASS.")
        print("=" * 80)
        sys.exit(0)
    else:
        print("          SOME INTEGRATION TESTS FAILED. CHECK LOG DETAILS.")
        print("=" * 80)
        sys.exit(1)

if __name__ == "__main__":
    main()
