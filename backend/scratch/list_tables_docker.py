import os
import psycopg2
import asyncio
from sqlalchemy import text
from database import SessionLocal

def list_db_info():
    print("Connecting using SessionLocal...")
    try:
        with SessionLocal() as session:
            # Query all table names in public schema
            result = session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema='public' 
                ORDER BY table_name;
            """))
            tables = [r[0] for r in result.fetchall()]
            print(f"Found {len(tables)} tables:")
            
            for table in tables:
                cnt_res = session.execute(text(f"SELECT COUNT(*) FROM {table};"))
                count = cnt_res.scalar()
                print(f"  - {table}: {count} rows")
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    list_db_info()
