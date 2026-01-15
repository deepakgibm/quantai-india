from sqlalchemy import text
from database import engine

def check_constraints():
    con = engine.connect()
    try:
        # Get all constraints for stock_candles
        query = text("""
            SELECT conname, pg_get_constraintdef(c.oid)
            FROM pg_constraint c
            JOIN pg_class t ON c.conrelid = t.oid
            WHERE t.relname = 'stock_candles';
        """)
        res = con.execute(query)
        rows = res.fetchall()
        print(f"Constraints on stock_candles:")
        for r in rows:
            print(f"- {r[0]}: {r[1]}")
    finally:
        con.close()

if __name__ == "__main__":
    check_constraints()
