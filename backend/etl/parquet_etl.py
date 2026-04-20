
import os
import polars as pl
import psycopg2
from datetime import datetime
import argparse
import logging
import time
import random
from pathlib import Path

# Database Configuration
# Fallback to localhost if not provided in environment
DB_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:admin@localhost:5432/quantai").replace("+asyncpg", "")

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_connection():
    return psycopg2.connect(DB_URL)

def create_partition_path(base_path, symbol, timeframe, year, month):
    path = Path(base_path) / f"symbol={symbol}" / f"timeframe={timeframe}" / f"year={year}" / f"month={month:02d}"
    path.mkdir(parents=True, exist_ok=True)
    return path

def validate_parquet(file_path, pg_stats):
    """
    Validate the written parquet file against PostgreSQL stats.
    """
    try:
        df = pl.read_parquet(file_path)
        row_count = len(df)
        min_ts = df["candle_ts"].min()
        max_ts = df["candle_ts"].max()
        
        # Check counts
        if row_count != pg_stats['row_count']:
            return False, f"Row count mismatch: Parquet={row_count}, PG={pg_stats['row_count']}"
        
        # Check timestamp range (allowing some tolerance for formatting if needed, but should be exact)
        if min_ts != pg_stats['min_ts'] or max_ts != pg_stats['max_ts']:
            return False, f"Timestamp mismatch: Parquet=({min_ts}, {max_ts}), PG=({pg_stats['min_ts']}, {pg_stats['max_ts']})"
            
        return True, "Success"
    except Exception as e:
        return False, str(e)

def retry_with_backoff(retries=3, backoff_in_seconds=1):
    def decorator(func):
        def wrapper(*args, **kwargs):
            x = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                    if x == retries:
                        logger.error(f"Failed after {retries} retries: {e}")
                        raise
                    sleep = (backoff_in_seconds * 2 ** x + random.uniform(0, 1))
                    logger.warning(f"Database error {e}, retrying in {sleep:.2f} seconds...")
                    time.sleep(sleep)
                    x += 1
                except Exception as e:
                    logger.error(f"Unexpected error: {e}")
                    raise
        return wrapper
    return decorator

@retry_with_backoff(retries=5, backoff_in_seconds=2)
def process_batch(symbol, instrument_id, timeframe, year, month, base_path):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Check if already processed
    cur.execute("""
        SELECT status FROM parquet_load_audit 
        WHERE symbol = %s AND timeframe = %s AND year = %s AND month = %s
    """, (symbol, timeframe, year, month))
    result = cur.fetchone()
    if result and result[0] == 'SUCCESS':
        logger.info(f"Skipping already successful batch: {symbol}_{timeframe}_{year}_{month}")
        conn.close()
        return

    logger.info(f"Processing: {symbol} | TF: {timeframe} | {year}-{month:02d}")
    
    try:
        # 1. Mark as IN_PROGRESS
        if result:
            cur.execute("""
                UPDATE parquet_load_audit SET status = 'IN_PROGRESS', last_updated = CURRENT_TIMESTAMP
                WHERE symbol = %s AND timeframe = %s AND year = %s AND month = %s
            """, (symbol, timeframe, year, month))
        else:
            cur.execute("""
                INSERT INTO parquet_load_audit (symbol, timeframe, year, month, status)
                VALUES (%s, %s, %s, %s, 'IN_PROGRESS')
            """, (symbol, timeframe, year, month))
        conn.commit()

        # 2. Get stats from PG for this month
        cur.execute("""
            SELECT COUNT(*), MIN(candle_ts), MAX(candle_ts)
            FROM stock_candle
            WHERE instrument_id = %s AND timeframe = %s 
              AND EXTRACT(YEAR FROM candle_ts) = %s 
              AND EXTRACT(MONTH FROM candle_ts) = %s
        """, (instrument_id, timeframe, year, month))
        row_count, min_ts, max_ts = cur.fetchone()
        
        if row_count == 0:
            logger.info(f"No data for {symbol}_{timeframe}_{year}_{month}")
            cur.execute("""
                UPDATE parquet_load_audit 
                SET status = 'SUCCESS', row_count_pg = 0, row_count_parquet = 0
                WHERE symbol = %s AND timeframe = %s AND year = %s AND month = %s
            """, (symbol, timeframe, year, month))
            conn.commit()
            conn.close()
            return

        pg_stats = {'row_count': row_count, 'min_ts': min_ts, 'max_ts': max_ts}

        # 3. Extract data using Polars
        query = f"""
            SELECT instrument_id, timeframe, candle_ts, open, high, low, close, volume
            FROM stock_candle
            WHERE instrument_id = {instrument_id} AND timeframe = {timeframe}
              AND EXTRACT(YEAR FROM candle_ts) = {year} 
              AND EXTRACT(MONTH FROM candle_ts) = {month}
        """
        df = pl.read_database(query, conn)
        
        # Standardize Types: LakeDAL expect Float64 for math operations
        decimal_cols = [col for col in ["open", "high", "low", "close"] if col in df.columns]
        if decimal_cols:
            df = df.with_columns([pl.col(c).cast(pl.Float64) for c in decimal_cols])

        # 4. Write to Parquet (Temporary file)
        partition_dir = create_partition_path(base_path, symbol, timeframe, year, month)
        file_name = f"data_{year}_{month:02d}.parquet"
        temp_file = partition_dir / f"{file_name}.tmp"
        final_file = partition_dir / file_name
        
        # Ensure schema compliance and compression: STANDARD ZSTD
        df.write_parquet(temp_file, compression="zstd")
        
        # 5. Validate
        is_valid, message = validate_parquet(temp_file, pg_stats)
        
        if is_valid:
            os.rename(temp_file, final_file)
            cur.execute("""
                UPDATE parquet_load_audit 
                SET status = 'SUCCESS', row_count_pg = %s, row_count_parquet = %s,
                    min_ts_pg = %s, max_ts_pg = %s, min_ts_parquet = %s, max_ts_parquet = %s,
                    last_updated = CURRENT_TIMESTAMP
                WHERE symbol = %s AND timeframe = %s AND year = %s AND month = %s
            """, (row_count, row_count, min_ts, max_ts, min_ts, max_ts, symbol, timeframe, year, month))
            logger.info(f"✅ Batch Success: {symbol}_{timeframe}_{year}_{month}")
        else:
            cur.execute("""
                UPDATE parquet_load_audit 
                SET status = 'FAILED', error_message = %s, last_updated = CURRENT_TIMESTAMP
                WHERE symbol = %s AND timeframe = %s AND year = %s AND month = %s
            """, (message, symbol, timeframe, year, month))
            logger.error(f"❌ Batch Validation Failed: {symbol}_{timeframe}_{year}_{month} | {message}")

        conn.commit()
    except Exception as e:
        logger.error(f"💥 Critical Error in Batch {symbol}_{timeframe}_{year}_{month}: {e}")
        conn.rollback()
        cur.execute("""
            UPDATE parquet_load_audit 
            SET status = 'FAILED', error_message = %s, last_updated = CURRENT_TIMESTAMP
            WHERE symbol = %s AND timeframe = %s AND year = %s AND month = %s
        """, (str(e), symbol, timeframe, year, month))
        conn.commit()
    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser(description="PostgreSQL to Parquet Migration Engine")
    parser.add_argument("--symbol", help="Target symbol (optional)")
    parser.add_argument("--start-at", help="Start processing from this symbol (alphabetically)")
    parser.add_argument("--base-path", default="data/parquet", help="Base path for parquet files")
    args = parser.parse_args()

    conn = get_db_connection()
    logger.info("Discovering symbol/timeframe ranges (optimized query)...")
    
    # 1. Get min/max ts per symbol and timeframe - much faster than SELECT DISTINCT on every row
    query_discovery = """
        SELECT m.symbol, h.instrument_id, h.timeframe, 
               MIN(h.candle_ts) as min_ts, MAX(h.candle_ts) as max_ts
        FROM stock_candle h
        JOIN instrument_master m ON h.instrument_id = m.instrument_id
        GROUP BY m.symbol, h.instrument_id, h.timeframe
    """
    df_ranges = pl.read_database(query_discovery, conn)
    conn.close()

    if args.symbol:
        df_ranges = df_ranges.filter(pl.col("symbol") == args.symbol)
        logger.info(f"Targeting specific symbol: {args.symbol}")
        
    if args.start_at:
        df_ranges = df_ranges.filter(pl.col("symbol") >= args.start_at)
        logger.info(f"Starting at symbol: {args.start_at}")

    logger.info(f"Found {len(df_ranges)} symbol/timeframe groups. Calculating month batches...")

    # 2. Expand ranges into (year, month) batches in Python
    batch_list = []
    for row in df_ranges.to_dicts():
        start_date = row['min_ts']
        end_date = row['max_ts']
        
        # Iterate through months from start_date to end_date
        current = datetime(start_date.year, start_date.month, 1)
        while current <= end_date:
            batch_list.append({
                'symbol': row['symbol'],
                'instrument_id': row['instrument_id'],
                'timeframe': row['timeframe'],
                'year': current.year,
                'month': current.month
            })
            # Move to next month
            if current.month == 12:
                current = datetime(current.year + 1, 1, 1)
            else:
                current = datetime(current.year, current.month + 1, 1)

    logger.info(f"Generated {len(batch_list)} potential month batches to process.")

    for batch in batch_list:
        process_batch(
            batch['symbol'], 
            batch['instrument_id'], 
            batch['timeframe'], 
            batch['year'], 
            batch['month'], 
            args.base_path
        )

if __name__ == "__main__":
    main()
