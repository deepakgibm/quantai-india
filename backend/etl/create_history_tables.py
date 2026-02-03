
import os
import sys
import psycopg2
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

from backend.config import settings

def get_connection():
    # Use sync connection URL
    return psycopg2.connect(
        host='localhost',
        port=5432,
        user='postgres',
        password='admin',
        database='quantai'
    )

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        print("Creating stock_candle_history table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_candle_history (
                instrument_id BIGINT NOT NULL,
                timeframe SMALLINT NOT NULL,
                candle_ts TIMESTAMP NOT NULL,
                open NUMERIC(12, 4),
                high NUMERIC(12, 4),
                low NUMERIC(12, 4),
                close NUMERIC(12, 4),
                volume BIGINT,
                PRIMARY KEY (instrument_id, timeframe, candle_ts),
                CONSTRAINT fk_instrument_history 
                    FOREIGN KEY(instrument_id) 
                    REFERENCES instrument_master(instrument_id)
            );
        """)
        
        print("Creating etl_job_status table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS etl_job_status (
                id Serial PRIMARY KEY,
                job_name VARCHAR(50) NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                status VARCHAR(20) DEFAULT 'PENDING',
                last_updated Timestamp DEFAULT CURRENT_TIMESTAMP,
                error_msg TEXT,
                CONSTRAINT uq_job_symbol UNIQUE (job_name, symbol)
            );
        """)
        
        # Create Index for fast lookup
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_stock_candle_history_lookup 
            ON stock_candle_history (instrument_id, timeframe, candle_ts);
        """)
        
        conn.commit()
        print("Tables created successfully.")
        
    except Exception as e:
        conn.rollback()
        print(f"Error creating tables: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    create_tables()
