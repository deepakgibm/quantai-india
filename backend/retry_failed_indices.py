"""
Fix failed indices by retrying with corrected NSE CSV codes.
"""
import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

from services.index_management_service import IndexManagementService
from database import sync_engine

svc = IndexManagementService()
RETRY_INDICES = ["NIFTY REALTY", "NIFTY PRIVATE BANK", "NIFTY CAPITAL GOODS", "NIFTY CHEMICALS"]

with sync_engine.begin() as conn:
    for name in RETRY_INDICES:
        print(f"\n  → Retrying {name}...")
        try:
            result = svc.refresh_index(name, conn)
            icon = "✓" if result.status in ("success", "partial") else "✗"
            print(f"  {icon} {name}: matched={result.matched_count} missing={result.missing_count} coverage={result.coverage_pct}%")
            if result.error:
                print(f"    ERROR: {result.error}")
        except Exception as e:
            print(f"  ✗ {name}: EXCEPTION: {e}")

print("\nDone.")
