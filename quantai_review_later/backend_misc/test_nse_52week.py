"""Test the NSE 52-week high/low service"""
import sys
sys.path.insert(0, '.')

from services.week52_nse_service import get_week52_breakout_service_nse
import json

print("Testing NSE 52-Week High/Low Service...")
print("=" * 50)

service = get_week52_breakout_service_nse()
data = service.detect_breakouts()

print(f"\n52-Week HIGH Breakouts: {len(data['high_breakouts'])} stocks")
print("-" * 50)
for stock in data['high_breakouts'][:5]:  # Show first 5
    print(f"  {stock['symbol']}: New52WH=₹{stock['ltp']}, Prev52WH=₹{stock['prev_close']}, Breakout={stock['breakout_pct']:.2f}%")

print(f"\n52-Week LOW Breakdowns: {len(data['low_breakdowns'])} stocks")
print("-" * 50)
for stock in data['low_breakdowns'][:5]:  # Show first 5
    print(f"  {stock['symbol']}: New52WL=₹{stock['ltp']}, Prev52WL=₹{stock['prev_close']}, Breakdown={stock['breakout_pct']:.2f}%")

print("\n" + "=" * 50)
status = service.get_status()
print(f"Service Status: {json.dumps(status, indent=2)}")
