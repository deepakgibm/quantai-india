
import sys
import time
import psycopg2
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

def monitor_count():
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='admin',
            database='quantai'
        )
        cursor = conn.cursor()
        
        print("Monitoring stock_candle_history row count...")
        initial_count = 0
        
        for i in range(5):
            cursor.execute("SELECT count(*) FROM stock_candle_history;")
            count = cursor.fetchone()[0]
            print(f"Time {i}: Row count = {count}")
            if i > 0:
                print(f"  Increase: {count - initial_count}")
            initial_count = count
            time.sleep(5)

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error monitoring count: {e}")

if __name__ == "__main__":
    monitor_count()
