"""Test momentum endpoint"""
import requests
import json

r = requests.get('http://localhost:8000/api/scanner/momentum', timeout=60)
data = r.json()
print(f'Status: {r.status_code}')
print(f'Type: {data.get("type")}')
print(f'Data count: {len(data.get("data", []))}')

if data.get('data'):
    print(f'\nSample data:')
    for item in data['data'][:5]:
        print(f"  {item.get('symbol')}: {item.get('change_pct')}% - {item.get('bucket')}")
else:
    print('No data returned')

print(f'\nStatus info: {data.get("status")}')
