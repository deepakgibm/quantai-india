import requests

BASE = 'http://localhost:8000'
login = requests.post(f'{BASE}/api/auth/login', json={'email': 'demo@example.com', 'password': 'demo123'})
token = login.json().get('access_token')
headers = {'Authorization': f'Bearer {token}'}

print("AI Endpoints Test:")
eps = [
    '/api/ai/breakout-detector',
    '/api/ai/top3-picks', 
    '/api/ai/earnings-reaction',
    '/api/ai/market-analysis',
    '/api/ai/trend-finder',
]

for ep in eps:
    try:
        r = requests.get(f'{BASE}{ep}', headers=headers, timeout=30)
        print(f'{ep}: {r.status_code}')
        if r.status_code != 200:
            print(f'  Error: {r.text[:100]}')
    except Exception as e:
        print(f'{ep}: ERROR - {e}')
