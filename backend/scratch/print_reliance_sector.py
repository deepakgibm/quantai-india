import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from utils.symbol_utils import get_stock_sector

def main():
    sector = get_stock_sector("RELIANCE")
    print("get_stock_sector('RELIANCE') returns:", repr(sector))

if __name__ == "__main__":
    main()
