
import sys
import os
from pprint import pprint

# Add backend to path to import services
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Import directly from services since we added backend/ to path
from services.db_data_fetcher import get_db_data_fetcher

def test_fetch_indices():
    print("Testing fetch_indices_snapshots...")
    fetcher = get_db_data_fetcher()
    
    try:
        snapshots = fetcher.fetch_indices_snapshots()
        print(f"Found {len(snapshots)} snapshots:")
        pprint(snapshots)
        
        expected = ["NIFTY 50", "BANK NIFTY", "INDIA VIX"]
        found = [s['name'] for s in snapshots]
        
        print("\nVerification:")
        for name in expected:
            if name in found:
                print(f"[OK] {name} found")
            else:
                print(f"[FAIL] {name} NOT found")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_fetch_indices()
