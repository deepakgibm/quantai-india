import json

with open("momentum_response.json", "r") as f:
    data = json.load(f)

# Count stocks by bucket
buckets = {}
for stock in data.get("data", []):
    bucket = stock.get("bucket", "UNKNOWN")
    if bucket not in buckets:
        buckets[bucket] = 0
    buckets[bucket] += 1

print("MOMENTUM BUCKET COUNTS:")
print("-" * 40)
print(f"STRONG_BULLISH:   {buckets.get('STRONG_BULLISH', 0)} stocks")
print(f"MODERATE_BULLISH: {buckets.get('MODERATE_BULLISH', 0)} stocks")
print(f"NEUTRAL:          {buckets.get('NEUTRAL', 0)} stocks")
print(f"MODERATE_BEARISH: {buckets.get('MODERATE_BEARISH', 0)} stocks")
print(f"STRONG_BEARISH:   {buckets.get('STRONG_BEARISH', 0)} stocks")
print(f"EXTREME_BEARISH:  {buckets.get('EXTREME_BEARISH', 0)} stocks")
print("-" * 40)
print(f"TOTAL: {len(data.get('data', []))} stocks")
