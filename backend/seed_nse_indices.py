"""
Seed NSE Index Data
====================
Fetches all NSE index constituents from official CSV sources and
populates index_master + index_constituent tables.

Run inside backend container:
    python seed_nse_indices.py
"""
import sys
import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

from services.index_management_service import IndexManagementService, NSE_INDICES
from database import sync_engine

svc = IndexManagementService()

print(f"\n{'='*60}")
print(f"  NSE Index Seed Script — {len(NSE_INDICES)} indices to import")
print(f"{'='*60}\n")

summary = []

with sync_engine.begin() as conn:
    for entry in NSE_INDICES:
        name = entry["index_name"]
        print(f"  → {name} ({entry['nse_index_code']}) ...", end=" ", flush=True)
        try:
            result = svc.refresh_index(name, conn)
            status_icon = "✓" if result.status == "success" else ("~" if result.status == "partial" else "✗")
            print(f"{status_icon} matched={result.matched_count} missing={result.missing_count} coverage={result.coverage_pct}%")
            summary.append(result)
        except Exception as e:
            print(f"✗ ERROR: {e}")
            summary.append(None)

print(f"\n{'='*60}")
print(f"  SUMMARY")
print(f"{'='*60}")

success = [r for r in summary if r and r.status in ("success", "partial")]
failed = [r for r in summary if r and r.status == "failed"]
none_results = [r for r in summary if r is None]

print(f"  Total indices processed : {len(NSE_INDICES)}")
print(f"  Successful / partial    : {len(success)}")
print(f"  Failed                  : {len(failed) + len(none_results)}")
print()

if success:
    total_matched = sum(r.matched_count for r in success)
    total_missing = sum(r.missing_count for r in success)
    print(f"  Total matched symbols   : {total_matched}")
    print(f"  Total missing symbols   : {total_missing}")
    print()

if [r for r in summary if r and r.missing_count > 0]:
    print("  Indices with missing symbols:")
    for r in summary:
        if r and r.missing_count > 0:
            print(f"    {r.index_name}: {r.missing_count} missing — {r.missing_symbols[:5]}")

print()
print("  Done! Use GET /api/indices to inspect the results.")
