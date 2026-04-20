import asyncio
from sqlalchemy import text
from database import AsyncSessionLocal

async def check_tables():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
        tables = [row[0] for row in result]
        print(f"Tables found: {tables}")
        
        screener_tables = ['screener_stock_score', 'screener_conviction_list', 'screener_sector_analysis']
        for table in screener_tables:
            if table in tables:
                print(f"Table {table} EXISTS")
                res = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = res.scalar()
                print(f"Table {table} count: {count}")
            else:
                print(f"Table {table} MISSING")

if __name__ == "__main__":
    asyncio.run(check_tables())
