import asyncio
import sys
import os

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from services.institutional_scanner_service import get_institutional_scanner_service

async def run():
    service = get_institutional_scanner_service()
    print("Starting synchronous scan of active NSE universe...")
    res = await service.scan_all_stocks()
    print("Scan status result:", res)

if __name__ == "__main__":
    asyncio.run(run())
