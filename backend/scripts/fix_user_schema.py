import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg2

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def fix_schema():
    # Load .env
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("[ERROR] DATABASE_URL not found in .env")
        return

    # Convert to psycopg2 format if needed
    # Usually: postgresql+asyncpg://user:pass@host:port/db
    # We need: postgresql://user:pass@host:port/db
    sync_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    
    # If using host.docker.internal on host, replace with localhost
    if "host.docker.internal" in sync_url:
        sync_url = sync_url.replace("host.docker.internal", "localhost")
        print(f"[INFO] Using localhost instead of host.docker.internal for host-level connection")

    print(f"[INFO] Connecting to: {sync_url.split('@')[1] if '@' in sync_url else 'unknown'}")
    
    try:
        conn = psycopg2.connect(sync_url)
        conn.autocommit = True
        cur = conn.cursor()
        
        # Add subscription_level if missing
        print("[INFO] Checking for subscription_level column...")
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name='subscription_level'
        """)
        
        if not cur.fetchone():
            print("[INFO] Adding subscription_level column to users table...")
            cur.execute("ALTER TABLE users ADD COLUMN subscription_level VARCHAR DEFAULT 'FREE'")
            print("[SUCCESS] Added subscription_level column.")
        else:
            print("[INFO] subscription_level column already exists.")

        # Check for other potential missing columns from models.py
        # failed_login_attempts, locked_until
        columns_to_check = [
            ("failed_login_attempts", "INTEGER DEFAULT 0"),
            ("locked_until", "TIMESTAMP NULL"),
            ("full_name", "VARCHAR NULL")
        ]
        
        for col_name, col_def in columns_to_check:
            cur.execute(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='users' AND column_name='{col_name}'
            """)
            if not cur.fetchone():
                print(f"[INFO] Adding {col_name} column to users table...")
                cur.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}")
                print(f"[SUCCESS] Added {col_name} column.")
            else:
                print(f"[INFO] {col_name} column already exists.")

        cur.close()
        conn.close()
        print("[DONE] Schema fix completed successfully.")
        
    except Exception as e:
        print(f"[ERROR] Failed to fix schema: {e}")

if __name__ == "__main__":
    fix_schema()
