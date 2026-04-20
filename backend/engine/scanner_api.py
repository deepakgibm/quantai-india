"""
High-Performance Scanner API Router
Reads pre-computed snapshots only - NO strategy execution in request path.
"""

from fastapi import APIRouter
from typing import Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["High-Performance Scanner (V3)"])


@router.get("/momentum")
async def get_momentum_v2():
    """
    Get momentum scanner results.
    Reads from pre-computed snapshots - response time < 50ms.
    """
    from engine.scanner_service import get_scanner_service
    
    service = get_scanner_service()
    snapshots = service.get_all_snapshots()
    
    # Sort by absolute change percentage
    snapshots.sort(key=lambda x: abs(x.get("change_pct", 0)), reverse=True)
    
    return {
        "type": "bucket_update",
        "timestamp": datetime.now().isoformat(),
        "data": snapshots[:100],  # Top 100
        "count": len(snapshots),
        "status": {
            "source": "IN_MEMORY",
            "is_healthy": len(snapshots) > 0,
            **service.get_status()
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
    from engine.scanner_service import get_scanner_service
    
    service = get_scanner_service()
    snapshots = service.get_filtered_snapshots(
        signal_type=signal_type,
        min_confidence=min_confidence
    )
    
    # Only return stocks with signals
    snapshots = [s for s in snapshots if s.get("active_strategies")]
    
    # Sort by signal strength descending
    snapshots.sort(key=lambda x: x.get("signal_strength", 0), reverse=True)
    
    return {
        "type": "active_signals",
        "timestamp": datetime.now().isoformat(),
        "data": snapshots[:50],
        "count": len(snapshots),
        "status": service.get_status()
    }


@router.get("/breakout")
async def get_breakout_v2():
    """
    Get breakout scanner results.
    Filters for strong bullish momentum (>2% change).
    """
    from engine.scanner_service import get_scanner_service
    
    service = get_scanner_service()
    snapshots = service.get_all_snapshots()
    
    # Filter for breakouts (strong positive movement)
    breakouts = [
        s for s in snapshots 
        if s.get("change_pct", 0) >= 2.0
    ]
    
    # Enrich with breakout-specific fields
    for b in breakouts:
        b["breakout_score"] = min(100, int(b.get("change_pct", 0) * 15 + 50))
        b["pattern"] = "BULLISH_BREAKOUT" if b.get("change_pct", 0) >= 4.0 else "MODERATE_BREAKOUT"
        b["strength"] = "STRONG" if b.get("change_pct", 0) >= 4.0 else "MODERATE"
    
    breakouts.sort(key=lambda x: x.get("change_pct", 0), reverse=True)
    
    return {
        "type": "breakout_scan",
        "timestamp": datetime.now().isoformat(),
        "data": breakouts[:50],
        "count": len(breakouts),
        "status": service.get_status()
    }


@router.get("/reversal")
async def get_reversal_v2():
    """
    Get reversal scanner results.
    Identifies oversold bounce candidates and overbought corrections.
    """
    from engine.scanner_service import get_scanner_service
    
    service = get_scanner_service()
    snapshots = service.get_all_snapshots()
    
    reversals = []
    for s in snapshots:
        change = s.get("change_pct", 0)
        rsi = s.get("indicators", {}).get("rsi_14", 50)
        
        # Bullish reversal: oversold (RSI < 35) or recent decline (-4% to -1%)
        if rsi < 35 or (-4.0 <= change <= -1.0):
            reversals.append({
                **s,
                "reversal_type": "BULLISH",
                "reversal_score": int(abs(change) * 20) if change < 0 else int((35 - rsi) * 2),
                "pattern": "OVERSOLD_BOUNCE"
            })
        # Bearish reversal: overbought (RSI > 65) or strong rally (+3% to +6%)
        elif rsi > 65 or (3.0 <= change <= 6.0):
            reversals.append({
                **s,
                "reversal_type": "BEARISH",
                "reversal_score": int(change * 15) if change > 0 else int((rsi - 65) * 2),
                "pattern": "OVERBOUGHT_CORRECTION"
            })
    
    reversals.sort(key=lambda x: x.get("reversal_score", 0), reverse=True)
    
    return {
        "type": "reversal_scan",
        "timestamp": datetime.now().isoformat(),
        "data": reversals[:50],
        "count": len(reversals),
        "status": service.get_status()
    }


@router.get("/trendfinder")
async def get_trendfinder_v2():
    """
    Get TrendFinder AI results.
    Uses EMA stack and momentum indicators for trend detection.
    """
    from engine.scanner_service import get_scanner_service
    
    service = get_scanner_service()
    snapshots = service.get_all_snapshots()
    
    trending = []
    for s in snapshots:
        change = abs(s.get("change_pct", 0))
        trend = s.get("trend_direction", "NEUTRAL")
        
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
            **service.get_status()
        }
    }


@router.get("/symbol/{symbol}")
async def get_symbol_snapshot(symbol: str):
    """
    Get detailed snapshot for a specific symbol.
    Includes all indicators and active signals.
    """
    from engine.scanner_service import get_scanner_service
    
    service = get_scanner_service()
    snapshot = service.get_snapshot(symbol.upper())
    
    if not snapshot:
        # Return graceful fallback instead of 404
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
    from engine.scanner_service import get_scanner_service
    
    service = get_scanner_service()
    return service.get_status()
