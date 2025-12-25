import asyncio
import sys
import os
from pathlib import Path

import sys
sys.path.append(os.getcwd())

from database import AsyncSessionLocal
from models import User
from sqlalchemy import select

async def check_users():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        print(f'Found {len(users)} users:')
        for u in users:
            print(f'  - Email: {u.email}, Username: {u.username}')

if __name__ == "__main__":
    asyncio.run(check_users())
