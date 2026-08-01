"""
Indices API Router
==================
REST endpoints for NSE Index Management.

Routes:
    GET  /api/indices                        List all indices with metadata
    GET  /api/indices/{index_name}           Single index detail
    GET  /api/indices/{index_name}/symbols   Constituent symbols
    GET  /api/indices/{index_name}/stats     Coverage / validation stats
    POST /api/indices/refresh                Trigger refresh (one or all)
    POST /api/indices/validate               Run validation report for one index
    GET  /api/indices/refresh/log            Last N refresh log entries
"""

import logging
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/indices", tags=["indices"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class RefreshRequest(BaseModel):
    index_name: Optional[str] = None   # None = refresh all


class ValidateRequest(BaseModel):
    index_name: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_sync_conn():
    """Provide a synchronous SQLAlchemy connection for the service."""
    from database import sync_engine
    return sync_engine.connect()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("")
async def list_indices(db: AsyncSession = Depends(get_db)):
    """
    List all indices stored in index_master with constituent count and metadata.
    """
    try:
        result = await db.execute(text("""
            SELECT
                im.index_name,
                im.display_name,
                im.category,
                im.description,
                im.constituent_count,
                im.last_refreshed,
                im.is_active,
                im.nse_index_code,
                COALESCE(
                    (SELECT COUNT(*) FROM index_constituent ic
                     WHERE ic.index_id = im.index_id AND ic.removed_at IS NULL),
                    0
                ) AS live_count,
                COALESCE(
                    (SELECT irl.coverage_pct FROM index_refresh_log irl
                     WHERE irl.index_id = im.index_id
                     ORDER BY irl.refreshed_at DESC LIMIT 1),
                    0.0
                ) AS coverage_pct
            FROM index_master im
            ORDER BY
                CASE im.category
                    WHEN 'Broad Market' THEN 1
                    WHEN 'Sector' THEN 2
                    WHEN 'Midcap' THEN 3
                    WHEN 'Smallcap' THEN 4
                    ELSE 5
                END,
                im.index_name
        """))
        rows = result.fetchall()
        indices = [
            {
                "index_name": r[0],
                "display_name": r[1] or r[0],
                "category": r[2] or "Broad Market",
                "description": r[3] or "",
                "constituent_count": r[8],   # live count from constituent table
                "last_refreshed": r[5].isoformat() if r[5] else None,
                "is_active": r[6],
                "nse_index_code": r[7],
                "coverage_pct": round(float(r[9] or 0), 2),
            }
            for r in rows
        ]

        # Supplement with catalogue entries not yet in DB
        from services.index_management_service import NSE_INDICES
        db_names = {i["index_name"] for i in indices}
        for entry in NSE_INDICES:
            if entry["index_name"] not in db_names:
                indices.append({
                    "index_name": entry["index_name"],
                    "display_name": entry.get("display_name", entry["index_name"]),
                    "category": entry.get("category", "Broad Market"),
                    "description": entry.get("description", ""),
                    "constituent_count": 0,
                    "last_refreshed": None,
                    "is_active": False,
                    "nse_index_code": entry["nse_index_code"],
                    "coverage_pct": 0.0,
                })

        return {"indices": indices, "total": len(indices)}
    except Exception as e:
        logger.error(f"list_indices error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/catalogue")
def list_catalogue():
    """Return the full NSE index catalogue (static, no DB required)."""
    from services.index_management_service import NSE_INDICES
    return {"catalogue": NSE_INDICES, "total": len(NSE_INDICES)}


@router.get("/refresh/log")
async def get_refresh_log(limit: int = Query(20, le=100), db: AsyncSession = Depends(get_db)):
    """Return the most recent refresh log entries."""
    try:
        result = await db.execute(text("""
            SELECT index_name, refreshed_at, added_count, removed_count,
                   matched_count, missing_count, total_nse_count, coverage_pct,
                   status, error_message
            FROM index_refresh_log
            ORDER BY refreshed_at DESC
            LIMIT :lim
        """), {"lim": limit})
        rows = result.fetchall()
        return {
            "log": [
                {
                    "index_name": r[0],
                    "refreshed_at": r[1].isoformat() if r[1] else None,
                    "added_count": r[2],
                    "removed_count": r[3],
                    "matched_count": r[4],
                    "missing_count": r[5],
                    "total_nse_count": r[6],
                    "coverage_pct": round(float(r[7] or 0), 2),
                    "status": r[8],
                    "error_message": r[9],
                }
                for r in rows
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{index_name}/symbols")
async def get_index_symbols(
    index_name: str,
    include_removed: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """
    Return constituent symbols for a given index.
    Optionally include historically removed constituents.
    """
    try:
        where_clause = "" if include_removed else "AND ic.removed_at IS NULL"
        result = await db.execute(text(f"""
            SELECT
                inst.symbol,
                inst.instrument_key,
                inst.company_name,
                inst.sector,
                ic.weight,
                ic.industry,
                ic.added_at,
                ic.removed_at
            FROM index_master im
            JOIN index_constituent ic ON ic.index_id = im.index_id
            JOIN instrument_master inst ON inst.instrument_id = ic.instrument_id
            WHERE im.index_name = :name {where_clause}
            ORDER BY inst.symbol
        """), {"name": index_name})
        rows = result.fetchall()

        if not rows:
            # Check if index exists at all
            ex = await db.execute(text(
                "SELECT index_id FROM index_master WHERE index_name = :name"
            ), {"name": index_name})
            if not ex.fetchone():
                raise HTTPException(status_code=404, detail=f"Index '{index_name}' not found. Use POST /api/indices/refresh to seed it.")

        return {
            "index_name": index_name,
            "symbols": [
                {
                    "symbol": r[0],
                    "instrument_key": r[1],
                    "company_name": r[2],
                    "sector": r[3],
                    "weight": float(r[4]) if r[4] else None,
                    "industry": r[5],
                    "added_at": r[6].isoformat() if r[6] else None,
                    "removed_at": r[7].isoformat() if r[7] else None,
                }
                for r in rows
            ],
            "count": len(rows),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_index_symbols error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{index_name}/stats")
async def get_index_stats(index_name: str, db: AsyncSession = Depends(get_db)):
    """Return validation/coverage statistics for one index."""
    try:
        # Index meta
        meta = await db.execute(text("""
            SELECT index_id, display_name, category, last_refreshed, constituent_count
            FROM index_master WHERE index_name = :name
        """), {"name": index_name})
        meta_row = meta.fetchone()
        if not meta_row:
            raise HTTPException(status_code=404, detail=f"Index '{index_name}' not found")

        index_id = meta_row[0]

        # Live count
        live = await db.execute(text(
            "SELECT COUNT(*) FROM index_constituent WHERE index_id = :iid AND removed_at IS NULL"
        ), {"iid": index_id})
        live_count = live.scalar() or 0

        # Last refresh log
        log = await db.execute(text("""
            SELECT matched_count, missing_count, total_nse_count, coverage_pct,
                   status, refreshed_at, missing_symbols
            FROM index_refresh_log WHERE index_id = :iid
            ORDER BY refreshed_at DESC LIMIT 1
        """), {"iid": index_id})
        log_row = log.fetchone()

        return {
            "index_name": index_name,
            "display_name": meta_row[1] or index_name,
            "category": meta_row[2],
            "last_refreshed": meta_row[3].isoformat() if meta_row[3] else None,
            "live_constituent_count": live_count,
            "last_refresh": {
                "matched_count": log_row[0] if log_row else 0,
                "missing_count": log_row[1] if log_row else 0,
                "total_nse_count": log_row[2] if log_row else 0,
                "coverage_pct": round(float(log_row[3] or 0), 2) if log_row else 0.0,
                "status": log_row[4] if log_row else "never_run",
                "refreshed_at": log_row[5].isoformat() if (log_row and log_row[5]) else None,
                "missing_symbols": log_row[6] if log_row else "[]",
            } if log_row else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{index_name}")
async def get_index_detail(index_name: str, db: AsyncSession = Depends(get_db)):
    """Return full detail for a single index."""
    try:
        result = await db.execute(text("""
            SELECT index_name, display_name, description, category, nse_index_code,
                   csv_url, last_refreshed, constituent_count, is_active
            FROM index_master WHERE index_name = :name
        """), {"name": index_name})
        row = result.fetchone()
        if not row:
            # Try catalogue
            from services.index_management_service import IndexManagementService
            svc = IndexManagementService()
            entry = svc.get_index_info(index_name)
            if entry:
                return {**entry, "in_database": False, "constituent_count": 0}
            raise HTTPException(status_code=404, detail=f"Index '{index_name}' not found")

        return {
            "index_name": row[0],
            "display_name": row[1] or row[0],
            "description": row[2],
            "category": row[3],
            "nse_index_code": row[4],
            "csv_url": row[5],
            "last_refreshed": row[6].isoformat() if row[6] else None,
            "constituent_count": row[7],
            "is_active": row[8],
            "in_database": True,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh")
async def refresh_indices(request: RefreshRequest, background_tasks: BackgroundTasks):
    """
    Trigger an index constituent refresh from NSE.
    If index_name is omitted, refreshes ALL indices.
    Runs in background so the HTTP response is immediate.
    """
    def _do_refresh(index_name: Optional[str]):
        from services.index_management_service import IndexManagementService
        from database import sync_engine
        svc = IndexManagementService()
        with sync_engine.begin() as conn:
            if index_name:
                result = svc.refresh_index(index_name, conn)
                logger.info(f"Refresh complete for {index_name}: {result.status}")
            else:
                results = svc.refresh_all(conn)
                for r in results:
                    logger.info(f"  {r.index_name}: {r.status} coverage={r.coverage_pct}%")

    background_tasks.add_task(_do_refresh, request.index_name)
    return {
        "status": "queued",
        "message": f"Refresh started for {'all indices' if not request.index_name else request.index_name}",
    }


@router.post("/validate")
def validate_index(request: ValidateRequest):
    """
    Run constituent validation for one index synchronously and return the report.
    """
    try:
        from services.index_management_service import IndexManagementService
        from database import sync_engine
        svc = IndexManagementService()

        # Find catalogue entry to get nse_index_code
        entry = svc.get_index_info(request.index_name)
        if not entry:
            raise HTTPException(status_code=404, detail=f"Index '{request.index_name}' not in catalogue")

        with sync_engine.connect() as conn:
            nse_records = svc.fetch_nse_constituents(entry["nse_index_code"])
            report = svc.validate_constituents(request.index_name, nse_records, conn)

        return {
            "index_name": report.index_name,
            "total_nse": report.total_nse,
            "matched_count": len(report.matched),
            "auto_resolved_count": len(report.auto_resolved),
            "missing_count": len(report.missing),
            "coverage_pct": report.coverage_pct,
            "missing": report.missing,
            "auto_resolved": report.auto_resolved,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"validate_index error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
