
import asyncio
import logging
import sys
import os
from datetime import datetime

# Add current directory to path
sys.path.append(os.getcwd())

from services.intraday_scanners import get_scanner
from services.relative_strength_scanner import RelativeStrengthScanner
from services.mean_reversion_scanner import MeanReversionScanner

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def verify_scanner(name, scanner_instance):
    logger.info(f"\n--- Verifying Scanner: {name} ---")
    try:
        t0 = datetime.now()
        if hasattr(scanner_instance, 'scan_all'):
            import inspect
            if inspect.iscoroutinefunction(scanner_instance.scan_all):
                result = await scanner_instance.scan_all(limit=5)
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, scanner_instance.scan_all, 5)
                
            elapsed = (datetime.now() - t0).total_seconds()
            
            if isinstance(result, dict):
                stocks = result.get("stocks", [])
                status = result.get("status", "success")
                count = len(stocks)
                processed = result.get("symbols_processed", 0)
                filter_stats = result.get("filter_stats", {})
                
                logger.info(f"Status: {status}")
                logger.info(f"Processed: {processed} symbols")
                logger.info(f"Found: {count} signals")
                logger.info(f"Time Taken: {elapsed:.2f}s")
                logger.info(f"Filter Stats: {filter_stats}")
                
                if count > 0:
                    for i, s in enumerate(stocks):
                        logger.info(f"  {i+1}. {s['symbol']} - {s.get('signal') or s.get('action') or s.get('trend')} (Strength: {s.get('strength')})")
                else:
                    logger.warning(f"No signals found for {name}. Filtered by rule: {filter_stats.get('filtered_by_rule', 0)}")
            else:
                logger.info(f"Found {len(result)} raw results")
        else:
            logger.error(f"Scanner {name} does not have scan_all method")
            
    except Exception as e:
        logger.error(f"Error verifying {name}: {e}", exc_info=True)

async def main():
    logger.info("Starting Comprehensive Scanner Verification...")
    
    # 1. Standalone Scanners
    rs_scanner = RelativeStrengthScanner()
    mr_scanner = MeanReversionScanner()
    
    await verify_scanner("Relative Strength (Daily)", rs_scanner)
    await verify_scanner("Mean Reversion (Daily)", mr_scanner)
    
    # 2. Intraday V2 Scanners
    intraday_names = ["momentum", "gap_scanner", "vwap", "sr_bounce", "relative_strength"]
    
    for name in intraday_names:
        scanner = get_scanner(name, "15m")
        if scanner:
            await verify_scanner(f"Intraday V2: {name}", scanner)
        else:
            logger.error(f"Could not find intraday scanner: {name}")

    logger.info("\nVerification Complete.")

if __name__ == "__main__":
    asyncio.run(main())
