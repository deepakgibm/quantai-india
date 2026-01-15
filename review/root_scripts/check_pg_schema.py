
import asyncio
from sqlalchemy import text
from database import engine

async def check_column():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT column_name, data_type, character_maximum_length FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'hashed_password'"))
        row = result.fetchone()
        if row:
            print(f"Column: {row[0]}, Type: {row[1]}, Max Length: {row[2]}")
        else:
            print("Column hashed_password not found in users table")

if __name__ == "__main__":
    asyncio.run(check_column())
