import psycopg2
from urllib.parse import urlparse

# Hardcoded from .env for testing
db_url = "postgresql://postgres:admin@localhost:5432/quantai"

print(f"Testing connection to: {db_url}")
parsed = urlparse(db_url)

try:
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        user=parsed.username,
        password=parsed.password,
        database=parsed.path.lstrip('/')
    )
    print("SUCCESS: Connected to PostgreSQL!")
    cursor = conn.cursor()
    
    # Check if stock_data exists
    cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'stock_data');")
    exists = cursor.fetchone()[0]
    print(f"Table 'stock_data' exists: {exists}")
    
    if exists:
        cursor.execute("SELECT count(*) FROM stock_data;")
        print(f"Total rows in stock_data: {cursor.fetchone()[0]}")
        
        cursor.execute("SELECT interval, count(*) FROM stock_data GROUP BY interval;")
        print(f"Intervals: {cursor.fetchall()}")
        
        cursor.execute("SELECT DISTINCT symbol FROM stock_data LIMIT 10;")
        print(f"Sample Symbols: {[r[0] for r in cursor.fetchall()]}")
        
    conn.close()
except Exception as e:
    print(f"FAILED: {e}")
