
import psycopg2
from config import settings

def purge_name_based_symbols():
    """Purge symbols that look like company names from stock_candles."""
    conn = psycopg2.connect(settings.SYNC_DATABASE_URL)
    cur = conn.cursor()
    
    # 1. Identity symbols with spaces or 'Ltd' or 'Limited'
    # Actually, tickers NEVER have spaces. Company names usually do.
    cur.execute("SELECT DISTINCT symbol FROM stock_candles WHERE symbol LIKE '% %' OR symbol LIKE '%Ltd%' OR symbol LIKE '%Limited%'")
    names = [row[0] for row in cur.fetchall()]
    
    print(f"Found {len(names)} name-based symbols to purge.")
    if not names:
        conn.close()
        return

    # 2. Delete them
    # Use symbol = ANY(%s) for efficiency
    cur.execute("DELETE FROM stock_candles WHERE symbol = ANY(%s)", (names,))
    deleted_count = cur.rowcount
    
    conn.commit()
    print(f"Successfully deleted {deleted_count} stale records for {len(names)} symbols.")
    
    # 3. Verify
    cur.execute("SELECT COUNT(*) FROM stock_candles")
    total = cur.fetchone()[0]
    print(f"Remaining records in stock_candles: {total}")
    
    conn.close()

if __name__ == "__main__":
    purge_name_based_symbols()
