import asyncio
import psycopg2
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).resolve().parents[2]
backend_dir = project_root / 'backend'
sys.path.append(str(backend_dir))
sys.path.append(str(project_root))

from backend.etl.backfill_history_2022 import get_last_candle_ts, get_connection
from backend.services.instrument_resolver import resolve_instrument_id

async def test_logic():
    symbol = '3MINDIA'
    instrument_id = resolve_instrument_id(symbol, exchange='NSE')
    print(f"Testing for {symbol} (ID: {instrument_id})")
    
    conn = get_connection()
    
    # 1D
    last_1d = get_last_candle_ts(conn, instrument_id, 1440)
    print(f"Last 1D TS: {last_1d}")
    if last_1d:
        actual_start = max(datetime(2022, 1, 1), last_1d + timedelta(days=1))
        print(f"Incremental 1D Start Date would be: {actual_start}")
    
    # 1m
    last_1m = get_last_candle_ts(conn, instrument_id, 1)
    print(f"Last 1m TS: {last_1m}")
    if last_1m:
        actual_start_1m = max(datetime(2022, 1, 1), last_1m + timedelta(minutes=1))
        print(f"Incremental 1m Start Date would be: {actual_start_1m}")
    
    conn.close()

if __name__ == "__main__":
    asyncio.run(test_logic())
