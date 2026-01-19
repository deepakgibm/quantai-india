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
from utils.auth import get_current_user, get_optional_user
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
async def get_strategies(current_user: Optional[User] = Depends(get_optional_user)):
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
    
    During market hours: Returns live HP scanner data
    After market hours: Returns cached EOD snapshot
    """
    from utils.market_state import is_market_open, get_trading_date
    from services.dragonfly_client import get_cache
    
    # Check if market is closed - return snapshot
    if not is_market_open():
        cache = get_cache()
        date_str = get_trading_date().strftime("%Y-%m-%d")
        snapshot = cache.get(f"snapshot:scanner_momentum:{date_str}")
        
        if snapshot and snapshot.get("data"):
            logger.info(f"Momentum: returning EOD snapshot ({date_str})")
            return {
                "type": "bucket_update",
                "timestamp": datetime.now().isoformat(),
                "data": snapshot["data"],
                "status": {
                    "source": "EOD_SNAPSHOT",
                    "is_healthy": True,
                    "stock_count": len(snapshot["data"]),
                    "trade_date": date_str,
                    "market_status": "CLOSED"
                }
            }
    
    # Market is open - use live data
    # 1. Check Route Cache
    cached = get_cached_scanner_data("momentum")
    if cached:
        # Enrich cached stocks with live prices
        try:
            if isinstance(cached, dict) and "data" in cached and cached["data"]:
                access_token = settings.UPSTOX_ACCESS_TOKEN
                cached["data"] = await enrich_scanner_results(cached["data"], access_token)
        except Exception as e:
            logger.error(f"momentum: Failed to enrich cached results: {e}")
        return cached

    from services.cache import get_cache_manager
    
    # 2. Check HP Engine Cache (Fastest)
    cache = get_cache_manager()
    cache_key = "quantai:momentum_data"
    # ... existing cache logic ...
    
    # Fast path: Try HP scanner snapshots (in-memory, <50ms)
    try:
        from engine.scanner_service import get_scanner_service
        hp_service = get_scanner_service()
        if hp_service._is_running:
            snapshots = hp_service.get_all_snapshots()
            if snapshots and len(snapshots) > 0:
                # Map to expected format
                data = []
                for s in snapshots[:500]: # Cap snapshot count
                    data.append({
                        "symbol": s.get("symbol"),
                        "ltp": s.get("ltp", 0),
                        "prev_close": s.get("prev_close", 0),
                        "change_pct": s.get("change_pct", 0),
                        "momentum_score": max(5, min(95, 50 + int(s.get("change_pct", 0) * 10))),
                        "bucket": s.get("momentum_bucket", "NEUTRAL"),
                        "direction": "UP" if s.get("change_pct", 0) > 0 else "DOWN",
                        "source": "HP_ENGINE",
                        "confidence": "HIGH" if s.get("signal_strength", 0) > 50 else "MEDIUM",
                        "active_strategies": s.get("active_strategies", []),
                        "last_update": s.get("updated_at")
                    })
                
                # Enrich top results with LIVE prices
                enriched_data = await enrich_scanner_results(data[:100])
                if len(data) > 100:
                    enriched_data.extend(data[100:])
                
                response = {
                    "type": "bucket_update",
                    "timestamp": datetime.now().isoformat(),
                    "data": enriched_data,
                    "status": {
                        "source": "HP_ENGINE_ENRICHED",
                        "is_healthy": True,
                        "stock_count": len(enriched_data),
                        "poll_interval": 5
                    }
                }
                set_cached_scanner_data("momentum", response)
                return response
    except Exception as e:
        logger.debug(f"HP scanner fallback: {e}")
    
    # Last resort: Use database (Optimized loop)
    from services.db_data_fetcher import get_db_data_fetcher
    logger.info("Using database fallback for momentum data")
    db_fetcher = get_db_data_fetcher()
    db_data = await asyncio.to_thread(db_fetcher.fetch_latest_data)
    
    data = []
    if db_data:
        count = 0
        for symbol, tick in db_data.items():
            if count > 200: break # Safety cap
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
            count += 1
    
    # Enrich database fallback with LIVE prices
    enriched_data = await enrich_scanner_results(data[:50])
    
    response = {
        "type": "bucket_update",
        "timestamp": datetime.now().isoformat(),
        "data": enriched_data,
        "status": {
            "source": "DB_ENRICHED",
            "is_healthy": len(enriched_data) > 0,
            "last_tick": datetime.now().isoformat(),
            "stock_count": len(enriched_data),
            "poll_interval": 60
        }
    }
    
    set_cached_scanner_data("momentum", response)
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
async def get_breakout_data(current_user: User = Depends(get_optional_user)):
    """
    REST endpoint for breakout scanner.
    
    During market hours: Returns live breakout data
    After market hours: Returns cached EOD snapshot
    """
    import time
    from utils.market_state import is_market_open, get_trading_date
    from services.dragonfly_client import get_cache as get_df_cache
    
    start_time = time.time()
    
    # Check if market is closed - return snapshot
    if not is_market_open():
        cache = get_df_cache()
        date_str = get_trading_date().strftime("%Y-%m-%d")
        snapshot = cache.get(f"snapshot:scanner_breakout:{date_str}")
        
        if snapshot and snapshot.get("data"):
            logger.info(f"Breakout: returning EOD snapshot ({date_str})")
            return {
                "type": "breakout_scan",
                "timestamp": datetime.now().isoformat(),
                "data": snapshot["data"],
                "count": len(snapshot["data"]),
                "status": {
                    "source": "EOD_SNAPSHOT",
                    "is_healthy": True,
                    "trade_date": date_str,
                    "market_status": "CLOSED"
                }
            }
    
    # Market is open - use live data
    # 1. Check Route Cache (5 min TTL)
    cached = get_cached_scanner_data("breakout")
    if cached:
        logger.info(f"breakout: Cache hit in {(time.time()-start_time)*1000:.0f}ms")
        # Enrich cached stocks with live prices
        try:
            if isinstance(cached, dict) and "data" in cached and cached["data"]:
                access_token = settings.UPSTOX_ACCESS_TOKEN
                cached["data"] = await enrich_scanner_results(cached["data"], access_token)
        except Exception as e:
            logger.error(f"breakout: Failed to enrich cached results: {e}")
        return cached

    from services.db_data_fetcher import get_db_data_fetcher
    from services.cache import get_cache_manager
    from services.dragonfly_client import cache_get, CacheKeys
    
    # 2. Check HP Scanner v3 Cache (Super Fast, <50ms)
    try:
        hp_breakout = cache_get(CacheKeys.breakout()) if hasattr(CacheKeys, 'breakout') else None
        if hp_breakout and len(hp_breakout) > 0:
            response = {
                "type": "breakout_scan",
                "timestamp": datetime.now().isoformat(),
                "data": hp_breakout[:50],
                "count": len(hp_breakout),
                "status": {
                    "source": "HP_SCANNER_CACHE",
                    "is_healthy": True,
                    "last_update": datetime.now().isoformat()
                }
            }
            set_cached_scanner_data("breakout", response, ttl=300)
            logger.info(f"breakout: HP cache hit in {(time.time()-start_time)*1000:.0f}ms")
            return response
    except Exception as e:
        logger.debug(f"HP scanner cache miss for breakout: {e}")
    
    # 3. Use database for breakout detection (Limit symbols for performance)
    logger.info("Using database for breakout scanner")
    db_fetcher = get_db_data_fetcher()
    db_data = await asyncio.to_thread(db_fetcher.fetch_latest_data)
    
    breakout_stocks = []
    if db_data:
        # Optimization: Limit loop iteration
        count = 0
        for symbol, tick in db_data.items():
            if count > 200: break # Safety cap
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
                count += 1
    
    breakout_stocks.sort(key=lambda x: x["change_pct"], reverse=True)
    
    # Enrich with LIVE prices
    enriched_data = await enrich_scanner_results(breakout_stocks[:50])
    
    response = {
        "type": "breakout_scan",
        "timestamp": datetime.now().isoformat(),
        "data": enriched_data,
        "count": len(enriched_data),
        "status": {
            "source": "DB_ENRICHED",
            "is_healthy": len(enriched_data) > 0,
            "last_update": datetime.now().isoformat()
        }
    }
    
    set_cached_scanner_data("breakout", response)
    return response


@router.get("/reversal")
async def get_reversal_data(current_user: User = Depends(get_current_user)):
    """
    REST endpoint for reversal scanner.
    
    During market hours: Returns live reversal data
    After market hours: Returns cached EOD snapshot
    """
    from utils.market_state import is_market_open, get_trading_date
    from services.dragonfly_client import get_cache as get_df_cache
    
    # Check if market is closed - return snapshot
    if not is_market_open():
        cache = get_df_cache()
        date_str = get_trading_date().strftime("%Y-%m-%d")
        snapshot = cache.get(f"snapshot:scanner_reversal:{date_str}")
        
        if snapshot and snapshot.get("data"):
            logger.info(f"Reversal: returning EOD snapshot ({date_str})")
            return {
                "type": "reversal_scan",
                "timestamp": datetime.now().isoformat(),
                "data": snapshot["data"],
                "count": len(snapshot["data"]),
                "status": {
                    "source": "EOD_SNAPSHOT",
                    "is_healthy": True,
                    "trade_date": date_str,
                    "market_status": "CLOSED"
                }
            }
    
    # Market is open - use live data
    cached = get_cached_scanner_data("reversal")
    if cached:
        # Enrich cached stocks with live prices
        try:
            if isinstance(cached, dict) and "data" in cached and cached["data"]:
                access_token = settings.UPSTOX_ACCESS_TOKEN
                cached["data"] = await enrich_scanner_results(cached["data"], access_token)
        except Exception as e:
            logger.error(f"reversal: Failed to enrich cached results: {e}")
        return cached

    from services.db_data_fetcher import get_db_data_fetcher
    from services.cache import get_cache_manager
    
    reversal_candidates = []
    
    try:
        # Add timeout protection to prevent hanging
        db_fetcher = get_db_data_fetcher()
        db_data = await asyncio.wait_for(
            asyncio.to_thread(db_fetcher.fetch_latest_data),
            timeout=30.0  # 30 second timeout
        )
        
        if db_data:
            count = 0
            for symbol, tick in db_data.items():
                if count > 200: break
                abs_change = abs(tick.change_pct)
                if (tick.change_pct <= -1.0 and tick.change_pct >= -4.0):
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
                    count += 1
                elif (tick.change_pct >= 3.0 and tick.change_pct <= 6.0):
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
                    count += 1
    except asyncio.TimeoutError:
        logger.warning("Reversal scanner timed out after 30 seconds")
        # Return empty result instead of hanging
    except Exception as e:
        logger.error(f"Reversal scanner error: {e}")
        # Continue with empty data
    
    reversal_candidates.sort(key=lambda x: x["reversal_score"], reverse=True)
    
    # Enrich with LIVE prices
    enriched_data = await enrich_scanner_results(reversal_candidates[:50])
    
    response = {
        "type": "reversal_scan",
        "timestamp": datetime.now().isoformat(),
        "data": enriched_data,
        "count": len(enriched_data),
        "status": {
            "source": "DB_ENRICHED",
            "is_healthy": len(enriched_data) > 0,
            "last_update": datetime.now().isoformat()
        }
    }
    
    set_cached_scanner_data("reversal", response)
    return response


@router.get("/trendfinder")
async def get_trendfinder_data(current_user: User = Depends(get_current_user)):
    """REST endpoint for TrendFinder AI scanner."""
    cached = get_cached_scanner_data("trendfinder")
    if cached:
        # Enrich cached stocks with live prices
        try:
            if isinstance(cached, dict) and "data" in cached and cached["data"]:
                access_token = settings.UPSTOX_ACCESS_TOKEN
                cached["data"] = await enrich_scanner_results(cached["data"], access_token)
        except Exception as e:
            logger.error(f"trendfinder: Failed to enrich cached results: {e}")
        return cached

    from services.db_data_fetcher import get_db_data_fetcher
    from services.cache import get_cache_manager
    
    db_fetcher = get_db_data_fetcher()
    db_data = await asyncio.to_thread(db_fetcher.fetch_latest_data)
    
    trending_stocks = []
    if db_data:
        count = 0
        for symbol, tick in db_data.items():
            if count > 200: break
            abs_change = abs(tick.change_pct)
            if abs_change >= 0.5:
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
                count += 1
    
    trending_stocks.sort(key=lambda x: x["ai_confidence"], reverse=True)
    
    # Enrich with LIVE prices
    enriched_data = await enrich_scanner_results(trending_stocks[:50])
    
    response = {
        "type": "trendfinder_scan",
        "timestamp": datetime.now().isoformat(),
        "data": enriched_data,
        "count": len(enriched_data),
        "status": {
            "source": "AI_DB_ENRICHED",
            "is_healthy": len(enriched_data) > 0,
            "last_update": datetime.now().isoformat(),
            "ai_model": "TrendFinder v1.0"
        }
    }
    
    set_cached_scanner_data("trendfinder", response)
    return response



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
        
        # Map to frontend structure
        mapped_results = []
        for res in results:
            # Calculate breakout_pct for frontend (positive for high, negative for low)
            breakout_pct = 0
            if res.get("breakout_type") == "52W_HIGH":
                breakout_pct = -res.get("percentage_from_high", 0) 
            elif res.get("breakout_type") == "52W_LOW":
                breakout_pct = res.get("percentage_from_low", 0)

            mapped_results.append({
                "symbol": res.get("symbol"),
                "ltp": res.get("current_price"),
                "high_52w": res.get("yearly_high"),
                "low_52w": res.get("yearly_low"),
                "prev_close": res.get("current_price"), 
                "change_pct": res.get("change_pct", 0),
                "breakout_type": res.get("breakout_type"),
                "breakout_pct": res.get("breakout_pct", breakout_pct),
                "volume_ratio": res.get("volume_ratio", 1.0),
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
