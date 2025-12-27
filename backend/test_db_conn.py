import psycopg2
from urllib.parse import urlparse
import os
from dotenv import load_dotenv

env_path = r"c:\Users\Deepak Kumar\Downloads\quantai-india\backend\.env"
load_dotenv(env_path)

db_url = os.getenv("DATABASE_URL")
print(f"Testing connection to: {db_url}")

if not db_url:
    print("DATABASE_URL not found in .env")
    exit(1)

if '+asyncpg' in db_url:
    db_url = db_url.replace('+asyncpg', '')

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
    cursor.execute("SELECT version();")
    print(f"DB Version: {cursor.fetchone()[0]}")
    
    # Check if stock_data exists
    cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'stock_data');")
    exists = cursor.fetchone()[0]
    print(f"Table 'stock_data' exists: {exists}")
    
    if exists:
        cursor.execute("SELECT count(*) FROM stock_data;")
        print(f"Rows in stock_data: {cursor.fetchone()[0]}")
        
        cursor.execute("SELECT DISTINCT symbol FROM stock_data LIMIT 5;")
        print(f"Sample symbols: {[r[0] for r in cursor.fetchall()]}")
        
    conn.close()
except Exception as e:
    print(f"FAILED: {e}")
