import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from services.market_data_orchestrator import get_market_data_orchestrator

async def main():
    orchestrator = get_market_data_orchestrator()
    # Wait a bit for orchestrator to initialize if it's singleton
    await asyncio.sleep(1)
    price = await orchestrator.get_ltp("MANAPPURAM")
    status = orchestrator.get_status()
    print(f"SYMBOL: MANAPPURAM")
    print(f"LTP: {price}")
    print(f"ORCHESTRATOR_STATUS: {status}")

if __name__ == "__main__":
    asyncio.run(main())
