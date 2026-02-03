
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, inspect
from config import settings
import time

def check_indexes():
    print("--- Connecting to DB ---")
    engine = create_engine(settings.SYNC_DATABASE_URL)
    inspector = inspect(engine)
    
    table_name = "nifty100_daily"
    print(f"--- Inspecting table: {table_name} ---")
    
    try:
        indexes = inspector.get_indexes(table_name)
        if not indexes:
            print("❌ NO INDEXES FOUND!")
        else:
            print(f"✅ Found {len(indexes)} indexes:")
            for idx in indexes:
                print(f"   - {idx['name']}: {idx['column_names']} (Unique: {idx['unique']})")
    except Exception as e:
        print(f"❌ Error inspecting indexes: {e}")
        return

    print("\n--- Running EXPLAIN ANALYZE on Bulk Query ---")
    # Simulate the query used in BreakoutDetector
    # "timestamp >= cutoff"
    cutoff_date = "2024-01-01"
    
    query = text("""
        EXPLAIN ANALYZE 
        SELECT symbol, timestamp, open, high, low, close, volume 
        FROM nifty100_daily 
        WHERE timestamp >= :cutoff 
        ORDER BY symbol, timestamp ASC
    """)
    
    try:
        with engine.connect() as conn:
            start_time = time.time()
            result = conn.execute(query, {"cutoff": cutoff_date})
            print(f"Query executed in {time.time() - start_time:.4f}s")
            
            print("\n--- QUERY PLAN ---")
            for row in result:
                print(row[0])
                
    except Exception as e:
        print(f"❌ Error executing EXPLAIN: {e}")

if __name__ == "__main__":
    with open("check_output.log", "w") as f:
        sys.stdout = f
        check_indexes()
        sys.stdout = sys.__stdout__
