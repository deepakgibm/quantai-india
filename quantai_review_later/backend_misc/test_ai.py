import requests

BASE = 'http://localhost:8000'
login = requests.post(f'{BASE}/api/auth/login', json={'email': 'demo@example.com', 'password': 'demo123'})
token = login.json().get('access_token')
headers = {'Authorization': f'Bearer {token}'}

endpoints = [
    '/api/ai/trend-finder',
    '/api/ai/breakout-detector', 
    '/api/ai/top3-picks',
    '/api/ai/earnings-reaction'
]

print("Testing AI Trading Engines:")
for ep in endpoints:
    try:
        r = requests.get(f'{BASE}{ep}', headers=headers, timeout=60)
        print(f'{ep}: {r.status_code}')
    except Exception as e:
        print(f'{ep}: ERROR - {str(e)[:50]}')
