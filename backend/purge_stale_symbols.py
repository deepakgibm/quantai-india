
import psycopg2
from config import settings

def purge_name_based_symbols():
    """Purge symbols that look like company names from stock_candle via instrument_master."""
    conn = psycopg2.connect(settings.SYNC_DATABASE_URL)
    cur = conn.cursor()
    
    # 1. Identify instrument_ids with symbols that look like company names
    cur.execute("""
        SELECT instrument_id, symbol 
        FROM instrument_master 
        WHERE symbol LIKE '% %' OR symbol LIKE '%Ltd%' OR symbol LIKE '%Limited%'
    """)
    rows = cur.fetchall()
    ids = [row[0] for row in rows]
    names = [row[1] for row in rows]
    
    # FILTER: Keep indices that might have spaces (e.g., 'NIFTY 50')
    filtered_ids = []
    filtered_names = []
    for i, name in zip(ids, names):
        if name in ['NIFTY 50', 'BANK NIFTY', 'INDIA VIX', 'NIFTY 100', 'NIFTY NEXT 50']:
            continue
        filtered_ids.append(i)
        filtered_names.append(name)

    print(f"Found {len(filtered_names)} name-based symbols to purge: {filtered_names[:10]}...")
    if not filtered_ids:
        conn.close()
        return

    # 2. Delete from stock_candle
    cur.execute("DELETE FROM stock_candle WHERE instrument_id = ANY(%s)", (filtered_ids,))
    deleted_count = cur.rowcount
    
    conn.commit()
    print(f"Successfully deleted {deleted_count} stale records from stock_candle.")
    
    # 3. Verify
    cur.execute("SELECT COUNT(*) FROM stock_candle")
    total = cur.fetchone()[0]
    print(f"Remaining records in stock_candle: {total}")
    
    conn.close()

if __name__ == "__main__":
    purge_name_based_symbols()
