
import requests
import json
import time

URL = "http://localhost:8000/api/scanner/momentum?force_refresh=true"
# We need an auth token if auth is enabled. Let's assume we can bypass it for local test if we are inside container or use a dummy token if we know the secret.
# Actually, I'll run it from within the container and see logs.
# But I already did curl -v.

def test_refresh():
    try:
        print(f"Requesting {URL}...")
        # Since I can't easily get a JWT here without login flow, 
        # I'll just check if the endpoint is reachable and what logs it produces even if 401.
        # But wait, 401 won't trigger the sync logic.
        
        # Let's try to find a valid token from another request in logs? No.
        # I'll temporarily disable auth AGAIN but more thoroughly or use a mock user.
        print("This test requires authentication. I will check logs instead after user refresh.")

if __name__ == "__main__":
    test_refresh()
