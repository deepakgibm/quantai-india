
import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy import text

# Add project root to sys.path
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from backend.database import AsyncSessionLocal
    from backend.services.upstox_client import get_upstox_client
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parent))
    from database import AsyncSessionLocal
    from services.upstox_client import get_upstox_client

INSERT_SQL = """
INSERT INTO stock_data (symbol, timestamp, open, high, low, close, volume, interval, source)
VALUES (:symbol, :timestamp, :open, :high, :low, :close, :volume, :interval, :source)
ON CONFLICT(symbol, timestamp, interval) DO NOTHING;
"""

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

async def process_symbol_chunked(symbol, instrument_key, from_dt, to_dt, session):
    client = get_upstox_client()
    
    # Chunking logic: 15 days per chunk
    chunk_size = timedelta(days=15)
    current_from = from_dt
    all_dfs = []
    
    print(f"      Fetching 1min data (chunked)...")
    
    while current_from < to_dt:
        current_to = min(current_from + chunk_size, to_dt)
        
        # print(f"        Fetching {current_from.date()} to {current_to.date()}...", end=" ", flush=True)
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
                # print(f"✓ {len(df_chunk)} recs")
            else:
                pass
                # print("No data")
        except Exception as e:
            print(f"        Error fetching chunk {current_from.date()}: {e}")
        
        current_from = current_to
        # Small delay between chunks
        await asyncio.sleep(0.2)
        
    if not all_dfs:
        print("      No data found for any chunk.")
        return 0
        
    df_1min = pd.concat(all_dfs, ignore_index=True)
    # Deduplicate just in case
    df_1min.drop_duplicates(subset=['timestamp'], inplace=True)
    df_1min.sort_values('timestamp', inplace=True)
    
    print(f"      ✓ Total {len(df_1min):,} records fetched.")
    
    # 2. Process and Insert 1-minute data
    total_inserted = 0
    
    # Helper to insert dataframe
    async def insert_df(df, interval_name):
        count = 0
        
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
    print("NIFTY 200 DATA REPAIR LOADER (CHUNKED)")
    print("=" * 80)
    
    # Load missing symbols
    missing_file = "missing_symbols.txt"
    if not os.path.exists(missing_file):
        print(f"❌ {missing_file} not found. Run check_missing_symbols.py first.")
        return
        
    with open(missing_file, "r") as f:
        missing_symbols = [line.strip() for line in f if line.strip()]
        
    print(f"Found {len(missing_symbols)} missing symbols.")
    
    # Load all instruments to get keys
    json_file = "nifty200_instruments.json"
    if not os.path.exists(json_file):
        print(f"❌ {json_file} not found.")
        return
        
    with open(json_file, "r") as f:
        all_instruments = json.load(f)
        
    # Create a map of symbol -> key
    symbol_map = {item[0]: item[1] for item in all_instruments}
    
    # Filter instruments to process
    to_process = []
    for sym in missing_symbols:
        if sym in symbol_map:
            to_process.append((sym, symbol_map[sym]))
        else:
            print(f"⚠️ Warning: Symbol {sym} not found in instruments file.")
            
    print(f"Ready to process {len(to_process)} symbols.")
    print()
    
    from_dt = datetime(2022, 1, 1)
    to_dt = datetime.now()
    grand_total = 0
    
    # async with AsyncSessionLocal() as session: # Don't use a single session
    for i, (sym, key) in enumerate(to_process):
        print(f"[{i + 1}/{len(to_process)}] {sym}")
        
        try:
            # Create a fresh session for each symbol
            async with AsyncSessionLocal() as session:
                # URL encode the key because it contains |
                import urllib.parse
                encoded_key = urllib.parse.quote(key)
                
                inserted = await process_symbol_chunked(
                    symbol=sym,
                    instrument_key=encoded_key,
                    from_dt=from_dt,
                    to_dt=to_dt,
                    session=session
                )
            grand_total += inserted
            print(f"   Total inserted for {sym}: {inserted:,}")
        except Exception as e:
            print(f"❌ Error processing {sym}: {e}")
            with open("repair_errors.log", "a") as err_f:
                err_f.write(f"{datetime.now()} - {sym} - {e}\n")
        
        print()
        # Small delay to be nice to API
        await asyncio.sleep(0.5)

    print("=" * 80)
    print(f"✅ Repair complete. Grand Total Records: {grand_total:,}")
    print("=" * 80)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
