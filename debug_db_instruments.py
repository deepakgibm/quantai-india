import psycopg2
import sys

def main():
    conn = psycopg2.connect("postgresql://postgres:admin@localhost:5432/quantai")
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM instrument_master WHERE is_active = TRUE AND exchange = 'NSE' AND series = 'EQ'")
    print(f"Matching Symbols Count (NSE, EQ, active): {cur.fetchone()[0]}")
    
    cur.execute("SELECT exchange, series, COUNT(*) FROM instrument_master GROUP BY exchange, series")
    print("Distribution by Exchange/Series:")
    for row in cur.fetchall():
        print(f"  {row[0]} / {row[1]}: {row[2]}")
        
    cur.execute("SELECT symbol, sector FROM instrument_master WHERE is_active = TRUE AND sector IS NOT NULL LIMIT 10")
    print("Sample Symbols with Sectors:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]}")
        
    conn.close()

if __name__ == "__main__":
    main()
