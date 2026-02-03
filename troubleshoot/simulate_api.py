import asyncio
import sys
import os
import json

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from services.breakout_detector import BreakoutDetector
from services.live_price_enricher import enrich_scanner_results
from config import settings

async def run_audit():
    print("Running Breakout Detector Scan...")
    detector = BreakoutDetector()
    raw_stocks = detector.scan_all(limit=20)
    
    print(f"Found {len(raw_stocks)} stocks. Enriching with live prices...")
    enriched_stocks = await enrich_scanner_results(raw_stocks, settings.UPSTOX_ACCESS_TOKEN)
    
    print("\n--- RESULTS ---")
    for s in enriched_stocks:
        symbol = s.get("symbol")
        price = s.get("current_price") or s.get("ltp")
        source = s.get("price_source")
        type = s.get("breakout_type")
        level = s.get("breakout_level")
        print(f"SYM: {symbol:10} | PRICE: {price:8} | SOURCE: {source:8} | LEVEL: {level:8} | TYPE: {type}")
        
    # Check for 308.5 specifically
    match = [s for s in enriched_stocks if (s.get("current_price") == 308.5 or s.get("ltp") == 308.5 or s.get("breakout_level") == 308.5)]
    if match:
        print(f"\n🎯 FOUND 308.5 MATCH: {json.dumps(match, indent=2)}")
    else:
        print("\n❌ No record found with 308.5 price.")

if __name__ == "__main__":
    asyncio.run(run_audit())
