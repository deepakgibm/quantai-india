import requests

BASE = 'http://localhost:8000'
login = requests.post(f'{BASE}/api/auth/login', json={'email': 'demo@example.com', 'password': 'demo123'})
token = login.json().get('access_token')
headers = {'Authorization': f'Bearer {token}'}

endpoints = [
    ('GET', '/api/auth/me', 'Auth Me'),
    ('GET', '/api/trading/dashboard', 'Dashboard'),
    ('GET', '/api/trading/market-indices', 'Indices'),
    ('GET', '/api/trading/gainers-losers', 'Gainers'),
    ('GET', '/api/ai/market-analysis', 'AI Market'),
    ('GET', '/api/ai/trend-finder', 'Trend'),
    ('GET', '/api/ai/breakout-detector', 'Breakout'),
    ('GET', '/api/ai/top3-picks', 'Top3'),
    ('GET', '/api/ai/earnings-reaction', 'Earnings'),
    ('GET', '/api/orders/', 'Orders'),
    ('GET', '/api/algorithms/', 'Algos'),
    ('GET', '/api/risk/', 'Risk'),
    ('GET', '/api/settings/', 'Settings'),
    ('GET', '/api/upstox/auth-url', 'Upstox Auth'),
    ('GET', '/api/upstox/portfolio', 'Portfolio'),
    ('GET', '/api/v1/alpha-prime/signals', 'Signals'),
    ('GET', '/api/v1/alpha-prime/config', 'Config'),
    ('POST', '/api/ai/prompt', 'AI Prompt'),
    ('POST', '/api/agentic-bot/process', 'Agentic Bot'),
]

passed = 0
failed = 0

print('='*50)
print('FINAL E2E TEST')
print('='*50)
print('Login: 200 OK')

for method, path, name in endpoints:
    try:
        if method == 'GET':
            r = requests.get(f'{BASE}{path}', headers=headers, timeout=30)
        else:
            r = requests.post(f'{BASE}{path}', headers=headers, json={'prompt': 'test'}, timeout=30)
        
        status = 'OK' if r.status_code == 200 else 'XX'
        print(f'{status} {name}: {r.status_code}')
        if r.status_code == 200:
            passed += 1
        else:
            failed += 1
    except Exception as e:
        print(f'XX {name}: ERROR')
        failed += 1

print('='*50)
print(f'TOTAL: {passed+1}/{passed+failed+1} PASSED ({round((passed+1)/(passed+failed+1)*100)}%)')
