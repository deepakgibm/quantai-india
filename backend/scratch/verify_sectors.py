import asyncio
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from utils.symbol_utils import _symbol_manager

def main():
    _symbol_manager.refresh_cache()
    print("Sectors Map Count:", len(_symbol_manager._sector_cache))
    sectors = set(_symbol_manager._sector_cache.values())
    print("Unique Sectors:", sectors)
    
    # print sector for some symbols
    symbols = ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK', 'NIFTY 50']
    for s in symbols:
        print(f"Symbol: {s}, Sector: {_symbol_manager.get_stock_sector(s)}")

if __name__ == "__main__":
    main()
