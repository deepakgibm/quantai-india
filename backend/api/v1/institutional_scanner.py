from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from database import get_db, get_read_db
from services.institutional_scanner_service import get_institutional_scanner_service
from services.dragonfly_client import get_cache

router = APIRouter()

@router.get("/dashboard")
async def get_dashboard_stats(db: Session = Depends(get_read_db)):
    """Retrieve summarized institutional scanner opportunity dashboard stats."""
    cache = get_cache()
    cached = await cache.get_async("qai:scanner:institutional:dashboard")
    if cached:
        return cached
        
    # Cache miss: compute from database tables
    try:
        from sqlalchemy import text
        # Count total scanned from vcp_scores
        vcp_count = db.execute(text("SELECT COUNT(*), COUNT(CASE WHEN vcp_score >= 80 THEN 1 END), COUNT(CASE WHEN breakout_ready = TRUE THEN 1 END) FROM vcp_scores")).fetchone()
        bo_count = db.execute(text("SELECT COUNT(*) FROM breakout_candidates")).fetchone()
        rs_count = db.execute(text("SELECT COUNT(CASE WHEN rs_score >= 80 THEN 1 END) FROM relative_strength_rankings")).fetchone()
        
        total = vcp_count[0] if vcp_count else 0
        vcp_cands = vcp_count[1] if vcp_count else 0
        bo_ready = vcp_count[2] if vcp_count else 0
        fresh_bo = bo_count[0] if bo_count else 0
        near_52w = bo_count[0] if bo_count else 0  # fallback approximate
        rs_leaders = rs_count[0] if rs_count else 0
        
        return {
            "total_scanned": total,
            "vcp_candidates": vcp_cands,
            "breakout_ready": bo_ready,
            "fresh_breakouts": fresh_bo,
            "near_52w_high": near_52w,
            "rs_leaders": rs_leaders,
            "last_updated": None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database aggregation failed: {e}")

@router.get("/results")
async def get_scanner_results():
    """Retrieve detailed, filterable pattern scan results."""
    cache = get_cache()
    cached = await cache.get_async("qai:scanner:institutional:results")
    if cached:
        return cached
    return []

@router.post("/scan")
async def trigger_scan(background_tasks: BackgroundTasks):
    """Trigger background scanning of all active stocks."""
    service = get_institutional_scanner_service()
    if service.scan_status["is_scanning"]:
        return {"status": "scanning", "progress": service.scan_status["progress"]}
        
    # Start scan in background
    background_tasks.add_task(service.scan_all_stocks)
    return {"status": "started", "message": "Background scanning task initialized."}

@router.get("/status")
async def get_scan_status():
    """Get status/progress of background scanning task."""
    service = get_institutional_scanner_service()
    return service.scan_status

@router.get("/detail/{symbol}")
async def get_stock_detail(symbol: str):
    """Retrieve full analysis detail for a single stock."""
    service = get_institutional_scanner_service()
    try:
        data = await service.get_stock_detail(symbol)
        return data
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found or details not available: {e}")
