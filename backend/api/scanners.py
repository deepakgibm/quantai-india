"""
Unified Scanner API Router
Consolidates standard, HP (Cache-First), and AI scanners.
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
import logging
import time

from models import User, ScannerPreset
from database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from utils.auth import get_current_user
from services.dragonfly_client import get_cache, CacheKeys, cache_get
from services.market_hours_service import get_market_hours_service
from services.momentum_scanner import MomentumScanner
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Scanners"])

# --- Models ---
class ScanRequest(BaseModel):
    indices: List[str] = Field(..., min_length=1)
    timeframe: str
    strategies: List[str]

class ScanResponse(BaseModel):
    status: str
    scan_id: str
    results: List[Dict[str, Any]]
    total_stocks: int
    signals_found: int
    duration_seconds: float

# --- Core Scanner Endpoints ---

@router.get("/strategies")
async def get_strategies():
    """Get all available scanning strategies."""
    try:
        from strategies import StrategyRegistry
        strategies = StrategyRegistry.list_strategies()
        return {"status": "success", "strategies": strategies, "total_count": len(strategies)}
    except Exception as e:
        logger.error(f"Failed to list strategies: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/run", response_model=ScanResponse)
async def run_scan(request: ScanRequest, current_user: User = Depends(get_current_user)):
    """Standard background/on-demand scanner execution."""
    logger.info(f"Received scan request for indices={request.indices}, strategies={request.strategies}")
    try:
        from core.scanner.scanner_engine import ScannerEngine
        scanner = ScannerEngine()
        logger.info("ScannerEngine initialized successfully")
        
        start_time = time.time()
        scan_id = f"scan_{int(start_time)}"
        
        results = await scanner.run_scan(
            indices=request.indices,
            timeframe=request.timeframe,
            strategies=request.strategies
        )
        duration = round(time.time() - start_time, 2)
        logger.info(f"Scan completed in {duration}s. Found {len(results)} results.")
        
        return ScanResponse(
            status="success", scan_id=scan_id, results=results,
            total_stocks=len(set(r["symbol"] for r in results)),
            signals_found=len(results),
            duration_seconds=duration
        )
    except ImportError as e:
        logger.error(f"Failed to import ScannerEngine: {e}")
        raise HTTPException(status_code=500, detail=f"Scanner configuration error: {str(e)}")
    except Exception as e:
        logger.error(f"Scan failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# --- High-Performance (HP) Cache-First Endpoints ---

@router.get("/hp/momentum")
async def get_hp_momentum():
    """HP momentum results (Cache-First, <50ms)."""
    data = cache_get(CacheKeys.momentum()) or []
    return {"type": "momentum", "data": data, "count": len(data), "source": "CACHE"}

@router.get("/hp/breakout")
async def get_hp_breakout():
    """HP breakout results (Cache-First, <50ms)."""
    data = cache_get(CacheKeys.breakout()) or []
    return {"type": "breakout", "data": data, "count": len(data), "source": "CACHE"}

# --- WebSocket Feed ---

@router.websocket("/ws")
async def scanner_websocket(websocket: WebSocket):
    """Real-time scanner update feed."""
    logger.info("New WebSocket connection request")
    try:
        await websocket.accept()
        logger.info("WebSocket accepted")
        
        from core.scanner.realtime_scanner_engine import get_realtime_scanner_engine
        from services.realtime_yearly_breakout_engine import get_realtime_yearly_breakout_engine
        
        engine = get_realtime_scanner_engine()
        breakout_engine = get_realtime_yearly_breakout_engine()
        
        logger.info("RealTimeScannerEngines obtained")
        
        while True:
            # Check connection state
            if websocket.client_state.name == "DISCONNECTED":
                break
                
            data = engine.get_all_stock_data()
            indices = engine.get_indices()
            breakouts = list(breakout_engine.breakouts.values())
            
            await websocket.send_json({
                "type": "bucket_update", 
                "data": data, 
                "indices": indices,
                "breakouts": breakouts,
                "timestamp": datetime.now().isoformat()
            })
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        logger.info("Scanner WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        # Try to close if not already closed
        try:
            await websocket.close()
        except:
            pass
@router.get("/momentum")
async def get_momentum_data(
    force_refresh: bool = False,
    current_user: User = Depends(get_current_user)
):
    """
    REST endpoint for momentum data.
    Delegates to ScannerEngine.
    """
    if force_refresh:
        logger.info("Force refresh requested for momentum data")
    
    # Use HP scanner if available, else standard
    market_service = get_market_hours_service()
    data = await get_hp_momentum()
    
    # Validation: Ensure data is valid list
    if data and isinstance(data, dict) and "data" in data:
        data = data["data"]
    
    if data and len(data) > 0 and market_service.is_market_open():
         # Wrap in bucket_update for Frontend
         return {
             "type": "bucket_update",
             "data": data,
             "timestamp": datetime.now().isoformat()
         }

    # Fallback to DB Scanning (if market closed or cache empty)
    logger.info("Momentum fallback: Using DB scanner (Market Closed/Cache Empty)")
    try:
        scanner = MomentumScanner()
        # Scan synchronous, run in threadpool
        raw_results = await asyncio.to_thread(scanner.scan_all)
        
        # Map to Frontend StockTick format
        mapped_results = []
        for r in raw_results:
            roc = r.get("roc_10d", 0)
            score = r.get("strength", 50)
            
            # Determine Bucket
            bucket = "NEUTRAL"
            if roc >= 3: 
                bucket = "STRONG_BULLISH"
            elif roc > 0: 
                bucket = "MODERATE_BULLISH"
            elif roc <= -3: 
                bucket = "STRONG_BEARISH"
            elif roc < 0: 
                bucket = "MODERATE_BEARISH"
                
            mapped_results.append({
                "symbol": r["symbol"],
                "ltp": r["current_price"],
                "prev_close": r["current_price"], # Approximation for DB fallback
                "change_pct": roc,
                "momentum_score": score,
                "bucket": bucket,
                "pct_bucket": "0%", # Placeholder
                "direction": "Bullish" if roc > 0 else "Bearish",
                "correlation": 0.5, # Default
                "source": "DB_FALLBACK",
                "confidence": "LOW",
                "last_update": datetime.now().isoformat()
            })
            
        return {
            "type": "bucket_update",
            "data": mapped_results,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Momentum DB fallback failed: {e}")
        return []

@router.get("/week52-breakouts")
async def get_week52_breakouts(
    force_refresh: bool = False,
    current_user: User = Depends(get_current_user)
):
    """Get stocks making new 52-week highs and 52-week low breakdowns."""
    
    # 1. Try HP Cache (Real-Time Engine) first
    try:
        hp_data = cache_get(CacheKeys.breakout())
        if hp_data and not force_refresh:
            high_breakouts = [m for m in hp_data if m.get("breakout_type") in ["52W_HIGH", "Yearly High", "Breakout"]]
            low_breakdowns = [m for m in hp_data if m.get("breakout_type") in ["52W_LOW", "Yearly Low"]]
            
            # Map legacy types if needed (RealTimeEngine uses "52W_HIGH" etc., Frontend might expect same or mapped)
            # Frontend code shows it handles "Breakout", "Yearly High", "Yearly Low".
            # RealTimeEngine produces "52W_HIGH", "Yearly High", "52W_LOW", "Yearly Low".
            # Let's align types to be safe.
            
            return {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "data": hp_data,
                "high_breakouts": high_breakouts,
                "low_breakdowns": low_breakdowns,
                "summary": {
                    "total_results": len(hp_data),
                    "total_high_breakouts": len(high_breakouts),
                    "total_low_breakdowns": len(low_breakdowns),
                    "source": "RealTime-Engine (HP Cache)"
                }
            }
    except Exception as e:
        logger.warning(f"HP Cache read failed for week52: {e}")

    # 2. Fallback to Legacy Engine (DB/Scan)
    from services.yearly_breakout_engine import YearlyBreakoutEngine
    
    try:
        engine = YearlyBreakoutEngine()
        results = await engine.get_cached_results()
        
        # If cache is empty or force refresh, run the scanner
        if not results or force_refresh:
            logger.info("week52-breakouts: Cache empty or refresh requested, running scanner...")
            # Note: This is slow (30s timeout)
            await engine.run_scanner(timeout=15.0)
            results = await engine.get_cached_results()
        
        # Map to frontend structure
        mapped_results = []
        for res in results:
            # Normalize breakout_type from engine to frontend format
            breakout_type = res.get("breakout_type", "")
            if breakout_type == "Breakout":
                breakout_type = "52W_HIGH"
            elif breakout_type == "Yearly High":
                breakout_type = "Yearly High"
            elif breakout_type == "Yearly Low":
                breakout_type = "52W_LOW"
            
            # Calculate breakout_pct for frontend (positive for high, negative for low)
            breakout_pct = res.get("breakout_pct", 0)
            if breakout_type in ["52W_HIGH", "Yearly High"]:
                breakout_pct = abs(breakout_pct)  # Ensure positive for highs
            elif breakout_type in ["52W_LOW", "Yearly Low"]:
                breakout_pct = -abs(breakout_pct) if breakout_pct > 0 else breakout_pct  # Negative for lows

            mapped_results.append({
                "symbol": res.get("symbol"),
                "ltp": res.get("current_price"),
                "high_52w": res.get("yearly_high"),
                "low_52w": res.get("yearly_low"),
                "prev_close": res.get("current_price"), 
                "change_pct": res.get("change_pct", 0),
                "breakout_type": breakout_type,
                "breakout_pct": round(breakout_pct, 2),
                "volume_ratio": res.get("volume_ratio", 1.0),
                "volume_strength": res.get("volume_strength", "Normal"),
                "industry": res.get("industry", "N/A"),
                "last_update": res.get("timestamp")
            })

        high_breakouts = [m for m in mapped_results if m.get("breakout_type") in ["52W_HIGH", "Yearly High", "Breakout"]]
        low_breakdowns = [m for m in mapped_results if m.get("breakout_type") in ["52W_LOW", "Yearly Low"]]
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "data": mapped_results,
            "high_breakouts": high_breakouts,
            "low_breakdowns": low_breakdowns,
            "summary": {
                "total_results": len(mapped_results),
                "total_high_breakouts": len(high_breakouts),
                "total_low_breakdowns": len(low_breakdowns),
                "source": "Upstox-Engine"
            }
        }
    except Exception as e:
        logger.error(f"52-week breakout API error: {e}")
        return {
            "status": "error",
            "message": str(e),
            "high_breakouts": [],
            "low_breakdowns": []
        }
