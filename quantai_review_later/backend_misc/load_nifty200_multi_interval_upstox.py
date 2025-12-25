"""
Nifty 200 Multi-Interval Loader (Upstox)
Loads 1min, 3min, 5min, 15min, 30min data from Jan 2022 to today.
"""
import asyncio
from datetime import datetime, timedelta
from backend.database import AsyncSessionLocal
from backend.models_alpha import StockData


# Using existing AsyncSessionLocal and StockData model from the application

# Intervals mapping to Upstox API strings
INTERVALS = {
    "1min": "1minute",
    "3min": "3minute",
    "5min": "5minute",
    "15min": "15minute",
    "30min": "30minute",
}

async def load_symbol_interval(symbol, instrument_key, interval_name, interval_api, from_dt, to_dt, session):
    from services.upstox_client import get_upstox_client
    client = get_upstox_client()
    try:
        df = await client.get_historical_data(
            symbol=symbol,
            instrument_key=instrument_key,
            from_date=from_dt,
            to_date=to_dt,
            interval=interval_api,
        )
        if df.empty:
            print(f"      {interval_name}: No data")
            return 0
        inserted = 0
        for _, row in df.iterrows():
            record = StockData(
                symbol=symbol,
                timestamp=row['timestamp'],
                open=float(row['open']),
                high=float(row['high']),
                low=float(row['low']),
                close=float(row['close']),
                volume=int(row['volume']),
                interval=interval_name,
                source="upstox",
            )
            try:
                session.add(record)
                inserted += 1
            except IntegrityError:
                await session.rollback()
                continue
        await session.commit()
        print(f"      {interval_name}: Inserted {inserted:,} records")
        return inserted
    except Exception as e:
        print(f"      {interval_name}: Error {e}")
        await session.rollback()
        return 0

async def main():
    print("="*80)
    print("NIFTY 200 MULTI-INTERVAL LOADER (UPSTOX)")
    print("="*80)
    print("Loading data from Jan 2022 to today for intervals: 1min, 3min, 5min, 15min, 30min")
    print()
    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Get symbols and instrument keys
    from services.upstox_client import get_upstox_client
    client = get_upstox_client()
    symbols = await client.get_nifty_200_symbols()
    print(f"Fetched {len(symbols)} Nifty 200 symbols")
    
    from_dt = datetime(2022, 1, 1)
    to_dt = datetime.now()
    total_inserted = 0
    async with AsyncSessionLocal() as session:
        for idx, (sym, key) in enumerate(symbols, 1):
            print(f"[{idx}/{len(symbols)}] {sym}")
            for interval_name, api_name in INTERVALS.items():
                inserted = await load_symbol_interval(
                    symbol=sym,
                    instrument_key=key,
                    interval_name=interval_name,
                    interval_api=api_name,
                    from_dt=from_dt,
                    to_dt=to_dt,
                    session=session,
                )
                total_inserted += inserted
                await asyncio.sleep(0.2)  # respect rate limits
            print()
    print("="*80)
    print(f"✅ Load complete. Total records inserted: {total_inserted:,}")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(main())
