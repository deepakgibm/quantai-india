import asyncio
import logging
import sys
import os

# Add project root to path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

from services.feature_store_orchestrator import get_feature_orchestrator

async def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("DataSync")
    
    logger.info("Starting manual Feature Store population...")
    orchestrator = get_feature_orchestrator(version="v1")
    
    # Process all timeframes
    timeframes = ["1d", "15m", "5m"]
    await orchestrator.process_incremental_updates(timeframes=timeframes)
    
    logger.info("Sync complete.")

if __name__ == "__main__":
    asyncio.run(main())
