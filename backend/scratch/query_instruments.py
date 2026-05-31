import asyncio
import sys
from pathlib import Path

# Add backend directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import text
from database import SessionLocal

async def main():
    db = SessionLocal()
    try:
        # Check columns
        res = db.execute(text("SELECT * FROM instrument_master LIMIT 1")).fetchone()
        if res:
            print("Columns in instrument_master:")
            print(list(res._mapping.keys()))
            print("\nRow value:")
            print(dict(res._mapping))
        else:
            print("instrument_master is empty")
    except Exception as e:
        print(f"Database query failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
