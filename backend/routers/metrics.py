"""
Metrics and Metadata API Router

Exposes endpoints for:
- ETL job health and lag metrics
- API latency percentiles
- Cache hit/miss ratios
- Data freshness indicators
- Symbol and Strategy metadata
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Any, Optional
from datetime import datetime, date, timedelta
import psycopg2
import logging

from config import settings
from services.metadata_cache_service import get_metadata_cache_service
from services.dragonfly_client import get_cache, CacheUnavailableError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/metrics", tags=["Metrics & Metadata"])


# =============================================================================
# Symbol & Strategy Metadata Endpoints
# =============================================================================

@router.get("/symbols", response_model=Dict[str, Any])
async def get_symbol_master():
    """
    Get cached symbol master data for fast frontend lookups.
    
    Returns:
        {
            "count": 501,
            "symbols": [{"symbol": "RELIANCE", "company_name": "...", "sector": "...", "instrument_key": "..."}],
            "source": "cache" | "database"
        }
    """
    service = get_metadata_cache_service()
    symbols = service.get_symbol_master()
    
    return {
        "count": len(symbols),
        "symbols": symbols,
        "source": "cache" if service._stats["hits"] > 0 else "database"
    }


@router.get("/symbols/{symbol}")
async def get_symbol_detail(symbol: str):
    """Get cached details for a specific symbol."""
    service = get_metadata_cache_service()
    detail = service.get_symbol_detail(symbol.upper())
    
    if not detail:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
    
    return detail


@router.get("/sectors")
async def get_sectors():
    """Get list of all sectors."""
    service = get_metadata_cache_service()
    sectors = service.get_sectors()
    
    return {
        "count": len(sectors),
        "sectors": sectors
    }


@router.get("/sectors/{sector}/symbols")
async def get_sector_symbols(sector: str):
    """Get symbols in a specific sector."""
    service = get_metadata_cache_service()
    symbols = service.get_sector_symbols(sector)
    
    return {
        "sector": sector,
        "count": len(symbols),
        "symbols": symbols
    }


@router.get("/strategies")
async def get_strategies():
    """
    Get all available trading strategies with metadata.
    
    Returns:
        {
            "count": 8,
            "strategies": [{
                "id": "momentum",
                "name": "Momentum Scanner",
                "description": "...",
                "category": "technical",
                "timeframes": ["1d", "1h"],
                "indicators": ["RSI", "MACD", "ADX"],
                "risk_level": "medium"
            }]
        }
    """
    service = get_metadata_cache_service()
    strategies = service.get_strategies()
    
    return {
        "count": len(strategies),
        "strategies": strategies
    }


@router.get("/strategies/{strategy_id}")
async def get_strategy_detail(strategy_id: str):
    """Get details for a specific strategy."""
    service = get_metadata_cache_service()
    detail = service.get_strategy_detail(strategy_id)
    
    if not detail:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")
    
    return detail


# =============================================================================
# Cache Management Endpoints
# =============================================================================

@router.post("/cache/warmup")
async def warmup_cache():
    """
    Trigger cache warm-up manually.
    Normally called at application startup.
    """
    service = get_metadata_cache_service()
    result = service.warm_cache()
    return result


@router.get("/cache/stats")
async def get_cache_stats():
    """
    Get cache hit/miss statistics.
    
    Returns:
        {
            "hits": 1234,
            "misses": 56,
            "hit_rate_percent": 95.67,
            "last_warmup": "2026-01-14T18:00:00",
            "cache_version": "v1"
        }
    """
    service = get_metadata_cache_service()
    return service.get_stats()


@router.delete("/cache/invalidate")
async def invalidate_cache():
    """Invalidate all metadata cache."""
    service = get_metadata_cache_service()
    success = service.invalidate_all()
    
    if success:
        return {"status": "success", "message": "Cache invalidated"}
    else:
        raise HTTPException(status_code=503, detail="Cache unavailable")


@router.get("/cache/latency")
async def get_cache_latency():
    """
    Compare latency for cached vs uncached data retrieval.
    
    Returns:
        {
            "cached_ms": 0.5,
            "uncached_ms": 25.3,
            "speedup_factor": 50.6,
            "cache_status": "hit" | "miss"
        }
    """
    import time
    
    service = get_metadata_cache_service()
    
    # Measure cached retrieval
    start = time.perf_counter()
    cached_data = service.get_symbol_master()
    cached_ms = (time.perf_counter() - start) * 1000
    
    # Track if it was a cache hit
    cache_status = "hit" if service._stats["hits"] > 0 else "miss"
    
    # Measure direct DB retrieval (bypass cache)
    start = time.perf_counter()
    uncached_data = service._load_symbols_from_db()
    uncached_ms = (time.perf_counter() - start) * 1000
    
    # Calculate speedup
    speedup = round(uncached_ms / cached_ms, 1) if cached_ms > 0 else None
    
    return {
        "cached_ms": round(cached_ms, 2),
        "uncached_ms": round(uncached_ms, 2),
        "speedup_factor": speedup,
        "cache_status": cache_status,
        "symbols_retrieved": len(cached_data) if cached_data else 0
    }

# =============================================================================
# Data Freshness Endpoints
# =============================================================================

@router.get("/freshness")
async def get_data_freshness():
    """
    Get data freshness indicators per timeframe.
    
    Returns:
        {
            "timeframes": {
                "1d": {"latest": "2026-01-14", "symbols": 501, "age_hours": 2.5},
                "1h": {"latest": "2026-01-14 15:00", "symbols": 450, "age_hours": 3.5},
                ...
            },
            "overall_health": "healthy" | "stale" | "missing"
        }
    """
    try:
        db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                timeframe,
                COUNT(DISTINCT symbol) as symbols,
                MAX(timestamp) as latest
            FROM stock_candles
            GROUP BY timeframe
            ORDER BY timeframe
        """)
        
        rows = cur.fetchall()
        conn.close()
        
        now = datetime.now()
        timeframes = {}
        
        for row in rows:
            tf, symbols, latest = row
            if latest:
                age_hours = (now - latest).total_seconds() / 3600
                timeframes[tf] = {
                    "latest": latest.isoformat() if isinstance(latest, datetime) else str(latest),
                    "symbols": symbols,
                    "age_hours": round(age_hours, 2)
                }
        
        # Determine overall health
        if not timeframes:
            health = "missing"
        elif any(tf.get("age_hours", 0) > 24 for tf in timeframes.values()):
            health = "stale"
        else:
            health = "healthy"
        
        return {
            "timeframes": timeframes,
            "overall_health": health,
            "checked_at": now.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Freshness check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ETL Health Endpoints
# =============================================================================

@router.get("/etl/health")
async def get_etl_health():
    """
    Get ETL job health and lag metrics.
    
    Returns:
        {
            "daily_snapshot": {"last_run": "...", "status": "success", "lag_hours": 2.5},
            "intraday_etl": {"last_run": "...", "status": "success", "lag_hours": 0.5}
        }
    """
    try:
        db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        # Check for ETL logs table
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'etl_logs'
            )
        """)
        has_logs = cur.fetchone()[0]
        
        if has_logs:
            cur.execute("""
                SELECT etl_name, status, started_at, completed_at
                FROM etl_logs
                WHERE started_at > NOW() - INTERVAL '7 days'
                ORDER BY started_at DESC
                LIMIT 10
            """)
            logs = cur.fetchall()
        else:
            logs = []
        
        conn.close()
        
        # Calculate lag based on latest data
        now = datetime.now()
        
        return {
            "status": "healthy" if logs else "unknown",
            "recent_runs": [
                {
                    "etl_name": log[0],
                    "status": log[1],
                    "started_at": log[2].isoformat() if log[2] else None,
                    "completed_at": log[3].isoformat() if log[3] else None
                }
                for log in logs
            ] if logs else [],
            "message": "ETL logs available" if logs else "No ETL logs found",
            "checked_at": now.isoformat()
        }
        
    except Exception as e:
        logger.error(f"ETL health check failed: {e}")
        return {
            "status": "error",
            "message": str(e),
            "checked_at": datetime.now().isoformat()
        }


# =============================================================================
# DragonflyDB Health Endpoint
# =============================================================================

@router.get("/cache/health")
async def get_cache_health():
    """
    Get DragonflyDB/Redis health status.
    
    Returns:
        {
            "status": "healthy" | "unavailable",
            "server_info": {...},
            "key_count": 150
        }
    """
    try:
        cache = get_cache()
        info = cache.info()
        
        return {
            "status": "healthy",
            "server_version": info.get("redis_version", "unknown"),
            "connected_clients": info.get("connected_clients", 0),
            "used_memory_human": info.get("used_memory_human", "unknown"),
            "key_count": len(cache._client.keys("qai:*")) if cache._client else 0
        }
        
    except CacheUnavailableError as e:
        return {
            "status": "unavailable",
            "error": str(e)
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
