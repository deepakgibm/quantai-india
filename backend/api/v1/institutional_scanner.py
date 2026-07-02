from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from database import get_read_db
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
        vcp_res = await db.execute(text("SELECT COUNT(*), COUNT(CASE WHEN vcp_score >= 80 THEN 1 END), COUNT(CASE WHEN breakout_ready = TRUE THEN 1 END) FROM vcp_scores"))
        vcp_count = vcp_res.fetchone()
        
        bo_res = await db.execute(text("SELECT COUNT(*) FROM breakout_candidates"))
        bo_count = bo_res.fetchone()
        
        rs_res = await db.execute(text("SELECT COUNT(CASE WHEN rs_score >= 80 THEN 1 END) FROM relative_strength_rankings"))
        rs_count = rs_res.fetchone()
        
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
async def get_scanner_results(db: Session = Depends(get_read_db)):
    """Retrieve detailed, filterable pattern scan results."""
    cache = get_cache()
    cached = await cache.get_async("qai:scanner:institutional:results")
    if cached:
        return cached
        
    # Cache miss fallback: query SQL database
    try:
        from sqlalchemy import text
        query = text("""
            SELECT 
                v.symbol,
                v.current_price,
                v.vcp_score,
                v.category as vcp_category,
                v.num_contractions as vcp_contractions,
                v.latest_contraction_pct as vcp_latest_contraction,
                v.volume_dry_up_pct as volume_dry_up,
                v.atr_contraction_pct as atr_contraction,
                v.breakout_pivot,
                v.breakout_ready,
                t.trend_template_score,
                t.sma50,
                t.sma150,
                t.sma200,
                t.distance_to_52w_high as distance_52w_high,
                r.rs_score,
                r.rank as rs_rank,
                r.sector_rank,
                r.industry_rank,
                r.sector,
                r.market_cap,
                d.box_top as darvas_top,
                d.box_bottom as darvas_bottom,
                d.days_inside_box as darvas_days
            FROM vcp_scores v
            LEFT JOIN trend_template_scores t ON v.symbol = t.symbol
            LEFT JOIN relative_strength_rankings r ON v.symbol = r.symbol
            LEFT JOIN darvas_boxes d ON v.symbol = d.symbol
        """)
        
        db_res = await db.execute(query)
        db_results = db_res.fetchall()
        
        results_list = []
        for row in db_results:
            results_list.append({
                "symbol": row.symbol,
                "company_name": row.symbol,  # fallback to symbol
                "sector": row.sector or "N/A",
                "current_price": row.current_price,
                "market_cap": row.market_cap or 0.0,
                "rs_score": row.rs_score or 0.0,
                "rs_rank": row.rs_rank or 1,
                "sector_rank": row.sector_rank or 1,
                "industry_rank": row.industry_rank or 1,
                "vcp_score": row.vcp_score,
                "vcp_category": row.vcp_category or "Ignore",
                "vcp_contractions": row.vcp_contractions or 0,
                "vcp_latest_contraction": row.vcp_latest_contraction or 0.0,
                "volume_dry_up": row.volume_dry_up or 0.0,
                "atr_contraction": row.atr_contraction or 0.0,
                "breakout_pivot": row.breakout_pivot,
                "breakout_ready": bool(row.breakout_ready),
                "trend_template_score": row.trend_template_score or 0.0,
                "sma50": row.sma50,
                "sma150": row.sma150,
                "sma200": row.sma200,
                "distance_52w_high": row.distance_52w_high or 0.0,
                "is_breakout": False,
                "breakout_type": None,
                "breakout_price": None,
                "volume_surge": 0.0,
                "darvas_status": "Inside",
                "darvas_top": row.darvas_top or 0.0,
                "darvas_bottom": row.darvas_bottom or 0.0,
                "darvas_days": row.darvas_days or 0,
                "cup_handle_confidence": 0.0,
                "double_bottom_confidence": 0.0,
                "flat_base_length": 0,
                "flat_base_depth": 0.0,
                "volume_contraction": 0.0,
                "supply_drying_score": 0.0,
                "accumulation_score": 0.0
            })
            
        return results_list
    except Exception as e:
        import traceback
        traceback.print_exc()
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
