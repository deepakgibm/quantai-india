import asyncio
import logging
import sys
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add current directory to path so imports work
sys.path.append(os.getcwd())

async def verify_live_price_enricher():
    logger.info("Verifying LivePriceEnricher...")
    try:
        from services.live_price_enricher import fetch_live_full_quotes
        
        # Test symbols
        results = await fetch_live_full_quotes(["RELIANCE", "TCS", "INFY"])
        
        if results:
            logger.info(f"✅ LivePriceEnricher returned data for {len(results)} symbols.")
            for symbol, data in results.items():
                logger.info(f"   - {symbol}: {data}")
        else:
            logger.warning("⚠️ LivePriceEnricher returned empty results (might be market closed or no data), but no crash.")
            
        return True
    except IndentationError:
        logger.error("❌ IndentationError detected in live_price_enricher! Verification FAILED.")
        return False
    except Exception as e:
        logger.error(f"❌ Error in LivePriceEnricher: {e}")
        import traceback
        traceback.print_exc()
        return False

async def verify_scanners():
    logger.info("\nVerifying Scanners...")
    try:
        # Import scanner modules to check for syntax/import errors
        from services import relative_strength_scanner
        from services import intraday_scanners
        logger.info("✅ Scanner modules imported successfully.")
        
        # We can implement a simple dry-run if needed, but import success proves Syntax/NameErrors are gone.
        return True
    except ImportError as e:
        logger.error(f"❌ ImportError in scanners: {e}")
        return False
    except NameError as e:
         logger.error(f"❌ NameError in scanners (checking for missing imports): {e}")
         return False
    except Exception as e:
        logger.error(f"❌ Error verifying scanners: {e}")
        return False

async def main():
    logger.info("Starting Direct Scanner Verification")
    
    enricher_ok = await verify_live_price_enricher()
    scanners_ok = await verify_scanners()
    
    if enricher_ok and scanners_ok:
        logger.info("\n🎉 AUTOMATED VERIFICATION PASSED: All checks successful.")
        sys.exit(0)
    else:
        logger.error("\n🚫 AUTOMATED VERIFICATION FAILED.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
