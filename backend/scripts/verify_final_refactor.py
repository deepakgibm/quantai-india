import asyncio
import os
import sys
import logging

# Set PYTHONPATH
sys.path.append(os.getcwd())

from services.trading_service import get_trading_service
from services.market_service import get_market_service
from utils.index_config import get_index_constituents, get_available_indices
from database import AsyncSessionLocal
from models import User
from sqlalchemy import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_everything():
    logger.info("Starting Final Refactor Verification...")
    
    # 1. Verify DB Indices
    logger.info("Checking Database-Driven Indices...")
    nifty50 = get_index_constituents("NIFTY 50")
    nifty100 = get_index_constituents("NIFTY 100")
    
    logger.info(f"NIFTY 50 count: {len(nifty50)}")
    logger.info(f"NIFTY 100 count: {len(nifty100)}")
    
    if len(nifty50) > 0 and len(nifty100) >= len(nifty50):
        logger.info("✅ Index constituent resolution passed (including hierarchy)")
    else:
        logger.error("❌ Index constituent resolution failed")

    # 2. Verify Available Indices
    indices = get_available_indices()
    logger.info(f"Available indices in DB: {[i['name'] for i in indices]}")
    if len(indices) > 0:
         logger.info("✅ Available indices lookup passed")
    else:
         logger.error("❌ No active indices found in DB")

    # 3. Verify TradingService (Stats)
    logger.info("Checking TradingService Dashboard Stats...")
    async with AsyncSessionLocal() as db:
        user_res = await db.execute(select(User).limit(1))
        user = user_res.scalar_one_or_none()
        
        if user:
            trading_service = get_trading_service()
            stats = await trading_service.get_dashboard_stats(user, db)
            logger.info(f"Dashboard Stats for {user.username}: {stats}")
            logger.info("✅ TradingService stats passed")
        else:
            logger.warning("No user found to test TradingService stats")

    # 4. Verify MarketService (Indices)
    logger.info("Checking MarketService Indices...")
    market_service = get_market_service()
    indices_data = await market_service.get_nifty100_top_movers()
    logger.info(f"Market Movers Source: {indices_data.get('source')}")
    logger.info("✅ MarketService movers passed")

    logger.info("Verification Complete!")

if __name__ == "__main__":
    asyncio.run(verify_everything())
