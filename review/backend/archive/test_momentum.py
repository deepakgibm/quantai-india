import requests
from collections import Counter

response = requests.get("http://localhost:8000/api/scanner/momentum")
data = response.json()

print(f"Total stocks: {len(data.get('data', []))}")

# Count by bucket
buckets = Counter(stock['bucket'] for stock in data.get('data', []))
print("\nBucket distribution:")
for bucket in ['STRONG_BULLISH', 'MODERATE_BULLISH', 'NEUTRAL', 'MODERATE_BEARISH', 'STRONG_BEARISH', 'EXTREME_BULLISH', 'EXTREME_BEARISH']:
    count = buckets.get(bucket, 0)
    if count > 0:
        print(f"  {bucket}: {count}")
