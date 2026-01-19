
import asyncio
from database import AsyncSessionLocal
from models_alpha import StockCandleV2, InstrumentMaster, TimeframeMapper
from sqlalchemy import select

async def verify():
    print("Testing 5m symbols...")
    async with AsyncSessionLocal() as session:
        query = (
            select(InstrumentMaster.symbol)
            .join(StockCandleV2, StockCandleV2.instrument_id == InstrumentMaster.instrument_id)
            .where(StockCandleV2.timeframe == 5)
            .distinct()
            .limit(10)
        )
        result = await session.execute(query)
        symbols = [row[0] for row in result.all()]
        print(f"5m Symbols found: {symbols}")

        print("Testing 1D symbols...")
        query_1d = (
            select(InstrumentMaster.symbol)
            .join(StockCandleV2, StockCandleV2.instrument_id == InstrumentMaster.instrument_id)
            .where(StockCandleV2.timeframe == 1440)
            .distinct()
            .limit(10)
        )
        result_1d = await session.execute(query_1d)
        symbols_1d = [row[0] for row in result_1d.all()]
        print(f"1D Symbols found: {symbols_1d}")

if __name__ == "__main__":
    asyncio.run(verify())
