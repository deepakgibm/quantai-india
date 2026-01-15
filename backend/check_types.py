from database import SessionLocal
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_schema():
    session = SessionLocal()
    try:
        tables = ['stock_master', 'stock_candles']
        for table in tables:
            print(f"\n--- {table} Columns & Types ---")
            query = text(f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = '{table}'
                ORDER BY ordinal_position;
            """)
            res = session.execute(query)
            for row in res:
                print(f"{row[0]}: {row[1]}")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == '__main__':
    check_schema()
