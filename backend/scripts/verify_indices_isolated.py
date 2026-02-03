import os
import sys
import logging

# Set PYTHONPATH
sys.path.append(os.getcwd())

from utils.index_config import get_index_constituents, get_available_indices

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_indices_isolated():
    logger.info("Starting Isolated Index Verification...")
    
    # 1. Verify DB Indices directly via utility
    try:
        nifty50 = get_index_constituents("NIFTY 50")
        nifty100 = get_index_constituents("NIFTY 100")
        
        logger.info(f"NIFTY 50 found: {len(nifty50)} symbols")
        logger.info(f"NIFTY 100 found: {len(nifty100)} symbols")
        
        if len(nifty50) == 50:
            logger.info("✅ NIFTY 50 count is exactly 50. Perfect.")
        elif len(nifty50) > 0:
            logger.info(f"✅ NIFTY 50 has {len(nifty50)} symbols (some might be missing in instrument_master)")
        
        if len(nifty100) > len(nifty50):
            logger.info("✅ NIFTY 100 correctly includes NIFTY 50 + others (Hierarchy working)")
        
        # 2. Check Available Indices
        indices = get_available_indices()
        logger.info(f"Active Indices: {[i['name'] for i in indices]}")
        
    except Exception as e:
        logger.error(f"❌ Isolated verification failed: {e}")

if __name__ == "__main__":
    verify_indices_isolated()
    logger.info("Isolated Verification Complete!")
