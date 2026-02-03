import sys
import os
import asyncio
import traceback

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from core.scanner.scanner_engine import ScannerEngine
from config import settings

# Force DB URL to localhost for local testing
settings.DATABASE_URL = "postgresql+asyncpg://postgres:admin@localhost:5432/quantai"

async def test_scanner():
    print("Initializing ScannerEngine...")
    try:
        scanner = ScannerEngine()
        print("Running scan...")
        results = await scanner.run_scan(
            indices=["NIFTY 50"],
            timeframe="15m",
            strategies=["MomentumStrategy"] # or any valid strategy name
        )
        print(f"✅ Scan successful. Found {len(results)} results.")
    except Exception as e:
        print("❌ Scan FAILED.")
        with open("error.log", "w") as f:
            traceback.print_exc(file=f)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_scanner())
