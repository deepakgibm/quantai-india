
import os
import polars as pl
import psycopg2
import argparse
import logging
from pathlib import Path

# Database Configuration
# Fallback to localhost if not provided in environment
DB_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:admin@localhost:5432/quantai").replace("+asyncpg", "")

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_connection():
    # Handle both URI and individual components if needed, 
    # but psycopg2.connect accepts URLs
    return psycopg2.connect(DB_URL)

def create_partition_path(base_path, symbol, timeframe, year, month):
    # Standardize partitioning to symbol={S}/timeframe={T}
    # LakeDAL uses the same Hive-style directory structure
    path = Path(base_path) / f"symbol={symbol}" / f"timeframe={timeframe}" / f"year={year}" / f"month={month:02d}"
    path.mkdir(parents=True, exist_ok=True)
    return path

def sync_incremental(symbol, instrument_id, timeframe, base_path):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 1. Read watermark: last_loaded_timestamp from audit table
    cur.execute("""
        SELECT MAX(max_ts_parquet) FROM parquet_load_audit 
        WHERE symbol = %s AND timeframe = %s AND status = 'SUCCESS'
    """, (symbol, timeframe))
    last_loaded_timestamp = cur.fetchone()[0]
    
    if not last_loaded_timestamp:
        logger.warning(f"No watermark found for {symbol}_{timeframe}. Full load should run first.")
        conn.close()
        return

    logger.info(f"Syncing {symbol} (TF: {timeframe}) from watermark: {last_loaded_timestamp}")

    # 2. Query PG for new rows
    query_new = f"""
        SELECT instrument_id, timeframe, candle_ts, open, high, low, close, volume
        FROM stock_candle
        WHERE instrument_id = {instrument_id} AND timeframe = {timeframe}
          AND candle_ts > '{last_loaded_timestamp}'
        ORDER BY candle_ts ASC
    """
    df_new = pl.read_database(query_new, conn)
    
    if len(df_new) == 0:
        logger.info(f"No new rows for {symbol}_{timeframe}")
        conn.close()
        return

    logger.info(f"Found {len(df_new)} new rows for {symbol}_{timeframe}")

    # Standardize Types: LakeDAL expect Float64 for math operations
    # Decimal often causes issues in vectorized calculations
    decimal_cols = [col for col in ["open", "high", "low", "close"] if col in df_new.columns]
    if decimal_cols:
        df_new = df_new.with_columns([pl.col(c).cast(pl.Float64) for c in decimal_cols])

    # 3. Group by Year/Month and append to Parquet
    df_new = df_new.with_columns([
        pl.col("candle_ts").dt.year().alias("year"),
        pl.col("candle_ts").dt.month().alias("month")
    ])
    
    partitions = df_new.group_by(["year", "month"]).agg(pl.all())
    
    for part in partitions.to_dicts():
        year = part['year']
        month = part['month']
        df_part = df_new.filter((pl.col("year") == year) & (pl.col("month") == month))
        df_part = df_part.drop(["year", "month"]) # Remove helper columns
        
        partition_dir = create_partition_path(base_path, symbol, timeframe, year, month)
        file_name = f"data_{year}_{month:02d}.parquet"
        final_file = partition_dir / file_name
        
        # Load existing if present, else create new
        if final_file.exists():
            df_existing = pl.read_parquet(final_file)
            # Standardize existing schema if it was old (ensuring consistency)
            if any(isinstance(df_existing.schema[c], pl.Decimal) for c in decimal_cols if c in df_existing.columns):
                df_existing = df_existing.with_columns([pl.col(c).cast(pl.Float64) for c in decimal_cols])
            
            # Idempotency: only append rows that are AFTER existing max
            max_existing = df_existing["candle_ts"].max()
            df_to_append = df_part.filter(pl.col("candle_ts") > max_existing)
            
            if len(df_to_append) > 0:
                df_combined = pl.concat([df_existing, df_to_append]).sort("candle_ts")
                temp_file = final_file.with_suffix(".tmp")
                # STANDARD COMPRESSION: ZSTD (matches LakeDAL)
                df_combined.write_parquet(temp_file, compression="zstd")
                os.replace(temp_file, final_file)
                logger.info(f"Appended {len(df_to_append)} rows to {final_file}")
            else:
                logger.info(f"All new rows already present in {final_file} (likely re-run)")
        else:
            # New partition: Use ZSTD
            df_part.write_parquet(final_file, compression="zstd")
            logger.info(f"Created new partition: {final_file}")

        # 4. Update Audit Watermark
        new_max_ts = df_part["candle_ts"].max()
        new_row_count = len(df_part)
        
        cur.execute("""
            INSERT INTO parquet_load_audit (symbol, timeframe, year, month, status, row_count_pg, row_count_parquet, min_ts_pg, max_ts_pg, min_ts_parquet, max_ts_parquet)
            VALUES (%s, %s, %s, %s, 'SUCCESS', %s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol, timeframe, year, month) DO UPDATE SET
                status = 'SUCCESS',
                row_count_pg = parquet_load_audit.row_count_pg + EXCLUDED.row_count_pg,
                row_count_parquet = parquet_load_audit.row_count_parquet + EXCLUDED.row_count_parquet,
                max_ts_pg = GREATEST(parquet_load_audit.max_ts_pg, EXCLUDED.max_ts_pg),
                max_ts_parquet = GREATEST(parquet_load_audit.max_ts_parquet, EXCLUDED.max_ts_parquet),
                last_updated = CURRENT_TIMESTAMP
        """, (symbol, timeframe, year, month, new_row_count, new_row_count, df_part["candle_ts"].min(), new_max_ts, df_part["candle_ts"].min(), new_max_ts))

    conn.commit()
    conn.close()

def main():
    parser = argparse.ArgumentParser(description="Incremental PostgreSQL -> Parquet Synchronizer")
    parser.add_argument("--symbol", help="Optional: filter by symbol")
    parser.add_argument("--base-path", default="data/parquet", help="Base directory for Parquet warehouse")
    args = parser.parse_args()

    conn = get_db_connection()
    # Get active symbols from instrument_master
    query = "SELECT symbol, instrument_id FROM instrument_master WHERE is_active = TRUE"
    df_symbols = pl.read_database(query, conn)
    
    # Get timeframes to sync (production standard)
    timeframes = [1, 3, 5, 15, 30, 60, 1440]
    
    for sym_row in df_symbols.to_dicts():
        if args.symbol and sym_row['symbol'] != args.symbol:
            continue
            
        for tf in timeframes:
            try:
                sync_incremental(sym_row['symbol'], sym_row['instrument_id'], tf, args.base_path)
            except Exception as e:
                logger.error(f"Failed incremental sync for {sym_row['symbol']} (TF: {tf}): {e}")

if __name__ == "__main__":
    # Ensure conflict handling works (requires unique constraint)
    # We should add a unique constraint to proxy (symbol, tf, year, month)
    # python -c "import psycopg2; conn=psycopg2.connect('...'); cur=conn.cursor(); cur.execute('ALTER TABLE parquet_load_audit ADD CONSTRAINT uq_batch UNIQUE (symbol, timeframe, year, month)'); conn.commit(); conn.close()"
    main()
