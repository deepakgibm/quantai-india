import asyncio
import logging
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

from backend.services.feature_store_orchestrator import get_feature_orchestrator

async def main():
    # Set up production logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("FullBackfill")
    
    # Use production version
    orchestrator = get_feature_orchestrator(version="v1")
    
    # Production timeframes
    timeframes = ["1d", "1h", "15m", "5m"]
    
    logger.info("🌊 Starting Full Market Feature Store Backfill...")
    logger.info(f"Target Timeframes: {timeframes}")
    
    try:
        # This will iterate through all active symbols in instrument_master
        await orchestrator.process_incremental_updates(timeframes=timeframes)
        logger.info("✅ Full Backfill Completed Successfully.")
    except Exception as e:
        logger.error(f"❌ Backfill Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
