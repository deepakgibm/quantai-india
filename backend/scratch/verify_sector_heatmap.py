import asyncio
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

from services.dragonfly_client import get_cache

def main():
    cache = get_cache()
    heatmap = cache.get("qai:market:sector_heatmap")
    print("Sector Heatmap Cache Value:")
    print(heatmap)

if __name__ == "__main__":
    main()
