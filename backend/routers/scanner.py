"""
Scanner API Router
Endpoints for equity scanner functionality.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import asyncio
import json
import logging
import sys

from services.live_price_enricher import enrich_scanner_results

from models import User, ScannerPreset
from database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import select
from utils.auth import get_current_user, get_current_user
from services.dragonfly_client import get_cache
from config import settings

logger = logging.getLogger(__name__)

# Global scanner components
StrategyRegistry = None
ScannerEngine = None
get_realtime_scanner_engine = None
_scanner_available = False
scanner = None

# 1. Robust Strategy Registry Loading
try:
    from strategies import StrategyRegistry
    # Explicitly import all tiers to force registration
    import strategies.tier1
    import strategies.tier2
    import strategies.tier3
    import strategies.multi_timeframe
    
    if StrategyRegistry:
        logger.info(f"StrategyRegistry loaded successfully with {len(StrategyRegistry.get_all())} strategies")
except Exception as e:
    logger.error(f"StrategyRegistry initialization failed: {e}")

# 2. Scanner Engine Loading (Independent of Registry)
try:
    from core.scanner.scanner_engine import ScannerEngine
    from core.scanner.realtime_scanner_engine import get_realtime_scanner_engine
    
    if ScannerEngine is not None:
        scanner = ScannerEngine()
        _scanner_available = True
        logger.info("Scanner Engine initialized successfully")
except Exception as e:
    logger.warning(f"Scanner engine initialization failed: {e}")
    _scanner_available = False

router = APIRouter(prefix="/api/scanner", tags=["Scanner"])

def get_cached_scanner_data(key: str):
    """Get data from cache if valid."""
    cache = get_cache()
    if not cache.is_available():
        return None
    try:
        return cache.get(f"qai:scanner:route:{key}")
    except Exception as e:
        logger.error(f"Scanner cache get error for {key}: {e}")
        return None

def set_cached_scanner_data(key: str, data: Dict, ttl: int = 300):
    """Set data in cache with TTL (default 5 minutes)."""
    cache = get_cache()
    if not cache.is_available():
        return
    try:
        cache.set(f"qai:scanner:route:{key}", data, ttl=ttl)
    except Exception as e:
        logger.error(f"Scanner cache set error for {key}: {e}")

# Store for scan progress
scan_progress: Dict[str, Dict] = {}


class ScanRequest(BaseModel):
    """Request model for running a scan."""
    indices: List[str] = Field(..., min_length=1, description="List of indices to scan")
    timeframe: str
    strategies: List[str]


class ScanResponse(BaseModel):
    """Response model for scan results."""
    status: str
    scan_id: str
    results: List[Dict[str, Any]]
    total_stocks: int
    signals_found: int
    duration_seconds: float


class PresetRequest(BaseModel):
    """Request model for saving a preset."""
    name: str
    indices: List[str]
    timeframe: str
    strategies: List[str]


# In-memory preset storage (use DB in production)
saved_presets: Dict[str, Dict] = {}




@router.get("/strategies")
async def get_strategies(current_user: User = Depends(get_current_user)):
    """Get all available scanning strategies grouped by tier."""
    # Check if StrategyRegistry is available (set to None if import failed)
    if StrategyRegistry is None:
        logger.warning("StrategyRegistry not available - returning fallback strategies")
        return {
            "status": "success",
            "strategies": {
                "Tier 1 - Highest Win Rate": [
                    {"name": "RSI Mean Reversion", "description": "Identifies oversold/overbought conditions", "tier": "Tier 1 - Highest Win Rate"}
                ],
                "Tier 2 - Solid Strategies": [
                    {"name": "MACD Crossover", "description": "Classic MACD signal line crossover", "tier": "Tier 2 - Solid Strategies"}
                ],
                "Tier 3 - Advanced Strategies": [],
                "Multi-Timeframe Confluence": []
            },
            "total_count": 2
        }
    
    # Get all registered strategies
    strategies = StrategyRegistry.list_strategies()
    
    # Group by tier
    grouped = {
        "Tier 1 - Highest Win Rate": [],
        "Tier 2 - Solid Strategies": [],
        "Tier 3 - Advanced Strategies": [],
        "Multi-Timeframe Confluence": []
    }
    
    for s in strategies:
        tier = s.get("tier", "Tier 3 - Advanced Strategies")
        if tier in grouped:
            grouped[tier].append(s)
        else:
            grouped["Tier 3 - Advanced Strategies"].append(s)
    
    return {
        "status": "success",
        "strategies": grouped,
        "total_count": len(strategies)
    }


@router.get("/indices")
async def get_indices(current_user: User = Depends(get_current_user)):
    """Get available indices for scanning."""
    try:
        return {
            "status": "success",
            "indices": scanner.get_available_indices()
        }
    except Exception as e:
        logger.error(f"Error getting indices: {e}")
        return {
            "status": "success",
            "indices": [
                {"name": "NIFTY 50", "symbol": "^NSEI", "count": 50},
                {"name": "NIFTY 100", "symbol": "^NSE100", "count": 100},
                {"name": "NIFTY 200", "symbol": "^NSE200", "count": 200}
            ]
        }


@router.get("/timeframes")
async def get_timeframes(current_user: User = Depends(get_current_user)):
    """Get available timeframes for scanning."""
    return {
        "status": "success",
        "timeframes": scanner.get_available_timeframes()
    }


@router.post("/run", response_model=ScanResponse)
async def run_scan(request: ScanRequest, current_user: User = Depends(get_current_user)):
    """
    Execute scanner with selected parameters.
    Returns scan results sorted by confidence.
    """
    start_time = datetime.now()
    scan_id = f"scan_{int(start_time.timestamp())}"
    
    logger.info(f"Starting scan {scan_id}: {request.indices}, {request.timeframe}, {len(request.strategies)} strategies")
    
    try:
        # Run the scan
        results = await scanner.run_scan(
            indices=request.indices,
            timeframe=request.timeframe,
            strategies=request.strategies
        )
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return ScanResponse(
            status="success",
            scan_id=scan_id,
            results=results,
            total_stocks=len(set(r["symbol"] for r in results)) if results else 0,
            signals_found=len(results),
            duration_seconds=round(duration, 2)
        )
        
    except Exception as e:
        logger.error(f"Scan failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/progress/{scan_id}")
async def get_scan_progress(scan_id: str, current_user: User = Depends(get_current_user)):
    """Get progress of a running scan."""
    if scan_id in scan_progress:
        return scan_progress[scan_id]
    return {"status": "not_found", "scan_id": scan_id}


@router.get("/presets")
async def get_presets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get saved scanner presets."""
    try:
        stmt = select(ScannerPreset).where(ScannerPreset.user_id == current_user.id)
        result = await db.execute(stmt)
        presets = result.scalars().all()
    except Exception as e:
        logger.warning(f"Failed to fetch presets (table may be missing): {e}")
        presets = []
    return {
        "status": "success",
        "presets": [
            {
                "id": str(p.id),
                "name": p.name,
                "indices": p.indices,
                "timeframe": p.timeframe,
                "strategies": p.strategies,
                "created_at": p.created_at.isoformat() if p.created_at else None
            } for p in presets
        ]
    }


@router.post("/presets")
async def save_preset(
    request: PresetRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save a scanner preset."""
    preset = ScannerPreset(
        user_id=current_user.id,
        name=request.name,
        indices=request.indices,
        timeframe=request.timeframe,
        strategies=request.strategies
    )
    db.add(preset)
    await db.commit()
    await db.refresh(preset)
    return {"status": "success", "preset_id": str(preset.id)}


@router.delete("/presets/{preset_id}")
async def delete_preset(
    preset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a scanner preset."""
    stmt = select(ScannerPreset).where(
        ScannerPreset.id == preset_id,
        ScannerPreset.user_id == current_user.id
    )
    result = await db.execute(stmt)
    preset = result.scalar_one_or_none()
    if preset:
        await db.delete(preset)
        await db.commit()
        return {"status": "success", "message": "Preset deleted"}
    raise HTTPException(status_code=404, detail="Preset not found")

@router.get("/momentum")
async def get_momentum_data(current_user: User = Depends(get_current_user)):
    """
    REST endpoint for momentum data.
    Delegates to ScannerEngine.
    """
    if not _scanner_available or scanner is None:
        raise HTTPException(status_code=503, detail="Scanner engine not available")
    
    return await scanner.get_momentum_scan()






@router.get("/breakout")
async def get_breakout_data(current_user: User = Depends(get_current_user)):
    """
    REST endpoint for breakout scanner.
    Delegates to ScannerEngine.
    """
    if not _scanner_available or scanner is None:
        raise HTTPException(status_code=503, detail="Scanner engine not available")
        
    return await scanner.get_breakout_scan()


@router.get("/reversal")
async def get_reversal_data(current_user: User = Depends(get_current_user)):
    """
    REST endpoint for reversal scanner.
    Delegates to ScannerEngine.
    """
    if not _scanner_available or scanner is None:
        raise HTTPException(status_code=503, detail="Scanner engine not available")
        
    return await scanner.get_reversal_scan()


@router.get("/trendfinder")
async def get_trendfinder_data(current_user: User = Depends(get_current_user)):
    """REST endpoint for TrendFinder AI scanner. Delegates to ScannerEngine."""
    if not _scanner_available or scanner is None:
        raise HTTPException(status_code=503, detail="Scanner engine not available")
        
    return await scanner.get_trendfinder_scan()



@router.get("/week52-breakouts")
async def get_week52_breakouts(current_user: User = Depends(get_current_user)):
    """Get stocks making new 52-week highs and 52-week low breakdowns."""
    # 1. Check Route Cache
    cached = get_cached_scanner_data("week52-breakouts")
    if cached:
        # Enrich cached stocks with live prices
        try:
            if isinstance(cached, dict) and "data" in cached and cached["data"]:
                access_token = settings.UPSTOX_ACCESS_TOKEN
                enrich_results = await enrich_scanner_results(cached["data"], access_token)
                
                # Re-map high/low lists after enrichment since price changed
                cached["data"] = enrich_results
                cached["high_breakouts"] = [m for m in enrich_results if m.get("breakout_type") == "52W_HIGH"]
                cached["low_breakdowns"] = [m for m in enrich_results if m.get("breakout_type") == "52W_LOW"]
                
        except Exception as e:
            logger.error(f"week52-breakouts: Failed to enrich cached results: {e}")
        return cached

    from services.yearly_breakout_engine import YearlyBreakoutEngine
    
    try:
        engine = YearlyBreakoutEngine()
        results = await engine.get_cached_results()
        
        # If cache is empty, try to run the scanner (this may take time)
        if not results:
            logger.info("week52-breakouts: Cache empty, running scanner...")
            try:
                await engine.run_scanner()
                results = await engine.get_cached_results()
            except Exception as scan_error:
                logger.error(f"week52-breakouts: Scanner failed: {scan_error}")
                # Return empty result with informative message
                return {
                    "status": "pending",
                    "message": "52-week breakout scan is in progress. Please try again in a few minutes.",
                    "high_breakouts": [],
                    "low_breakdowns": [],
                    "data": []
                }
        
        # Map to frontend structure
        mapped_results = []
        for res in results:
            # Normalize breakout_type from engine to frontend format
            breakout_type = res.get("breakout_type", "")
            if breakout_type == "Breakout" or breakout_type == "Yearly High":
                breakout_type = "52W_HIGH"
            elif breakout_type == "Yearly Low":
                breakout_type = "52W_LOW"
            
            # Calculate breakout_pct for frontend (positive for high, negative for low)
            breakout_pct = res.get("breakout_pct", 0)
            if breakout_type == "52W_HIGH":
                breakout_pct = abs(breakout_pct)  # Ensure positive for highs
            elif breakout_type == "52W_LOW":
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

        high_breakouts = [m for m in mapped_results if m.get("breakout_type") == "52W_HIGH"]
        low_breakdowns = [m for m in mapped_results if m.get("breakout_type") == "52W_LOW"]
        
        response = {
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
        
        set_cached_scanner_data("week52-breakouts", response)
        return response
    except Exception as e:
        logger.error(f"52-week breakout API error: {e}")
        return {
            "status": "error",
            "message": str(e),
            "high_breakouts": [],
            "low_breakdowns": []
        }



@router.get("/momentum/status")
async def get_momentum_status(current_user: User = Depends(get_current_user)):
    """Get current status of the momentum data feed."""
    engine = get_realtime_scanner_engine()
    return engine.get_status()


@router.websocket("/ws/scanner")
async def scanner_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time scanner updates.
    Includes data source status (WS/REST) for UI display.
    """
    await websocket.accept()
    engine = get_realtime_scanner_engine()
    
    # Initialize the engine if not already done
    if not engine._is_initialized:
        try:
            await engine.initialize()
        except Exception as e:
            logger.warning(f"Engine initialization warning: {e}")
    
    logger.info("New WebSocket connection to /ws/scanner")
    
    try:
        while True:
            # Get current data and status
            data = engine.get_all_stock_data()
            status = engine.get_status()
            
            # If no real-time data, use DB fallback
            if not data or len(data) == 0:
                from services.db_data_fetcher import get_db_data_fetcher
                db_fetcher = get_db_data_fetcher()
                db_data = await asyncio.to_thread(db_fetcher.fetch_latest_data)
                
                fallback_data = []
                for symbol, tick in db_data.items():
                    fallback_data.append({
                        "symbol": tick.symbol,
                        "ltp": tick.ltp,
                        "prev_close": tick.prev_close,
                        "change_pct": tick.change_pct,
                        "momentum_score": max(5, min(95, 50 + int(tick.change_pct * 10))),
                        "bucket": _map_bucket_to_legacy(tick.change_pct),
                        "pct_bucket": tick.bucket,
                        "direction": tick.direction,
                        "correlation": 0.5,
                        "source": "DB",
                        "confidence": "LOW",
                        "last_update": tick.timestamp
                    })
                data = fallback_data
                status = {
                    "source": "DB",
                    "is_healthy": len(data) > 0,
                    "last_tick": datetime.now().isoformat(),
                    "stock_count": len(data),
                    "poll_interval": 60
                }
            
            await websocket.send_json({
                "type": "bucket_update",
                "timestamp": datetime.now().isoformat(),
                "data": data,
                "indices": engine.get_indices(),
                "status": status
            })
            await asyncio.sleep(1)
            
            # Check for messages from client
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=0.01)
            except asyncio.TimeoutError:
                pass
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected from /ws/scanner")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close()
        except:
            pass
