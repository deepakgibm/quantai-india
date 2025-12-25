"""
Raw SQL Loader for Nifty 200 multi‑interval data (Upstox)
Loads 1min data from Jan 2022 to today, and resamples to 3min, 5min, 15min, 30min.
Supports resumable execution via checkpoint file.
"""
import asyncio
import json
import os
import sys
from pathlib import Path
import pandas as pd

# Add project root to sys.path
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

# Import existing async engine and session maker
from backend.database import AsyncSessionLocal
# Upstox client
from backend.services.upstox_client import get_upstox_client

INSERT_SQL = """
INSERT INTO stock_data (symbol, timestamp, open, high, low, close, volume, interval, source)
VALUES (:symbol, :timestamp, :open, :high, :low, :close, :volume, :interval, :source)
ON CONFLICT(symbol, timestamp, interval) DO NOTHING;
"""

CHECKPOINT_FILE = "loader_checkpoint.json"

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, "r") as f:
                data = json.load(f)
                # Handle old checkpoint format
                if "last_interval_index" in data:
                    return {"last_symbol_index": data["last_symbol_index"]}
                return data
        except Exception as e:
            print(f"⚠️ Could not read checkpoint file: {e}")
    return {"last_symbol_index": -1}

def save_checkpoint(symbol_idx):
    try:
        with open(CHECKPOINT_FILE, "w") as f:
            json.dump({"last_symbol_index": symbol_idx}, f)
    except Exception as e:
        print(f"⚠️ Could not save checkpoint: {e}")

def resample_data(df, interval_minutes):
    """Resample 1-minute data to higher timeframes"""
    if df.empty:
        return pd.DataFrame()
    
    # Ensure timestamp is datetime and set as index
    df = df.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        df.set_index('timestamp', inplace=True)
    
    # Define aggregation rules
    agg_rules = {
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum',
        'symbol': 'first' # Keep symbol
    }
    
    # Resample
    rule = f'{interval_minutes}T'
    resampled = df.resample(rule).agg(agg_rules)
    
    # Drop NaN rows (intervals with no data)
    resampled.dropna(inplace=True)
    
    # Reset index to make timestamp a column again
    resampled.reset_index(inplace=True)
    
    return resampled

async def process_symbol(symbol, instrument_key, from_dt, to_dt, session: AsyncSession):
    client = get_upstox_client()
    
    # Chunking logic: 30 days per chunk (safe limit)
    chunk_size = timedelta(days=30)
    current_from = from_dt
    all_dfs = []
    
    print(f"      Fetching 1min data (chunked)...", end=" ", flush=True)
    
    while current_from < to_dt:
        current_to = min(current_from + chunk_size, to_dt)
        
        try:
            df_chunk = await client.get_historical_data(
                symbol=symbol,
                instrument_key=instrument_key,
                from_date=current_from,
                to_date=current_to,
                interval="1minute",
            )
            if not df_chunk.empty:
                all_dfs.append(df_chunk)
                print(".", end="", flush=True)
            else:
                print("x", end="", flush=True)
        except Exception as e:
            print(f"!", end="", flush=True)
            # print(f"        Error fetching chunk {current_from.date()}: {e}")
        
        current_from = current_to
        # Small delay between chunks
        await asyncio.sleep(0.1)
        
    if not all_dfs:
        print(" No data found.")
        return 0
        
    df_1min = pd.concat(all_dfs, ignore_index=True)
    # Deduplicate just in case
    df_1min.drop_duplicates(subset=['timestamp'], inplace=True)
    df_1min.sort_values('timestamp', inplace=True)
    
    print(f" ✓ {len(df_1min):,} records")
    
    # 2. Process and Insert 1-minute data
    total_inserted = 0
    
    # Helper to insert dataframe
    async def insert_df(df, interval_name):
        count = 0
        # Batch insert for speed
        data_to_insert = []
        
        for _, row in df.iterrows():
            data_to_insert.append({
                "symbol": symbol,
                "timestamp": row["timestamp"].to_pydatetime(),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": int(row["volume"]),
                "interval": interval_name,
                "source": "upstox",
            })
            
        if data_to_insert:
            # Batch insert in chunks of 1000
            batch_size = 1000
            for i in range(0, len(data_to_insert), batch_size):
                batch = data_to_insert[i:i+batch_size]
                await session.execute(text(INSERT_SQL), batch)
                count += len(batch)
                
        return count

    # Insert 1min
    c = await insert_df(df_1min, "1min")
    total_inserted += c
    
    # 3. Resample and Insert others
    intervals_map = {
        "3min": 3,
        "5min": 5,
        "15min": 15,
        "30min": 30
    }
    
    for name, minutes in intervals_map.items():
        print(f"      Resampling to {name}...", end=" ", flush=True)
        df_resampled = resample_data(df_1min, minutes)
        if not df_resampled.empty:
            c = await insert_df(df_resampled, name)
            total_inserted += c
            print(f"✓ {c:,} records")
        else:
            print("Empty")

    await session.commit()
    return total_inserted

async def main():
    print("=" * 80)
    print("NIFTY 200 MULTI‑INTERVAL LOADER (FETCH 1MIN & RESAMPLE)")
    print("=" * 80)
    print("Loading 1min data from Jan 2022 and generating 3, 5, 15, 30min intervals")
    
    # Load symbols from JSON
    json_file = str(Path(__file__).resolve().parent / "nifty200_instruments.json")
    if not os.path.exists(json_file):
        print(f"❌ {json_file} not found. Run fetch_instrument_keys.py first.")
        return
        
    with open(json_file, "r") as f:
        symbols = json.load(f)
        
    print(f"Loaded {len(symbols)} Nifty 200 symbols from {json_file}")

    checkpoint = load_checkpoint()
    start_symbol_idx = checkpoint.get("last_symbol_index", -1)
    current_symbol_idx = start_symbol_idx + 1
        
    print(f"🔄 Resuming from Symbol Index: {current_symbol_idx}")
    print()
    
    if current_symbol_idx >= len(symbols):
        print("✅ All symbols already processed!")
        return

    from_dt = datetime(2022, 1, 1)
    to_dt = datetime.now()
    grand_total = 0
    
    async with AsyncSessionLocal() as session:
        for s_idx in range(current_symbol_idx, len(symbols)):
            sym, key = symbols[s_idx]
            print(f"[{s_idx + 1}/{len(symbols)}] {sym}")
            
            try:
                inserted = await process_symbol(
                    symbol=sym,
                    instrument_key=key,
                    from_dt=from_dt,
                    to_dt=to_dt,
                    session=session
                )
                grand_total += inserted
                print(f"   Total inserted for {sym}: {inserted:,}")
            except Exception as e:
                print(f"❌ Error processing {sym}: {e}")
                with open("loader_errors.log", "a") as err_f:
                    err_f.write(f"{datetime.now()} - {sym} - {e}\n")
            
            # Save checkpoint regardless of success/failure to move forward
            # (If failed, we skip it next time. If we want to retry failed ones, we need smarter logic,
            # but for now, let's skip to ensure we get the rest)
            save_checkpoint(s_idx)
            
            print()
            await asyncio.sleep(0.5)

    print("=" * 80)
    print(f"✅ Load complete. Grand Total Records: {grand_total:,}")
    print("=" * 80)

if __name__ == "__main__":
    try:
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user. Progress saved.")
