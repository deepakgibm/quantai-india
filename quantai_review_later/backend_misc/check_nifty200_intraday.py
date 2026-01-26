"""
Check for Nifty 200 Intraday Data Tables
Verifies existence and coverage of 1min, 5min, 15min candle data
"""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = "sqlite+aiosqlite:///./quantai.db"

async def check_nifty200_tables():
    """Check for Nifty 200 intraday data tables"""
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        # Get all tables
        result = await conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ))
        tables = [row[0] for row in result.fetchall()]
    
    print("="*80)
    print("NIFTY 200 INTRADAY DATA TABLE CHECK")
    print("="*80)
    print()
    
    # Check for specific intraday tables
    intraday_keywords = ['1min', '5min', '15min', '1minute', '5minute', '15minute', 'intraday', 'candle']
    nifty_keywords = ['nifty', '200', 'stock']
    
    print("📊 ALL TABLES IN DATABASE:")
    for table in tables:
        print(f"   - {table}")
    
    print(f"\n📋 Total Tables: {len(tables)}")
    print()
    
    # Look for intraday-related tables
    print("🔍 SEARCHING FOR INTRADAY DATA TABLES:")
    intraday_tables = []
    for table in tables:
        table_lower = table.lower()
        if any(keyword in table_lower for keyword in intraday_keywords):
            intraday_tables.append(table)
            print(f"   ✓ Found: {table}")
    
    if not intraday_tables:
        print("   ❌ NO INTRADAY TABLES FOUND")
    
    print()
    
    # Check StockData table (the main intraday table from historical_loader.py)
    if 'stock_data' in [t.lower() for t in tables]:
        print("✅ FOUND: stock_data table (Main intraday table)")
        print()
        
        # Check data in stock_data
        async with engine.begin() as conn:
            # Get record count
            result = await conn.execute(text("SELECT COUNT(*) FROM stock_data"))
            total_records = result.scalar()
            
            if total_records > 0:
                # Get interval types
                result = await conn.execute(text(
                    "SELECT DISTINCT interval FROM stock_data"
                ))
                intervals = [row[0] for row in result.fetchall() if row[0]]
                
                # Get unique symbols
                result = await conn.execute(text(
                    "SELECT COUNT(DISTINCT symbol) FROM stock_data"
                ))
                unique_symbols = result.scalar()
                
                # Get date range
                result = await conn.execute(text(
                    "SELECT MIN(timestamp), MAX(timestamp) FROM stock_data"
                ))
                date_range = result.fetchone()
                
                # Get sample intervals data
                result = await conn.execute(text("""
                    SELECT interval, COUNT(*) as count, COUNT(DISTINCT symbol) as symbols
                    FROM stock_data 
                    GROUP BY interval
                """))
                interval_stats = result.fetchall()
                
                print("📈 STOCK_DATA TABLE ANALYSIS:")
                print(f"   Total Records: {total_records:,}")
                print(f"   Unique Symbols: {unique_symbols}")
                print(f"   Date Range: {date_range[0]} to {date_range[1]}")
                print()
                print("   Interval Breakdown:")
                for interval, count, symbols in interval_stats:
                    interval_name = interval if interval else "NULL"
                    print(f"      {interval_name:15s}: {count:,} records ({symbols} symbols)")
                
                # Check for specific intervals
                has_1min = any('1min' in str(i).lower() if i else False for i, _, _ in interval_stats)
                has_5min = any('5min' in str(i).lower() if i else False for i, _, _ in interval_stats)
                has_15min = any('15min' in str(i).lower() if i else False for i, _, _ in interval_stats)
                
                print()
                print("🎯 REQUIRED INTERVALS CHECK:")
                print(f"   1-minute data:  {'✅ PRESENT' if has_1min else '❌ MISSING'}")
                print(f"   5-minute data:  {'✅ PRESENT' if has_5min else '❌ MISSING'}")
                print(f"   15-minute data: {'✅ PRESENT' if has_15min else '❌ MISSING'}")
            else:
                print("   ⚠️  TABLE EXISTS BUT IS EMPTY")
                print()
                print("🎯 REQUIRED INTERVALS CHECK:")
                print("   1-minute data:  ❌ NO DATA")
                print("   5-minute data:  ❌ NO DATA")
                print("   15-minute data: ❌ NO DATA")
    else:
        print("❌ stock_data table NOT FOUND")
        print()
        print("🎯 REQUIRED INTERVALS CHECK:")
        print("   1-minute data:  ❌ TABLE MISSING")
        print("   5-minute data:  ❌ TABLE MISSING")
        print("   15-minute data: ❌ TABLE MISSING")
    
    print()
    print("="*80)
    print("RECOMMENDATION:")
    print("="*80)
    
    if 'stock_data' not in [t.lower() for t in tables]:
        print("""
To create and populate the intraday data tables:

1. Run the historical loader:
   cd backend
   python -m etl.historical_loader

2. This will fetch data from Upstox API for:
   - Nifty 200 symbols (or available mapping)
   - 1-minute candles
   - Last 5 years

3. For 5-minute and 15-minute data, modify the loader to fetch different intervals.
""")
    elif total_records == 0:
        print("""
The stock_data table exists but is empty.

Run the historical loader to populate it:
   cd backend
   python -m etl.historical_loader
""")
    else:
        intervals_needed = []
        if not has_1min:
            intervals_needed.append("1-minute")
        if not has_5min:
            intervals_needed.append("5-minute")
        if not has_15min:
            intervals_needed.append("15-minute")
        
        if intervals_needed:
            print(f"""
Missing intervals: {', '.join(intervals_needed)}

To add these intervals:
1. Modify etl/historical_loader.py to fetch multiple intervals
2. Or create separate tables for each interval
3. Run the loader for each interval type
""")
        else:
            print("""
✅ All required intervals are present!

Data is ready for:
- AlphaPrime signal generation
- Backtesting
- Live trading analysis
""")
    
    print("="*80)
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_nifty200_tables())
