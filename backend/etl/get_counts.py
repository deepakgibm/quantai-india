import psycopg2

DB_URL = "postgresql://postgres:admin@localhost:5432/quantai"

def get_counts():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM instrument_master")
    print(f"Total symbols in instrument_master: {cur.fetchone()[0]}")
    cur.execute("SELECT count(distinct instrument_id) FROM stock_candle_history")
    print(f"Total symbols with history: {cur.fetchone()[0]}")
    conn.close()

if __name__ == "__main__":
    get_counts()
