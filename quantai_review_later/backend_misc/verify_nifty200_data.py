
import asyncio
import sys
from pathlib import Path
from sqlalchemy import text

# Add project root to sys.path
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from backend.database import AsyncSessionLocal
except ImportError:
    # Fallback if running from backend dir directly
    sys.path.append(str(Path(__file__).resolve().parent))
    from database import AsyncSessionLocal

async def verify_data():
    async with AsyncSessionLocal() as session:
        print("Verifying Nifty 200 Data...")
        
        # Check total count
        result = await session.execute(text("SELECT COUNT(*) FROM stock_data"))
        total_count = result.scalar()
        print(f"Total records in stock_data: {total_count:,}")
        
        # Check count by interval
        print("\nRecords by Interval:")
        result = await session.execute(text("SELECT interval, COUNT(*) FROM stock_data GROUP BY interval"))
        rows = result.fetchall()
        for interval, count in rows:
            print(f"  {interval}: {count:,}")
            
        # Check count by symbol (sample top 5)
        print("\nTop 5 Symbols by Record Count:")
        result = await session.execute(text("SELECT symbol, COUNT(*) as c FROM stock_data GROUP BY symbol ORDER BY c DESC LIMIT 5"))
        rows = result.fetchall()
        for symbol, count in rows:
            print(f"  {symbol}: {count:,}")

        # Check ABB specifically
        print("\nChecking ABB:")
        result = await session.execute(text("SELECT COUNT(*) FROM stock_data WHERE symbol='ABB'"))
        abb_count = result.scalar()
        print(f"  ABB: {abb_count:,}")
            
        # Check for symbols with 0 records
        print("\nSymbols with 0 records (if any):")
        # This is harder to check directly without joining with the full list, 
        # but we can check distinct symbols count
        result = await session.execute(text("SELECT COUNT(DISTINCT symbol) FROM stock_data"))
        distinct_symbols = result.scalar()
        print(f"Distinct symbols in database: {distinct_symbols}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(verify_data())
