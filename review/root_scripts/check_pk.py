import os
import sys
from sqlalchemy import create_engine, text

sys.path.append(os.path.join(os.getcwd(), 'backend'))
from config import settings

def check_pk():
    print(f"Checking PK: {settings.SYNC_DATABASE_URL}")
    try:
        engine = create_engine(settings.SYNC_DATABASE_URL)
        with engine.connect() as conn:
            # Postgres specific query for PK
            res = conn.execute(text("""
                SELECT a.attname
                FROM   pg_index i
                JOIN   pg_attribute a ON a.attrelid = i.indrelid
                                     AND a.attnum = ANY(i.indkey)
                WHERE  i.indrelid = 'stock_master'::regclass
                AND    i.indisprimary;
            """))
            pk = [r[0] for r in res.fetchall()]
            print(f"Primary Key columns: {pk}")
            
            # Check if updated_at is there
            cols = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'stock_master'"))
            print("Columns Found:")
            for r in cols:
                print(f"- {r[0]}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_pk()
