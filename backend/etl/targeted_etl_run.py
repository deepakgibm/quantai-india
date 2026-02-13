import asyncio
from datetime import datetime
from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).resolve().parents[2]
backend_dir = project_root / 'backend'
sys.path.append(str(backend_dir))
sys.path.append(str(project_root))

from backend.etl.backfill_history_2022 import process_symbol, get_connection
from backend.services.upstox_client import get_upstox_client

async def targeted():
    symbols = ['RELIANCE', 'NIFTY 50', 'TCS']
    client = get_upstox_client()
    
    conn = get_connection()
    cur = conn.cursor()
    # Reset status for these symbols
    cur.execute("UPDATE etl_job_status SET status = 'PENDING' WHERE symbol = ANY(%s) AND job_name = 'backfill_2022'", (symbols,))
    conn.commit()
    conn.close()
    
    for symbol in symbols:
        print(f"\n--- TARGETED START: {symbol} ---")
        await process_symbol(client, symbol)
        print(f"--- TARGETED END: {symbol} ---")

    await client.aclose()

if __name__ == "__main__":
    asyncio.run(targeted())
