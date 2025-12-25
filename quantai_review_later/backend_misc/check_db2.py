import sqlite3
import os

print("Files in current dir:", os.listdir('.'))
print("DB exists:", os.path.exists('quantai.db'))

if os.path.exists('quantai.db'):
    conn = sqlite3.connect('quantai.db')
    cursor = conn.cursor()
    
    # List tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print("\nTables:", tables)
    
    # Check stock_data table
    for table_tuple in tables:
        table_name = table_tuple[0]
        print(f"\n=== Table: {table_name} ===")
        cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]")
        count = cursor.fetchone()[0]
        print(f"Row count: {count}")

    conn.close()
