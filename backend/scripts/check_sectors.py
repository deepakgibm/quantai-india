
import sys
import psycopg2
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))


def check_sectors():
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='admin',
            database='quantai'
        )
        cursor = conn.cursor()
        
        print("Checking instrument_master for sectors...")
        cursor.execute("SELECT count(*) FROM instrument_master")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT count(*) FROM instrument_master WHERE sector IS NOT NULL")
        with_sector = cursor.fetchone()[0]
        
        print(f"Total Instruments: {total}")
        print(f"With Sector Info: {with_sector}")
        
        if with_sector > 0:
            cursor.execute("SELECT sector, count(*) FROM instrument_master GROUP BY sector ORDER BY count(*) DESC LIMIT 5")
            print("\nTop 5 Sectors:")
            for row in cursor.fetchall():
                print(f"  {row[0]}: {row[1]}")
        else:
            print("\nWARNING: No sector information found!")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_sectors()
