import psycopg2

def check_today_data():
    try:
        conn = psycopg2.connect('postgresql://postgres:admin@localhost:5432/quantai')
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM stock_candle_history WHERE candle_ts >= '2026-02-09'")
        count = cur.fetchone()[0]
        print(f"Total rows from Feb 9th, 2026: {count}")
        
        if count > 0:
            cur.execute("SELECT symbol FROM etl_job_status s JOIN instrument_master m ON s.symbol = m.symbol WHERE status = 'COMPLETED' AND EXISTS (SELECT 1 FROM stock_candle_history h WHERE h.instrument_id = m.instrument_id AND h.candle_ts >= '2026-02-09') LIMIT 5")
            symbols = [r[0] for r in cur.fetchall()]
            print(f"Sample symbols with today's data: {symbols}")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_today_data()
