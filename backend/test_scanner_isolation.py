
import asyncio
import logging

# Mock logging to see output
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_scanner():
    try:
        from services.momentum_scanner import MomentumScanner
        print("Initializing MomentumScanner...")
        scanner = MomentumScanner()
        
        print("Running scan_all(limit=5)...")
        results = scanner.scan_all(limit=5)
        
        print(f"Scan results count: {len(results)}")
        if results:
            print(f"First result: {results[0]['symbol']} - {results[0]['bucket']}")
        else:
            print("No results found.")
            
    except Exception as e:
        print(f"CRASH during scanner test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_scanner())
