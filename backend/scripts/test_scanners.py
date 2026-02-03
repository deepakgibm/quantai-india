import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))

from services.ai_service import get_ai_service
from services.trend_analyzer import TrendAnalyzer
from services.breakout_detector import BreakoutDetector
from services.top5_buysell import Top5BuySellEngine
from services.mean_reversion_scanner import MeanReversionScanner
from services.intraday_scanners import VWAPScannerV2, GapScannerV2, MomentumScannerV2, SRBounceScannerV2

async def test_scanners():
    load_dotenv("backend/.env")
    ai_service = get_ai_service()
    
    scanners = [
        (TrendAnalyzer, "Trend Finder", "trend-finder"),
        (BreakoutDetector, "Breakout Detector", "breakout-detector"),
        (Top5BuySellEngine, "Top 5 Picks", "top5-picks"),
        (MomentumScannerV2, "Momentum Scanner", "momentum"),
        (MeanReversionScanner, "Mean Reversion", "mean-reversion"),
        (GapScannerV2, "Gap Scanner", "gap"),
        (VWAPScannerV2, "VWAP Scanner", "vwap"),
        (SRBounceScannerV2, "S/R Bounce Scanner", "sr-bounce")
    ]
    
    print(f"{'Scanner Name':<25} | {'Status':<10} | {'Count':<6} | {'Message/Error'}")
    print("-" * 80)
    
    for scanner_class, name, key in scanners:
        try:
            # We set a shorter timeout for test
            result = await ai_service.run_scanner(scanner_class, name, key, limit=5, timeout=15.0)
            status = result.get("status", "unknown")
            count = result.get("count", 0)
            msg = result.get("message", result.get("description", ""))
            
            print(f"{name:<25} | {status:<10} | {count:<6} | {msg}")
            
        except Exception as e:
            print(f"{name:<25} | {'ERROR':<10} | {'0':<6} | {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_scanners())
