
import asyncio
import sys
import json
from pathlib import Path
from sqlalchemy import text

# Add project root to sys.path
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from backend.database import AsyncSessionLocal
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parent))
    from database import AsyncSessionLocal

async def check_missing():
    # Load all expected symbols
    json_file = "nifty200_instruments.json"
    with open(json_file, "r") as f:
        all_symbols_data = json.load(f)
        all_symbols = [s[0] for s in all_symbols_data]
        
    print(f"Total expected symbols: {len(all_symbols)}")
    
    # Get existing symbols from DB
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT DISTINCT symbol FROM stock_data"))
        existing_symbols = [row[0] for row in result.fetchall()]
        
    print(f"Total existing symbols in DB: {len(existing_symbols)}")
    
    existing_set = set(existing_symbols)
    missing_symbols = [s for s in all_symbols if s not in existing_set]
    
    print(f"Missing symbols: {len(missing_symbols)}")
    if missing_symbols:
        print("First 10 missing symbols:")
        print(missing_symbols[:10])
        
        # Save missing symbols to a file for reference
        with open("missing_symbols.txt", "w") as f:
            for s in missing_symbols:
                f.write(f"{s}\n")
        print("Saved all missing symbols to missing_symbols.txt")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check_missing())
