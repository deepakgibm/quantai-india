"""
Check Nifty100 Data Coverage
Query the database to verify if 20 years of data is loaded in the nifty100_daily table.
"""

import asyncio
from sqlalchemy import select, func, distinct
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models_ml import Nifty100Daily
from config import settings


async def check_nifty100_coverage():
    """Check the data coverage in the nifty100_daily table."""
    
    # Create async engine
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        # Get total record count
        result = await session.execute(select(func.count(Nifty100Daily.id)))
        total_records = result.scalar()
        
        # Get unique symbols count
        result = await session.execute(select(func.count(distinct(Nifty100Daily.symbol))))
        unique_symbols = result.scalar()
        
        # Get date range
        result = await session.execute(select(func.min(Nifty100Daily.timestamp)))
        min_date = result.scalar()
        
        result = await session.execute(select(func.max(Nifty100Daily.timestamp)))
        max_date = result.scalar()
        
        # Get symbol list with their record counts
        result = await session.execute(
            select(
                Nifty100Daily.symbol,
                func.count(Nifty100Daily.id).label('count'),
                func.min(Nifty100Daily.timestamp).label('min_date'),
                func.max(Nifty100Daily.timestamp).label('max_date')
            ).group_by(Nifty100Daily.symbol)
            .order_by(func.count(Nifty100Daily.id).desc())
        )
        symbol_stats = result.all()
        
        # Calculate coverage
        if min_date and max_date:
            days_coverage = (max_date - min_date).days
            years_coverage = days_coverage / 365.25
        else:
            days_coverage = 0
            years_coverage = 0
        
        # Expected 20 years from today
        twenty_years_ago = datetime.now() - timedelta(days=20*365.25)
        
        # Print results
        print("\n" + "="*80)
        print("NIFTY 100 DATA COVERAGE REPORT")
        print("="*80)
        print(f"\n📊 OVERALL STATISTICS:")
        print(f"   Total Records: {total_records:,}")
        print(f"   Unique Symbols: {unique_symbols}")
        print(f"   Date Range: {min_date.date() if min_date else 'N/A'} to {max_date.date() if max_date else 'N/A'}")
        print(f"   Coverage: {days_coverage:,} days ({years_coverage:.2f} years)")
        
        if min_date:
            if min_date <= twenty_years_ago:
                print(f"   ✅ HAS 20+ YEARS OF DATA")
            else:
                shortage_days = (min_date - twenty_years_ago).days
                shortage_years = shortage_days / 365.25
                print(f"   ⚠️  SHORT BY {shortage_days} days ({shortage_years:.2f} years)")
        else:
            print(f"   ❌ NO DATA FOUND")
        
        print(f"\n📈 TOP 10 SYMBOLS BY RECORD COUNT:")
        print(f"   {'Symbol':<15} {'Records':<12} {'Start Date':<15} {'End Date':<15} {'Years'}")
        print(f"   {'-'*15} {'-'*12} {'-'*15} {'-'*15} {'-'*6}")
        
        for i, (symbol, count, min_dt, max_dt) in enumerate(symbol_stats[:10], 1):
            symbol_years = (max_dt - min_dt).days / 365.25 if min_dt and max_dt else 0
            print(f"   {symbol:<15} {count:<12,} {min_dt.date() if min_dt else 'N/A':<15} {max_dt.date() if max_dt else 'N/A':<15} {symbol_years:.2f}")
        
        if len(symbol_stats) > 10:
            print(f"\n📋 ALL SYMBOLS ({unique_symbols} total):")
            print(f"   {'Symbol':<15} {'Records':<12} {'Start Date':<15} {'End Date':<15} {'Years'}")
            print(f"   {'-'*15} {'-'*12} {'-'*15} {'-'*15} {'-'*6}")
            
            for symbol, count, min_dt, max_dt in symbol_stats:
                symbol_years = (max_dt - min_dt).days / 365.25 if min_dt and max_dt else 0
                print(f"   {symbol:<15} {count:<12,} {min_dt.date() if min_dt else 'N/A':<15} {max_dt.date() if max_dt else 'N/A':<15} {symbol_years:.2f}")
        
        # Check for data quality issues
        print(f"\n🔍 DATA QUALITY CHECK:")
        
        # Check for symbols with less than expected records
        expected_records_20y = 20 * 252  # ~252 trading days per year
        low_count_symbols = [s for s in symbol_stats if s[1] < expected_records_20y * 0.8]
        
        if low_count_symbols:
            print(f"   ⚠️  {len(low_count_symbols)} symbols with fewer than expected records:")
            for symbol, count, _, _ in low_count_symbols[:5]:
                print(f"      - {symbol}: {count:,} records (expected ~{expected_records_20y:,})")
            if len(low_count_symbols) > 5:
                print(f"      ... and {len(low_count_symbols) - 5} more")
        else:
            print(f"   ✅ All symbols have adequate record counts")
        
        print("\n" + "="*80)
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(check_nifty100_coverage())
