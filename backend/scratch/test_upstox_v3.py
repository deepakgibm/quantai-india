import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path('backend/.env'))

def fetch_token():
    db_url = os.getenv('DATABASE_URL').replace('+asyncpg', '')
    engine = create_engine(db_url)
    with engine.connect() as conn:
        try:
            res = conn.execute(text("SELECT encrypted_token FROM auth_tokens WHERE token_type = 'ANALYTICS'"))
            row = res.fetchone()
            print(f"DB Token (Encrypted): {row[0][:50]}..." if row else "No DB Token")
        except Exception as e:
            print(f"Error fetching token: {e}")
            
    print(f"Env Token: {os.getenv('UPSTOX_ACCESS_TOKEN')[:50]}...")

fetch_token()
