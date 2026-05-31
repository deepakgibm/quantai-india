import sys
from pathlib import Path
import json

sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

from services.cache import get_cache_manager

def main():
    cache = get_cache_manager()
    if not cache.is_available():
        print("Cache is not available.")
        return
        
    heatmap = cache.get("qai:market:sector_heatmap")
    print("qai:market:sector_heatmap in cache:", heatmap is not None)
    if heatmap:
        print("Heatmap Data Keys:", list(heatmap.keys()))
        print("Heatmap sample data (first 3):")
        print(json.dumps(heatmap.get("data", [])[:3], indent=2))
        
        # Search for Oil Gas & Consumable Fuels (RELIANCE sector)
        for entry in heatmap.get("data", []):
            if entry.get("sector") == "Oil Gas & Consumable Fuels" or "Consumable" in entry.get("sector", ""):
                print("\nFound Reliance Sector Entry:")
                print(json.dumps(entry, indent=2))

if __name__ == "__main__":
    main()
