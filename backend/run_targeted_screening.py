import sys
import logging

# Add backend to path
sys.path.append("/app")

import asyncio
from database import AsyncSessionLocal
from screener.services.screener_service import ScreenerService

logging.basicConfig(level=logging.INFO)

async def run_test_async():
    async with AsyncSessionLocal() as session:
        service = ScreenerService(session)
        symbols = ["BHEL", "RELIANCE", "TCS"]
        print(f"Running screening for {symbols}...")
        summary = await service.run_full_screening(symbols=symbols)
        print("Summary:", summary)

def run_test():
    asyncio.run(run_test_async())

if __name__ == "__main__":
    run_test()
