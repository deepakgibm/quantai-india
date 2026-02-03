
import asyncio
from sqlalchemy import select
from database import AsyncSessionLocal
from models_alpha import InstrumentMaster

async def check():
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(InstrumentMaster.symbol).limit(5))
        print(f"InstrumentMaster sample: {res.all()}")

if __name__ == "__main__":
    asyncio.run(check())
