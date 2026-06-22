import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from database import sync_engine
from sqlalchemy import inspect, text

def drop_ml_tables():
    print(f"Connecting to database: {sync_engine.url}")
    inspector = inspect(sync_engine)
    tables = inspector.get_table_names()
    
    table_to_drop = "ai_model_registry"
    
    if table_to_drop in tables:
        print(f"Table '{table_to_drop}' found. Dropping...")
        with sync_engine.connect() as conn:
            # SQLAlchemy drops require raw execution or metadata drop
            conn.execute(text(f"DROP TABLE {table_to_drop}"))
            conn.commit()
        print(f"Successfully dropped table '{table_to_drop}'.")
    else:
        print(f"Table '{table_to_drop}' does not exist in the database. No action needed.")

if __name__ == "__main__":
    drop_ml_tables()
