
import asyncio
import logging
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(backend_dir))

# Configure logging
logging.basicConfig(level=logging.INFO)

from services.sector_service import SectorPerformanceService
from services.dragonfly_client import get_cache

async def test_sector_service():
    print("Initializing Sector Service...")
    service = SectorPerformanceService()
    
    print("Running calculation...")
    await service._calculate_and_cache()
    
    print("Checking Cache...")
    cache = get_cache()
    heatmap = cache.get("qai:market:sector_heatmap")
    
    if heatmap:
        print("\nSUCCESS! Heatmap Data found in cache:")
        data = heatmap.get("data", [])
        print(f"Total Sectors: {len(data)}")
        for i, sector in enumerate(data[:3]):
            print(f"{i+1}. {sector['sector']}: {sector['change_pct']}% ({sector['stock_count']} stocks)")
            
        # Check specific sector
        first_sector = data[0]['sector']
        print(f"\nChecking stocks for {first_sector}...")
        stocks_data = cache.get(f"qai:market:sector_stocks:{first_sector}")
        if stocks_data:
            stocks = stocks_data.get("stocks", [])
            print(f"Found {len(stocks)} stocks. Top: {stocks[0]['symbol']} ({stocks[0]['change_pct']}%)")
        else:
            print(f"FAILED to get stocks for {first_sector}")
    else:
        print("\nFAILURE: No data in 'qai:market:sector_heatmap'")

if __name__ == "__main__":
    asyncio.run(test_sector_service())
