import os
import psycopg2
from dotenv import load_dotenv
from pathlib import Path

def init_ai_schema():
    env_path = Path("backend/.env")
    load_dotenv(env_path)
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not found")
        return
        
    sync_url = db_url.replace("postgresql+asyncpg://", "postgresql://").replace("host.docker.internal", "localhost")
    
    try:
        conn = psycopg2.connect(sync_url)
        conn.autocommit = True
        cur = conn.cursor()
        
        print("Creating table ai_model_registry...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ai_model_registry (
                id SERIAL PRIMARY KEY,
                model_id VARCHAR(50) NOT NULL,
                version VARCHAR(20) NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                timeframe VARCHAR(10) NOT NULL,
                status VARCHAR(20) DEFAULT 'READY',
                is_pro BOOLEAN DEFAULT FALSE,
                artifact_path VARCHAR(255),
                mse FLOAT,
                mae FLOAT,
                r2_score FLOAT,
                custom_metrics JSON,
                trained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                last_used_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (model_id, symbol, timeframe)
            )
        """)
        
        # Add indexes
        print("Creating indexes for ai_model_registry...")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_model_lookup ON ai_model_registry (model_id, symbol, timeframe)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_model_status ON ai_model_registry (status)")
        
        print("[SUCCESS] ai_model_registry table created successfully.")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error creating AI schema: {e}")

if __name__ == "__main__":
    init_ai_schema()
