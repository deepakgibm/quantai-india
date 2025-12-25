import requests

BASE = 'http://localhost:8000'
login = requests.post(f'{BASE}/api/auth/login', json={'email': 'demo@example.com', 'password': 'demo123'})
token = login.json().get('access_token')
headers = {'Authorization': f'Bearer {token}'}

results = []

# GET endpoints
get_eps = [
    '/api/auth/me',
    '/api/trading/dashboard',
    '/api/trading/market-indices',
    '/api/trading/gainers-losers',
    '/api/ai/market-analysis',
    '/api/ai/trend-finder',
    '/api/ai/breakout-detector',
    '/api/ai/top3-picks',
    '/api/ai/earnings-reaction',
    '/api/orders/',
    '/api/algorithms/',
    '/api/risk/',
    '/api/settings/',
    '/api/upstox/auth-url',
    '/api/upstox/portfolio',
    '/api/v1/alpha-prime/signals',
    '/api/v1/alpha-prime/config',
]

for ep in get_eps:
    try:
        r = requests.get(f'{BASE}{ep}', headers=headers, timeout=30)
        results.append((ep, r.status_code))
    except Exception as e:
        results.append((ep, str(e)[:20]))

# POST endpoints
post_eps = [
    ('/api/ai/prompt', {'prompt': 'test'}),
    ('/api/agentic-bot/process', {'prompt': 'test'}),
]

for ep, data in post_eps:
    try:
        r = requests.post(f'{BASE}{ep}', headers=headers, json=data, timeout=30)
        results.append((ep, r.status_code))
    except Exception as e:
        results.append((ep, str(e)[:20]))

# Print results
passed = 0
failed = 0
for ep, status in results:
    icon = 'OK' if status == 200 else 'XX'
    print(f'{icon} {ep}: {status}')
    if status == 200:
        passed += 1
    else:
        failed += 1

print(f'\nTOTAL: {passed}/{passed+failed} PASSED')
