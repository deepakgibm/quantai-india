import asyncio
import io
import sys
from datetime import datetime
from pathlib import Path

# Force UTF-8 for stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add project root to path for imports
project_root = Path(__file__).resolve().parents[2]
backend_dir = project_root / 'backend'
sys.path.append(str(backend_dir))
sys.path.append(str(project_root))

from backend.etl.backfill_history_2022 import process_symbol, get_connection, get_last_candle_ts
from backend.services.upstox_client import get_upstox_client
from backend.services.instrument_resolver import resolve_instrument_id

async def trace_reliance():
    symbol = 'RELIANCE'
    inst_id = resolve_instrument_id(symbol, exchange='NSE')
    client = get_upstox_client()
    
    conn = get_connection()
    
    print(f"--- TRACE RELIANCE (ID: {inst_id}) ---")
    
    # Snapshot Before
    last_1d = get_last_candle_ts(conn, inst_id, 1440)
    last_1m = get_last_candle_ts(conn, inst_id, 1)
    print(f"BEFORE: Daily={last_1d}, 1m={last_1m}")
    
    # Run targeted ETL logic
    # I will also print some debug info from inside process_symbol if it allows
    # but for now let's just run it.
    await process_symbol(client, symbol)
    
    # Snapshot After
    last_1d_after = get_last_candle_ts(conn, inst_id, 1440)
    last_1m_after = get_last_candle_ts(conn, inst_id, 1)
    print(f"AFTER:  Daily={last_1d_after}, 1m={last_1m_after}")
    
    if last_1d == last_1d_after:
        print("!!! NO CHANGE DETECTED IN DB FOR DAILY")
    else:
        print(f"SUCCESS: Daily updated to {last_1d_after}")

    conn.close()
    await client.aclose()

if __name__ == "__main__":
    asyncio.run(trace_reliance())
