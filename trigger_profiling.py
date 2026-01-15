
import requests
import time

print("Triggering Breakout Scanner for Profiling (No Auth)...")
start = time.time()
try:
    response = requests.get("http://localhost:8000/api/scanner/breakout", timeout=60)
    print(f"Response Code: {response.status_code}")
    print(f"Total Request Time: {time.time() - start:.2f}s")
except Exception as e:
    print(f"Request failed: {e}")
