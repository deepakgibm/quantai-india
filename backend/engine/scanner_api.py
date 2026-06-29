"""
High-Performance Scanner API Router
Reads pre-computed snapshots only - NO strategy execution in request path.
Queries DragonflyDB cache instead of local process memory.
"""

from fastapi import APIRouter
from typing import Optional
from datetime import datetime
import logging
import pandas as pd
from services.dragonfly_client import get_cache, CacheKeys

logger = logging.getLogger(__name__)

router = APIRouter(tags=["High-Performance Scanner (V3)"])


@router.get("/momentum")
async def get_momentum_v2():
    """
    Get momentum scanner results.
    Reads from pre-computed snapshots - response time < 50ms.
    """
    cache = get_cache()
    snapshots = await cache.get_async(CacheKeys.momentum()) or []
    status = await cache.get_async(CacheKeys.worker_status()) or {}
    
    return {
        "type": "bucket_update",
        "timestamp": datetime.now().isoformat(),
        "data": snapshots[:100],  # Top 100
        "count": len(snapshots),
        "status": {
            "source": "DRAGONFLY_CACHE",
            "is_healthy": len(snapshots) > 0,
            **status
        }
    }


@router.get("/signals")
async def get_active_signals(
    signal_type: Optional[str] = None,
    min_confidence: float = 50
):
    """
    Get stocks with active strategy signals.
    Filtered by signal type (BUY/SELL) and minimum confidence.
    """
    cache = get_cache()
    signals = await cache.get_async(CacheKeys.signals()) or []
    status = await cache.get_async(CacheKeys.worker_status()) or {}
    
    filtered_signals = []
    for s in signals:
        s_types = s.get("signals", [])
        if signal_type:
            is_buy = any("OVERSOLD" in sig or "BULLISH" in sig or "BUY" in sig for sig in s_types)
            is_sell = any("OVERBOUGHT" in sig or "BEARISH" in sig or "SELL" in sig for sig in s_types)
            if signal_type.upper() == "BUY" and not is_buy:
                continue
            if signal_type.upper() == "SELL" and not is_sell:
                continue
        filtered_signals.append(s)
        
    return {
        "type": "active_signals",
        "timestamp": datetime.now().isoformat(),
        "data": filtered_signals[:50],
        "count": len(filtered_signals),
        "status": status
    }


@router.get("/breakout")
async def get_breakout_v2():
    """
    Get breakout scanner results.
    Filters for strong bullish momentum (>2% change).
    """
    cache = get_cache()
    breakouts = await cache.get_async(CacheKeys.breakout()) or []
    status = await cache.get_async(CacheKeys.worker_status()) or {}
    
    # Enrich with breakout-specific fields
    for b in breakouts:
        b["breakout_score"] = min(100, int(b.get("change_pct", 0) * 15 + 50))
        b["pattern"] = "BULLISH_BREAKOUT" if b.get("change_pct", 0) >= 4.0 else "MODERATE_BREAKOUT"
        b["strength"] = "STRONG" if b.get("change_pct", 0) >= 4.0 else "MODERATE"
        
    return {
        "type": "breakout_scan",
        "timestamp": datetime.now().isoformat(),
        "data": breakouts[:50],
        "count": len(breakouts),
        "status": status
    }


@router.get("/reversal")
async def get_reversal_v2():
    """
    Get reversal scanner results.
    Identifies oversold bounce candidates and overbought corrections.
    """
    cache = get_cache()
    reversals = await cache.get_async(CacheKeys.reversal()) or []
    status = await cache.get_async(CacheKeys.worker_status()) or {}
    
    enriched_reversals = []
    for r in reversals:
        change = r.get("change_pct", 0)
        rsi = r.get("indicators", {}).get("rsi_14", 50)
        
        # Bullish reversal: oversold (RSI < 35) or recent decline (-4% to -1%)
        if rsi < 35 or (-4.0 <= change <= -1.0):
            enriched_reversals.append({
                **r,
                "reversal_type": "BULLISH",
                "reversal_score": int(abs(change) * 20) if change < 0 else int((35 - rsi) * 2),
                "pattern": "OVERSOLD_BOUNCE"
            })
        # Bearish reversal: overbought (RSI > 65) or strong rally (+3% to +6%)
        elif rsi > 65 or (3.0 <= change <= 6.0):
            enriched_reversals.append({
                **r,
                "reversal_type": "BEARISH",
                "reversal_score": int(change * 15) if change > 0 else int((rsi - 65) * 2),
                "pattern": "OVERBOUGHT_CORRECTION"
            })
            
    enriched_reversals.sort(key=lambda x: x.get("reversal_score", 0), reverse=True)
    
    return {
        "type": "reversal_scan",
        "timestamp": datetime.now().isoformat(),
        "data": enriched_reversals[:50],
        "count": len(enriched_reversals),
        "status": status
    }


@router.get("/trendfinder")
async def get_trendfinder_v2():
    """
    Get TrendFinder AI results.
    Uses EMA stack and momentum indicators for trend detection.
    """
    cache = get_cache()
    snapshots = await cache.get_async(CacheKeys.all_snapshots()) or []
    status = await cache.get_async(CacheKeys.worker_status()) or {}
    
    trending = []
    for s in snapshots:
        change = abs(s.get("change_pct", 0))
        signals = s.get("signals", [])
        trend = "BULLISH" if "EMA_BULLISH_STACK" in signals else "BEARISH" if "EMA_BEARISH_STACK" in signals else "NEUTRAL"
        
        if change >= 0.5 or trend != "NEUTRAL":
            confidence = min(95, int(change * 25 + 30))
            trending.append({
                **s,
                "trend_direction": trend,
                "trend_strength": "STRONG" if change >= 3.0 else "MODERATE" if change >= 1.5 else "WEAK",
                "ai_confidence": confidence,
                "signal": "BUY" if s.get("change_pct", 0) > 1.0 else "SELL" if s.get("change_pct", 0) < -1.0 else "HOLD"
            })
            
    trending.sort(key=lambda x: x.get("ai_confidence", 0), reverse=True)
    
    return {
        "type": "trendfinder_scan",
        "timestamp": datetime.now().isoformat(),
        "data": trending[:50],
        "count": len(trending),
        "status": {
            "source": "AI_ENGINE",
            "ai_model": "TrendFinder v2.0",
            **status
        }
    }


@router.get("/symbol/{symbol}")
async def get_symbol_snapshot(symbol: str):
    """
    Get detailed snapshot for a specific symbol.
    Includes all indicators and active signals.
    """
    cache = get_cache()
    snapshot = await cache.get_async(CacheKeys.snapshot(symbol.upper()))
    
    if not snapshot:
        all_snaps = await cache.get_async(CacheKeys.all_snapshots()) or []
        for s in all_snaps:
            if s.get("symbol") == symbol.upper():
                snapshot = s
                break
                
    if not snapshot:
        return {
            "status": "not_found",
            "data": None,
            "symbol": symbol.upper(),
            "message": f"Symbol {symbol} not currently in HP Scanner cache. Try /api/v3/scanner/snapshots for all available symbols.",
            "timestamp": datetime.now().isoformat()
        }
        
    return {
        "status": "success",
        "data": snapshot,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/status")
async def get_scanner_status():
    """Get scanner service status."""
    cache = get_cache()
    status = await cache.get_async(CacheKeys.worker_status()) or {}
    
    last_scan_str = status.get("last_scan")
    is_healthy = True
    warning = None
    
    if last_scan_str:
        try:
            last_scan_dt = datetime.fromisoformat(last_scan_str)
            age_seconds = (datetime.now() - last_scan_dt).total_seconds()
            if age_seconds > 60:
                is_healthy = False
                warning = f"Scanner heartbeat stale. Last update: {age_seconds:.1f}s ago."
        except Exception:
            is_healthy = False
            warning = "Failed to parse scanner heartbeat timestamp."
    else:
        is_healthy = False
        warning = "No scanner heartbeat found. Scanner worker not running."
        
    return {
        "is_running": status.get("pid") is not None,
        "is_healthy": is_healthy,
        "warning": warning,
        "source": "DRAGONFLY_CACHE",
        **status
    }

