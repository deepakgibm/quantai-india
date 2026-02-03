import os
import psycopg2
from dotenv import load_dotenv
from pathlib import Path

def check_tables():
    env_path = Path("backend/.env")
    load_dotenv(env_path)
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not found")
        return
        
    sync_url = db_url.replace("postgresql+asyncpg://", "postgresql://").replace("host.docker.internal", "localhost")
    
    try:
        conn = psycopg2.connect(sync_url)
        cur = conn.cursor()
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
        tables = [t[0].lower() for t in cur.fetchall()]
        print(f"DEBUG: All tables in public schema: {tables}")
        
        if "ai_model_registry" in tables:
            print("RESULT: ai_model_registry EXISTS")
        else:
            print("RESULT: ai_model_registry MISSING")
                
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_tables()
