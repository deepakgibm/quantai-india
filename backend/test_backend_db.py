import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.getcwd())

from database import engine, init_db
from sqlalchemy import text

async def test_backend_db():
    print(f"Testing backend database engine...")
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print(f"Connection successful: {result.fetchone()}")
            
            # Check for stock_data table
            result = await conn.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'stock_data'"))
            exists = result.scalar() > 0
            print(f"Table 'stock_data' exists: {exists}")
            
            if exists:
                result = await conn.execute(text("SELECT COUNT(*) FROM stock_data"))
                print(f"Row count in stock_data: {result.scalar()}")
            else:
                print("Table 'stock_data' does not exist in PostgreSQL public schema.")
                
    except Exception as e:
        print(f"Backend database connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_backend_db())
