
import polars as pl
import psycopg2
import logging
from pathlib import Path

# Database Configuration
DB_URL = "postgresql://postgres:admin@localhost:5432/quantai"

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_connection():
    return psycopg2.connect(DB_URL)

def run_reconciliation():
    logger.info("Starting Reconciliation Report Generation...")
    
    conn = get_db_connection()
    
    # 1. Get Audit Summary from PG
    query_audit = """
        SELECT symbol, timeframe, SUM(row_count_pg) as pg_rows, SUM(row_count_parquet) as parquet_rows,
               MIN(min_ts_pg) as min_ts, MAX(max_ts_pg) as max_ts,
               COUNT(*) FILTER (WHERE status = 'SUCCESS') as successful_batches,
               COUNT(*) FILTER (WHERE status = 'FAILED') as failed_batches
        FROM parquet_load_audit
        GROUP BY symbol, timeframe
    """
    df_audit = pl.read_database(query_audit, conn)
    
    # 2. Get Real-time Database Stats (Original Source)
    query_source = """
        SELECT m.symbol, h.timeframe, COUNT(*) as source_rows,
               MIN(h.candle_ts) as source_min_ts, MAX(h.candle_ts) as source_max_ts
        FROM stock_candle_history h
        JOIN instrument_master m ON h.instrument_id = m.instrument_id
        GROUP BY m.symbol, h.timeframe
    """
    df_source = pl.read_database(query_source, conn)
    
    conn.close()
    
    # 3. Join and Compare
    # Only compare symbols that are in the audit (already attempted to migrate)
    df_report = df_source.join(df_audit, on=["symbol", "timeframe"], how="inner")
    
    # Calculate discrepancies
    df_report = df_report.with_columns([
        (pl.col("source_rows") - pl.col("parquet_rows").fill_null(0)).alias("row_diff"),
        (pl.col("parquet_rows").fill_null(0) / pl.col("source_rows") * 100).alias("completion_pct")
    ])
    
    # Filter for discrepancies or partial loads
    df_issues = df_report.filter((pl.col("row_diff") != 0) | (pl.col("failed_batches") > 0))
    
    print("\n--- RECONCILIATION SUMMARY ---")
    print(f"Total Batches Processed: {df_audit['successful_batches'].sum() + df_audit['failed_batches'].sum()}")
    print(f"Total Successful Batches: {df_audit['successful_batches'].sum()}")
    print(f"Total Failed Batches: {df_audit['failed_batches'].sum()}")
    print(f"Total Rows Migrated: {df_audit['parquet_rows'].sum()}")
    
    if len(df_issues) > 0:
        print("\n--- ISSUES DETECTED ---")
        print(df_issues.select(["symbol", "timeframe", "source_rows", "parquet_rows", "row_diff", "completion_pct", "failed_batches"]))
    else:
        print("\n✅ All migrated symbols match PostgreSQL perfectly.")
    
    # Save report
    df_report.write_csv("reconciliation_report.csv")
    logger.info("Reconciliation report saved to reconciliation_report.csv")

if __name__ == "__main__":
    run_reconciliation()
