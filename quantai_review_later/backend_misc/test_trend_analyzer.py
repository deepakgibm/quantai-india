"""Test script for TrendAnalyzer"""
from services.trend_analyzer import TrendAnalyzer

t = TrendAnalyzer()

print("=" * 50)
print("TECHNICAL TREND FINDER TEST")
print("=" * 50)

# Test individual stock
print("\n1. Testing RELIANCE analysis:")
result = t.analyze_stock('RELIANCE')
if result:
    print(f"   Trend: {result['trend']}")
    print(f"   Score: {result['strength']}")
    print(f"   Price: {result['current_price']}")
    print(f"   EMA-20: {result['indicators']['ema_20']}")
    print(f"   RSI: {result['indicators']['rsi']}")
    print(f"   ADX: {result['indicators']['adx']}")
    print(f"   Volume Ratio: {result['indicators']['volume_ratio']}")
    print(f"   Reason: {result['reason']}")
else:
    print("   No data available")

# Run full scan
print("\n2. Running full scan (top 10):")
results = t.scan_all(limit=10)
print(f"   Found {len(results)} trending stocks:")
for r in results:
    print(f"   - {r['symbol']}: {r['trend']} score={r['strength']} price={r['current_price']}")

print("\n" + "=" * 50)
print("TEST COMPLETE")
