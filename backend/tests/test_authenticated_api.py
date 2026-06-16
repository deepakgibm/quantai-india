"""
Authenticated API validation script - tests protected endpoints with auth token.
"""
import requests
import psycopg2
import json
import time
import os
from datetime import datetime

BASE_URL = "http://localhost:8000"
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:admin@localhost:5432/quantai")

# User credentials
USER_EMAIL = "dthat53@gmail.com"
USER_PASSWORD = "admin1243"

def get_db_connection():
    sync_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    return psycopg2.connect(sync_url)

def get_auth_token():
    """Get auth token using provided credentials."""
    print(f"[1] Authenticating as {USER_EMAIL}...")
    try:
        resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": USER_EMAIL, "password": USER_PASSWORD},
            timeout=10
        )
        print(f"    Login response: {resp.status_code}")
        
        if resp.status_code == 200:
            token = resp.json().get("access_token")
            print(f"    Token obtained: {token[:50]}..." if token else "    No token in response")
            return token
        else:
            print(f"    Error: {resp.text[:200]}")
            return None
    except Exception as e:
        print(f"    Exception: {e}")
        return None

def run_endpoint_check(url, name, auth_token=None):
    """Test a single endpoint and return result."""
    headers = {}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    
    try:
        start = time.time()
        resp = requests.get(url, headers=headers, timeout=30)
        elapsed_ms = (time.time() - start) * 1000
        return {
            "endpoint": name,
            "url": url,
            "status_code": resp.status_code,
            "response_time_ms": round(elapsed_ms, 2),
            "pass": resp.status_code == 200,
            "data_preview": str(resp.text)[:300] if resp.ok else resp.text[:200]
        }
    except Exception as e:
        return {
            "endpoint": name,
            "url": url,
            "status_code": "ERROR",
            "response_time_ms": 0,
            "pass": False,
            "error": str(e)
        }

def run_db_validations(conn):
    """Run database ground truth validations."""
    cur = conn.cursor()
    results = {}
    
    cur.execute("SELECT COUNT(*) FROM instrument_master WHERE is_active = TRUE")
    results["instrument_count"] = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM stock_candle WHERE timeframe = 1440")
    results["daily_candle_count"] = cur.fetchone()[0]
    
    cur.execute("SELECT MAX(candle_ts) FROM stock_candle WHERE timeframe = 1440")
    row = cur.fetchone()
    results["latest_daily_candle"] = str(row[0]) if row[0] else None
    
    cur.execute("""
        SELECT COUNT(DISTINCT im.symbol) 
        FROM stock_candle sc 
        JOIN instrument_master im ON sc.instrument_id = im.instrument_id 
        WHERE sc.timeframe = 1440
    """)
    results["symbols_with_daily_candles"] = cur.fetchone()[0]
    
    return results

def main():
    print("=" * 80)
    print("       AUTHENTICATED API REGRESSION TEST - Schema Migration")
    print("=" * 80)
    print(f"\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE_URL}")
    
    # Get auth token
    token = get_auth_token()
    if not token:
        print("\n❌ FAILED: Could not obtain authentication token")
        return 1
    
    print(f"\n[2] Testing authenticated endpoints...")
    print("-" * 80)
    
    # Protected endpoints that previously showed 401
    endpoints = [
        (f"{BASE_URL}/api/scanner/strategies", "Scanner Strategies"),
        (f"{BASE_URL}/api/scanner/timeframes", "Scanner Timeframes"),
        (f"{BASE_URL}/api/scanner/indices", "Scanner Indices"),
        (f"{BASE_URL}/api/scanner/momentum", "Scanner Momentum"),
        (f"{BASE_URL}/api/scanner/breakout", "Scanner Breakout"),
        (f"{BASE_URL}/api/scanner/week52-breakouts", "Week52 Breakouts"),
        (f"{BASE_URL}/api/scanner/reversal", "Scanner Reversal"),
        (f"{BASE_URL}/api/scanner/trendfinder", "Scanner TrendFinder"),
        (f"{BASE_URL}/api/trading/dashboard", "Trading Dashboard"),
        (f"{BASE_URL}/api/trading/top-gainers", "Top Gainers"),
        (f"{BASE_URL}/api/trading/gainers-losers", "Gainers Losers"),
        (f"{BASE_URL}/api/ai/breakout-stocks", "AI Breakout Stocks"),
    ]
    
    results = []
    passed = 0
    failed = 0
    
    for url, name in endpoints:
        result = run_endpoint_check(url, name, token)
        results.append(result)
        
        status = "✅ PASS" if result["pass"] else "❌ FAIL"
        if result["pass"]:
            passed += 1
        else:
            failed += 1
        
        print(f"{status} | {name:25} | {result['status_code']:4} | {result['response_time_ms']:8.2f}ms")
        if not result["pass"] and result.get("data_preview"):
            print(f"       Error: {result['data_preview'][:100]}")
    
    print("-" * 80)
    print(f"\nAuthenticated API Results: {passed} passed, {failed} failed")
    
    # Database validations
    print(f"\n[3] Database Ground Truth Validations...")
    print("-" * 80)
    
    try:
        conn = get_db_connection()
        db_results = run_db_validations(conn)
        conn.close()
        
        for key, value in db_results.items():
            print(f"   {key}: {value}")
        
        print("-" * 80)
        print("✅ Database connection and queries successful")
    except Exception as e:
        print(f"❌ Database validation failed: {e}")
        db_results = {}
    
    # Summary
    print(f"\n{'=' * 80}")
    print("                              SUMMARY")
    print("=" * 80)
    
    if failed == 0:
        print("\n✅ ALL AUTHENTICATED TESTS PASSED - Schema migration is STABLE")
    else:
        print(f"\n⚠️  {failed} TESTS HAVE ISSUES - Review required")
        print("\nFailed endpoints:")
        for r in results:
            if not r["pass"]:
                print(f"   - {r['endpoint']}: {r.get('status_code')} - {r.get('data_preview', r.get('error', ''))[:80]}")
    
    print("\n" + "=" * 80)
    
    # Save results to JSON
    output = {
        "timestamp": datetime.now().isoformat(),
        "authenticated": True,
        "user": USER_EMAIL,
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{100*passed/len(results):.1f}%"
        },
        "api_results": results,
        "db_validations": db_results
    }
    
    with open("test_results_authenticated.json", "w") as f:
        json.dump(output, f, indent=2, default=str)
    
    print(f"\nDetailed results saved to: test_results_authenticated.json")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    exit(main())
