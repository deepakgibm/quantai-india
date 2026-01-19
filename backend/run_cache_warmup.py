import asyncio
import logging
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from workers.cache_warmer import CacheWarmer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting manual cache warm-up...")
    warmer = CacheWarmer()
    # Call _run_warmup directly (not in a thread) to wait for completion
    warmer._run_warmup()
    logger.info("Manual cache warm-up finished.")

if __name__ == "__main__":
    main()
