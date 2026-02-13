import psycopg2
import polars as pl
from datetime import datetime

DB_URL = "postgresql://postgres:admin@localhost:5432/quantai"

def check_incremental_status():
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        print("--- INCREMENTAL SYNC STATUS REPORT ---")
        
        # 1. Get active symbols
        cur.execute("SELECT symbol, instrument_id FROM instrument_master WHERE is_active = TRUE")
        symbols = cur.fetchall()
        
        timeframes = [1, 5, 15, 60, 1440]
        
        total_pending = 0
        symbols_with_pending = 0
        
        for symbol, inst_id in symbols:
            symbol_has_pending = False
            for tf in timeframes:
                # Get max TS in DB
                cur.execute("SELECT MAX(candle_ts) FROM stock_candle WHERE instrument_id = %s AND timeframe = %s", (inst_id, tf))
                db_max = cur.fetchone()[0]
                
                if not db_max:
                    continue
                
                # Get max TS in Parquet Audit
                cur.execute("SELECT MAX(max_ts_parquet) FROM parquet_load_audit WHERE symbol = %s AND timeframe = %s", (symbol, tf))
                parquet_max = cur.fetchone()[0]
                
                if not parquet_max or db_max > parquet_max:
                    diff = (db_max - (parquet_max if parquet_max else datetime(1970, 1, 1))).total_seconds() / 60
                    if diff > 1: # More than 1 minute diff
                        print(f"PENDING: {symbol} (TF: {tf}) | DB: {db_max} | Parquet: {parquet_max}")
                        total_pending += 1
                        symbol_has_pending = True
            
            if symbol_has_pending:
                symbols_with_pending += 1

        # 2. Check for failed batches
        cur.execute("SELECT count(*) FROM parquet_load_audit WHERE status != 'SUCCESS'")
        failed_count = cur.fetchone()[0]
        if failed_count > 0:
            print(f"⚠️ WARNING: {failed_count} batches have non-SUCCESS status in audit.")
        else:
            print("✅ No failed batches in audit.")

        # 3. Check for symbols with history but NO audit records
        cur.execute("""
            SELECT count(distinct instrument_id) FROM stock_candle
            WHERE instrument_id NOT IN (
                SELECT DISTINCT i.instrument_id 
                FROM parquet_load_audit a
                JOIN instrument_master i ON a.symbol = i.symbol
            )
        """)
        unmigrated_count = cur.fetchone()[0]
        if unmigrated_count > 0:
            print(f"❌ ERROR: {unmigrated_count} symbols have data in DB but ZERO records in Parquet audit.")
        else:
            print("✅ All symbols with DB data have at least one audit record.")

        if total_pending == 0 and failed_count == 0 and unmigrated_count == 0:
            print("\n🏁 FINAL VERDICT: Parquet Incremental ETL is 100% COMPLETE and Up-to-Date.")
        else:
            print(f"\n⚠️ FINAL VERDICT: Parquet Incremental ETL is INCOMPLETE ({total_pending} pending, {failed_count} failed, {unmigrated_count} unmigrated).")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_incremental_status()
