"""
Cache-First Scanner API (v3)
All reads from Memcached, sub-50ms response target.
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import time

from services.dragonfly_client import (
    get_cache, cache_get, CacheKeys, cache_stats
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v3/scanner", tags=["HP Scanner v3"])


# =============================================================================
# Latency Tracking Middleware
# =============================================================================
class LatencyTracker:
    """Track API latency metrics."""
    
    def __init__(self):
        self.latencies: List[float] = []
        self.max_samples = 1000
    
    def record(self, latency_ms: float):
        self.latencies.append(latency_ms)
        if len(self.latencies) > self.max_samples:
            self.latencies = self.latencies[-self.max_samples:]
    
    def get_percentiles(self) -> Dict[str, float]:
        if not self.latencies:
            return {"p50": 0, "p95": 0, "p99": 0}
        
        sorted_latencies = sorted(self.latencies)
        n = len(sorted_latencies)
        
        return {
            "p50": sorted_latencies[int(n * 0.50)],
            "p95": sorted_latencies[int(n * 0.95)],
            "p99": sorted_latencies[int(n * 0.99)] if n > 100 else sorted_latencies[-1],
            "count": n,
            "avg": round(sum(self.latencies) / n, 2)
        }


latency_tracker = LatencyTracker()


def track_latency(func):
    """Decorator to track endpoint latency."""
    async def wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        elapsed = (time.time() - start) * 1000
        latency_tracker.record(elapsed)
        return result
    wrapper.__name__ = func.__name__
    return wrapper


# =============================================================================
# API Endpoints (Cache-First with EOD Snapshot Fallback)
# =============================================================================

def _get_eod_snapshot_or_none(signal_type: str):
    """Helper to get EOD snapshot when market is closed."""
    from utils.market_state import is_market_open, get_trading_date
    
    if is_market_open():
        return None
    
    # Market is closed - try to get snapshot
    cache = get_cache()
    date_str = get_trading_date().strftime("%Y-%m-%d")
    snapshot = cache.get(f"snapshot:hp_scanner_signals:{date_str}")
    
    if snapshot and signal_type in snapshot:
        return snapshot[signal_type]
    return None


@router.get("/momentum")
async def get_momentum():
    """
    Get momentum scanner results.
    
    During market hours: Reads from live Memcached
    After market hours: Returns EOD snapshot
    Target: <50ms
    """
    start = time.time()
    
    # Check EOD snapshot first (market closed)
    eod_data = _get_eod_snapshot_or_none("momentum")
    if eod_data is not None:
        elapsed = (time.time() - start) * 1000
        latency_tracker.record(elapsed)
        return {
            "type": "momentum",
            "timestamp": datetime.now().isoformat(),
            "count": len(eod_data),
            "data": eod_data,
            "latency_ms": round(elapsed, 2),
            "source": "EOD_SNAPSHOT",
            "market_status": "CLOSED"
        }
    
    # Read from live cache
    data = cache_get(CacheKeys.momentum())
    
    if data is None:
        logger.warning("Momentum cache miss - cache may not be warmed")
        data = []
    
    elapsed = (time.time() - start) * 1000
    latency_tracker.record(elapsed)
    
    return {
        "type": "momentum",
        "timestamp": datetime.now().isoformat(),
        "count": len(data),
        "data": data,
        "latency_ms": round(elapsed, 2),
        "source": "MEMCACHED" if data else "EMPTY"
    }


@router.get("/breakout")
async def get_breakout():
    """
    Get breakout scanner results (>2% moves).
    
    During market hours: Cache-first, zero computation
    After market hours: Returns EOD snapshot
    """
    start = time.time()
    
    # Check EOD snapshot first (market closed)
    eod_data = _get_eod_snapshot_or_none("breakout")
    if eod_data is not None:
        elapsed = (time.time() - start) * 1000
        latency_tracker.record(elapsed)
        return {
            "type": "breakout",
            "timestamp": datetime.now().isoformat(),
            "count": len(eod_data),
            "data": eod_data,
            "latency_ms": round(elapsed, 2),
            "source": "EOD_SNAPSHOT",
            "market_status": "CLOSED"
        }
    
    data = cache_get(CacheKeys.breakout())
    
    if data is None:
        data = []
    
    elapsed = (time.time() - start) * 1000
    latency_tracker.record(elapsed)
    
    return {
        "type": "breakout",
        "timestamp": datetime.now().isoformat(),
        "count": len(data),
        "data": data,
        "latency_ms": round(elapsed, 2),
        "source": "MEMCACHED" if data else "EMPTY"
    }


@router.get("/reversal")
async def get_reversal():
    """
    Get reversal scanner results (RSI extremes).
    
    During market hours: Cache-first, zero computation
    After market hours: Returns EOD snapshot
    """
    start = time.time()
    
    # Check EOD snapshot first (market closed)
    eod_data = _get_eod_snapshot_or_none("reversal")
    if eod_data is not None:
        elapsed = (time.time() - start) * 1000
        latency_tracker.record(elapsed)
        return {
            "type": "reversal",
            "timestamp": datetime.now().isoformat(),
            "count": len(eod_data),
            "data": eod_data,
            "latency_ms": round(elapsed, 2),
            "source": "EOD_SNAPSHOT",
            "market_status": "CLOSED"
        }
    
    data = cache_get(CacheKeys.reversal())
    
    if data is None:
        data = []
    
    elapsed = (time.time() - start) * 1000
    latency_tracker.record(elapsed)
    
    return {
        "type": "reversal",
        "timestamp": datetime.now().isoformat(),
        "count": len(data),
        "data": data,
        "latency_ms": round(elapsed, 2),
        "source": "MEMCACHED" if data else "EMPTY"
    }


@router.get("/signals")
async def get_active_signals():
    """
    Get all active strategy signals.
    
    During market hours: Cache-first, zero computation
    After market hours: Returns combined EOD snapshot
    """
    start = time.time()
    
    # Check if market is closed
    from utils.market_state import is_market_open, get_trading_date
    
    if not is_market_open():
        cache = get_cache()
        date_str = get_trading_date().strftime("%Y-%m-%d")
        snapshot = cache.get(f"snapshot:hp_scanner_signals:{date_str}")
        
        if snapshot:
            elapsed = (time.time() - start) * 1000
            latency_tracker.record(elapsed)
            return {
                "type": "signals",
                "timestamp": datetime.now().isoformat(),
                "count": snapshot.get("total_signals", 0),
                "data": snapshot,
                "latency_ms": round(elapsed, 2),
                "source": "EOD_SNAPSHOT",
                "market_status": "CLOSED"
            }
    
    data = cache_get(CacheKeys.signals())
    
    if data is None:
        data = []
    
    elapsed = (time.time() - start) * 1000
    latency_tracker.record(elapsed)
    
    return {
        "type": "signals",
        "timestamp": datetime.now().isoformat(),
        "count": len(data),
        "data": data,
        "latency_ms": round(elapsed, 2),
        "source": "MEMCACHED" if data else "EMPTY"
    }


@router.get("/snapshots")
async def get_all_snapshots():
    """
    Get all symbol snapshots.
    Cache-first, zero computation.
    """
    start = time.time()
    
    data = cache_get(CacheKeys.all_snapshots())
    
    if data is None:
        data = []
    
    elapsed = (time.time() - start) * 1000
    latency_tracker.record(elapsed)
    
    return {
        "type": "snapshots",
        "timestamp": datetime.now().isoformat(),
        "count": len(data),
        "data": data,
        "latency_ms": round(elapsed, 2),
        "source": "MEMCACHED" if data else "EMPTY"
    }


@router.get("/symbol/{symbol}")
async def get_symbol_snapshot(symbol: str):
    """
    Get snapshot for a single symbol.
    Cache-first, zero computation.
    """
    start = time.time()
    
    data = cache_get(CacheKeys.snapshot(symbol))
    
    if data is None:
        # Try indicators
        indicators = cache_get(CacheKeys.indicator(symbol, "1d"))
        if indicators:
            data = {"symbol": symbol, "indicators": indicators}
        else:
            # Return graceful fallback instead of 404
            elapsed = (time.time() - start) * 1000
            latency_tracker.record(elapsed)
            return {
                "status": "not_found",
                "symbol": symbol.upper(),
                "data": None,
                "message": f"Symbol {symbol} not currently in cache. Try /api/v3/scanner/snapshots for all available symbols.",
                "latency_ms": round(elapsed, 2),
                "source": "CACHE_MISS"
            }
    
    elapsed = (time.time() - start) * 1000
    latency_tracker.record(elapsed)
    
    return {
        "symbol": symbol,
        "data": data,
        "latency_ms": round(elapsed, 2),
        "source": "MEMCACHED"
    }


@router.get("/status")
async def get_status():
    """Get HP scanner service status."""
    from services.hp_scanner_service import get_hp_scanner_service
    from workers.indicator_worker import get_indicator_worker
    
    service = get_hp_scanner_service()
    worker = get_indicator_worker()
    
    return {
        "service": service.get_status(),
        "worker": worker.get_stats(),
        "cache": cache_stats(),
        "latency": latency_tracker.get_percentiles()
    }


@router.get("/metrics")
async def get_metrics():
    """Get detailed performance metrics."""
    return {
        "timestamp": datetime.now().isoformat(),
        "latency": latency_tracker.get_percentiles(),
        "cache": cache_stats(),
        "target_p95_ms": 50,
        "target_achieved": latency_tracker.get_percentiles().get("p95", 1000) < 50
    }


@router.post("/warm")
async def trigger_warm():
    """Manually trigger cache warm-up."""
    from services.hp_scanner_service import get_hp_scanner_service
    
    service = get_hp_scanner_service()
    
    if not service._is_running:
        await service.start()
    
    return {
        "status": "warming",
        "message": "Cache warm-up triggered",
        "symbol_count": len(service._symbols)
    }
