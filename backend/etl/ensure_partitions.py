import os
import sys
import psycopg2
from dotenv import load_dotenv
from pathlib import Path

# Load env
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:admin@localhost:5432/quantai")
SYNC_DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

def create_partitions():
    conn = psycopg2.connect(SYNC_DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()
    
    years = [2024, 2025, 2026]
    months = range(1, 13)
    
    print("Ensuring partitions exist for:", years)
    
    for year in years:
        for month in months:
            start_date = f"{year}-{month:02d}-01"
            if month == 12:
                end_date = f"{year+1}-01-01"
            else:
                end_date = f"{year}-{month+1:02d}-01"
            
            table_name = f"stock_candle_{year}_{month:02d}"
            
            sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name}
            PARTITION OF stock_candle
            FOR VALUES FROM ('{start_date}') TO ('{end_date}');
            """
            
            try:
                cur.execute(sql)
                print(f"Verified partition: {table_name}")
            except Exception as e:
                print(f"Error creating partition {table_name}: {e}")
                
    conn.close()

if __name__ == "__main__":
    create_partitions()
