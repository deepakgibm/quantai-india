from sqlalchemy import text
from database import engine

def check_all():
    con = engine.connect()
    try:
        # List all unique indices
        res = con.execute(text("""
            SELECT
                i.relname as index_name,
                a.attname as column_name
            FROM
                pg_class t,
                pg_class i,
                pg_index ix,
                pg_attribute a
            WHERE
                t.oid = ix.indrelid
                AND i.oid = ix.indexrelid
                AND a.attrelid = t.oid
                AND a.attnum = ANY(ix.indkey)
                AND t.relname = 'stock_candles'
                AND ix.indisunique = true;
        """))
        rows = res.fetchall()
        print("Unique Indexes on stock_candles:")
        indices = {}
        for r in rows:
            indices.setdefault(r[0], []).append(r[1])
        for name, cols in indices.items():
            print(f"- {name}: {', '.join(cols)}")
            
        # Get instrument_key for a sample symbol
        res = con.execute(text("SELECT symbol, instrument_key FROM stock_candles LIMIT 5"))
        print("\nSample instrument keys from stock_candles:")
        for r in res:
            print(f"- {r[0]}: {r[1]}")
            
    finally:
        con.close()

if __name__ == "__main__":
    check_all()
