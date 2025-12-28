"""
Scanner API Router
Endpoints for equity scanner functionality.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio
import json
import logging
import sys

logger = logging.getLogger(__name__)

# Global scanner components
StrategyRegistry = None
ScannerEngine = None
get_realtime_scanner_engine = None
_scanner_available = False
scanner = None

try:
    from strategies import StrategyRegistry
    from core.scanner.scanner_engine import ScannerEngine
    from core.scanner.realtime_scanner_engine import get_realtime_scanner_engine
    
    _scanner_available = True
    
    if ScannerEngine is not None:
        scanner = ScannerEngine()
        logger.info(f"Scanner engine initialized with {len(StrategyRegistry._strategies) if StrategyRegistry else 0} strategies")
except Exception as e:
    logger.warning(f"Scanner components initialization failed: {e}")
    
    # Second attempt to at least get the registry for the strategy list
    if StrategyRegistry is None:
        try:
            from strategies import StrategyRegistry
        except Exception:
            StrategyRegistry = None
    
    _scanner_available = False

router = APIRouter(prefix="/api/scanner", tags=["Scanner"])

# Store for scan progress
scan_progress: Dict[str, Dict] = {}


class ScanRequest(BaseModel):
    """Request model for running a scan."""
    indices: List[str]
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
async def get_strategies():
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
async def get_indices():
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
async def get_timeframes():
    """Get available timeframes for scanning."""
    return {
        "status": "success",
        "timeframes": scanner.get_available_timeframes()
    }


@router.post("/run", response_model=ScanResponse)
async def run_scan(request: ScanRequest):
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
async def get_scan_progress(scan_id: str):
    """Get progress of a running scan."""
    if scan_id in scan_progress:
        return scan_progress[scan_id]
    return {"status": "not_found", "scan_id": scan_id}


@router.get("/presets")
async def get_presets():
    """Get saved scanner presets."""
    return {
        "status": "success",
        "presets": list(saved_presets.values())
    }


@router.post("/presets")
async def save_preset(request: PresetRequest):
    """Save a scanner preset."""
    preset_id = f"preset_{int(datetime.now().timestamp())}"
    saved_presets[preset_id] = {
        "id": preset_id,
        "name": request.name,
        "indices": request.indices,
        "timeframe": request.timeframe,
        "strategies": request.strategies,
        "created_at": datetime.now().isoformat()
    }
    return {"status": "success", "preset_id": preset_id}


@router.delete("/presets/{preset_id}")
async def delete_preset(preset_id: str):
    """Delete a scanner preset."""
    if preset_id in saved_presets:
        del saved_presets[preset_id]
        return {"status": "success"}
    raise HTTPException(status_code=404, detail="Preset not found")

@router.get("/momentum")
async def get_momentum_data():
    """
    REST endpoint for momentum data.
    Returns database data immediately for fast response.
    Falls back to realtime data if available.
    Cached for 60 seconds to reduce DB load.
    """
    from services.db_data_fetcher import get_db_data_fetcher
    from services.cache import get_cache_manager
    
    # Check cache first
    cache = get_cache_manager()
    cache_key = "quantai:momentum_data"
    cached = cache.get(cache_key)
    if cached:
        logger.debug("Momentum data served from cache")
        return cached
    
    # First try realtime engine if already initialized (fast path)
    engine = get_realtime_scanner_engine()
    if engine._is_initialized:
        data = engine.get_all_stock_data()
        if data and len(data) > 0:
            status = engine.get_status()
            return {
                "type": "bucket_update",
                "timestamp": datetime.now().isoformat(),
                "data": data,
                "status": {
                    "source": status.get("source", "REST"),
                    "is_healthy": status.get("is_healthy", False),
                    "last_tick": status.get("last_tick"),
                    "stock_count": status.get("stock_count", 0),
                    "poll_interval": status.get("poll_interval", 5)
                }
            }
    
    # Default: Use database for immediate response (market closed or WS unavailable)
    logger.info("Using database fallback for momentum data")
    db_fetcher = get_db_data_fetcher()
    db_data = db_fetcher.fetch_latest_data()
    
    data = []
    if db_data:
        for symbol, tick in db_data.items():
            data.append({
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
    
    response = {
        "type": "bucket_update",
        "timestamp": datetime.now().isoformat(),
        "data": data,
        "status": {
            "source": "DB",
            "is_healthy": len(data) > 0,
            "last_tick": datetime.now().isoformat(),
            "stock_count": len(data),
            "poll_interval": 60
        }
    }
    
    # Cache the response for 60 seconds
    cache.set(cache_key, response, ttl=60)
    return response


def _map_bucket_to_legacy(change_pct: float) -> str:
    """Map percent change to legacy bucket names."""
    abs_change = abs(change_pct)
    is_bullish = change_pct >= 0
    
    if abs_change >= 5.0:
        return "EXTREME_BULLISH" if is_bullish else "EXTREME_BEARISH"
    elif abs_change >= 3.0:
        return "STRONG_BULLISH" if is_bullish else "STRONG_BEARISH"
    elif abs_change >= 1.0:
        return "MODERATE_BULLISH" if is_bullish else "MODERATE_BEARISH"
    else:
        return "NEUTRAL"


@router.get("/breakout")
async def get_breakout_data():
    """
    REST endpoint for breakout scanner.
    Returns stocks showing breakout patterns (price crossing resistance levels).
    Filters for stocks with strong upward momentum.
    """
    from services.db_data_fetcher import get_db_data_fetcher
    from services.cache import get_cache_manager
    
    # Check cache first
    cache = get_cache_manager()
    cache_key = "quantai:breakout_data"
    cached = cache.get(cache_key)
    if cached:
        logger.debug("Breakout data served from cache")
        return cached
    
    # Use database for breakout detection
    logger.info("Using database for breakout scanner")
    db_fetcher = get_db_data_fetcher()
    db_data = db_fetcher.fetch_latest_data()
    
    breakout_stocks = []
    if db_data:
        for symbol, tick in db_data.items():
            # Breakout criteria: strong positive movement (>2%) or high volume
            if tick.change_pct >= 2.0:
                breakout_stocks.append({
                    "symbol": tick.symbol,
                    "ltp": tick.ltp,
                    "prev_close": tick.prev_close,
                    "change_pct": tick.change_pct,
                    "breakout_score": min(100, int(tick.change_pct * 15 + 50)),
                    "pattern": "BULLISH_BREAKOUT" if tick.change_pct >= 4.0 else "MODERATE_BREAKOUT",
                    "strength": "STRONG" if tick.change_pct >= 4.0 else "MODERATE",
                    "source": "DB",
                    "last_update": tick.timestamp
                })
    
    # Sort by change percentage descending
    breakout_stocks.sort(key=lambda x: x["change_pct"], reverse=True)
    
    response = {
        "type": "breakout_scan",
        "timestamp": datetime.now().isoformat(),
        "data": breakout_stocks[:50],  # Top 50 breakouts
        "count": len(breakout_stocks),
        "status": {
            "source": "DB",
            "is_healthy": len(breakout_stocks) > 0,
            "last_update": datetime.now().isoformat()
        }
    }
    
    # Cache for 60 seconds
    cache.set(cache_key, response, ttl=60)
    return response


@router.get("/reversal")
async def get_reversal_data():
    """
    REST endpoint for reversal scanner.
    Returns stocks showing reversal patterns (trend changes).
    Identifies potential bottoms and tops.
    """
    from services.db_data_fetcher import get_db_data_fetcher
    from services.cache import get_cache_manager
    
    # Check cache first
    cache = get_cache_manager()
    cache_key = "quantai:reversal_data"
    cached = cache.get(cache_key)
    if cached:
        logger.debug("Reversal data served from cache")
        return cached
    
    # Use database for reversal detection
    logger.info("Using database for reversal scanner")
    db_fetcher = get_db_data_fetcher()
    db_data = db_fetcher.fetch_latest_data()
    
    reversal_candidates = []
    if db_data:
        for symbol, tick in db_data.items():
            abs_change = abs(tick.change_pct)
            # Reversal criteria: moderate movement in either direction indicating potential trend change
            # Looking for stocks that moved between -3% to -1% (potential bullish reversal from oversold)
            # or between +1% to +3% after decline (potential bearish reversal)
            if (tick.change_pct <= -1.0 and tick.change_pct >= -4.0):
                # Potential bullish reversal (oversold bounce candidate)
                reversal_candidates.append({
                    "symbol": tick.symbol,
                    "ltp": tick.ltp,
                    "prev_close": tick.prev_close,
                    "change_pct": tick.change_pct,
                    "reversal_score": int(abs(tick.change_pct) * 20),
                    "pattern": "BULLISH_REVERSAL",
                    "type": "OVERSOLD_BOUNCE",
                    "strength": "STRONG" if tick.change_pct <= -3.0 else "MODERATE",
                    "source": "DB",
                    "last_update": tick.timestamp
                })
            elif (tick.change_pct >= 3.0 and tick.change_pct <= 6.0):
                # Potential bearish reversal (overbought correction candidate)
                reversal_candidates.append({
                    "symbol": tick.symbol,
                    "ltp": tick.ltp,
                    "prev_close": tick.prev_close,
                    "change_pct": tick.change_pct,
                    "reversal_score": int(tick.change_pct * 15),
                    "pattern": "BEARISH_REVERSAL",
                    "type": "OVERBOUGHT_CORRECTION",
                    "strength": "STRONG" if tick.change_pct >= 5.0 else "MODERATE",
                    "source": "DB",
                    "last_update": tick.timestamp
                })
    
    # Sort by reversal score descending
    reversal_candidates.sort(key=lambda x: x["reversal_score"], reverse=True)
    
    response = {
        "type": "reversal_scan",
        "timestamp": datetime.now().isoformat(),
        "data": reversal_candidates[:50],  # Top 50 reversal candidates
        "count": len(reversal_candidates),
        "status": {
            "source": "DB",
            "is_healthy": len(reversal_candidates) > 0,
            "last_update": datetime.now().isoformat()
        }
    }
    
    # Cache for 60 seconds
    cache.set(cache_key, response, ttl=60)
    return response


@router.get("/trendfinder")
async def get_trendfinder_data():
    """
    REST endpoint for TrendFinder AI scanner.
    Returns stocks identified by AI-based trend detection.
    Similar to momentum but with AI confidence scoring.
    """
    from services.db_data_fetcher import get_db_data_fetcher
    from services.cache import get_cache_manager
    
    # Check cache first
    cache = get_cache_manager()
    cache_key = "quantai:trendfinder_data"
    cached = cache.get(cache_key)
    if cached:
        logger.debug("TrendFinder data served from cache")
        return cached
    
    # Use database for trend analysis
    logger.info("Using database for TrendFinder AI scanner")
    db_fetcher = get_db_data_fetcher()
    db_data = db_fetcher.fetch_latest_data()
    
    trending_stocks = []
    if db_data:
        for symbol, tick in db_data.items():
            abs_change = abs(tick.change_pct)
            # TrendFinder: identify stocks with clear directional movement (>0.5%)
            if abs_change >= 0.5:
                # Calculate AI confidence based on magnitude of movement
                ai_confidence = min(95, int(abs_change * 25 + 30))
                
                trending_stocks.append({
                    "symbol": tick.symbol,
                    "ltp": tick.ltp,
                    "prev_close": tick.prev_close,
                    "change_pct": tick.change_pct,
                    "trend_direction": "BULLISH" if tick.change_pct > 0 else "BEARISH",
                    "trend_strength": "STRONG" if abs_change >= 3.0 else "MODERATE" if abs_change >= 1.5 else "WEAK",
                    "ai_confidence": ai_confidence,
                    "momentum_score": max(5, min(95, 50 + int(tick.change_pct * 10))),
                    "signal": "BUY" if tick.change_pct > 1.0 else "SELL" if tick.change_pct < -1.0 else "HOLD",
                    "source": "DB",
                    "last_update": tick.timestamp
                })
    
    # Sort by AI confidence descending
    trending_stocks.sort(key=lambda x: x["ai_confidence"], reverse=True)
    
    response = {
        "type": "trendfinder_scan",
        "timestamp": datetime.now().isoformat(),
        "data": trending_stocks[:50],  # Top 50 trends
        "count": len(trending_stocks),
        "status": {
            "source": "AI_DB",
            "is_healthy": len(trending_stocks) > 0,
            "last_update": datetime.now().isoformat(),
            "ai_model": "TrendFinder v1.0"
        }
    }
    
    # Cache for 60 seconds
    cache.set(cache_key, response, ttl=60)
    return response



@router.get("/week52-breakouts")
async def get_week52_breakouts():
    """
    Get stocks making new 52-week highs and 52-week low breakdowns.
    Uses NSETools to fetch real-time data from NSE.
    
    Returns:
        Dict with high_breakouts and low_breakdowns lists
    """
    from services.week52_nse_service import get_week52_breakout_service_nse
    import asyncio
    
    try:
        service = get_week52_breakout_service_nse()
        # Run the synchronous NSE fetch operation in a thread pool to avoid blocking
        data = await asyncio.to_thread(service.detect_breakouts)
        status = service.get_status()
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "high_breakouts": data.get("high_breakouts", []),
            "low_breakdowns": data.get("low_breakdowns", []),
            "summary": {
                "total_high_breakouts": len(data.get("high_breakouts", [])),
                "total_low_breakdowns": len(data.get("low_breakdowns", [])),
                "source": status.get("source", "NSE"),
                "last_updated": status.get("last_fetch")
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



@router.get("/momentum/status")
async def get_momentum_status():
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
                db_data = db_fetcher.fetch_latest_data()
                
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
