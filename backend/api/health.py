from fastapi import APIRouter
from fastapi.responses import JSONResponse
from datetime import datetime
import time
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Health"])

@router.get("/")
async def health_check():
    """
    Comprehensive health check - checks all critical dependencies.
    """
    health = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }
    
    # 1. Check DragonflyDB/Redis
    try:
        from services.dragonfly_client import get_cache
        start = time.perf_counter()
        cache = get_cache()
        if cache.is_available():
            await cache.get_async("health_ping") # Test ping asynchronously to avoid blocking event loop
            latency = (time.perf_counter() - start) * 1000
            health["checks"]["dragonfly"] = {
                "status": "healthy", 
                "latency_ms": round(latency, 2)
            }
        else:
            health["checks"]["dragonfly"] = {"status": "unhealthy", "error": "Not connected"}
            health["status"] = "degraded"
    except Exception as e:
        health["checks"]["dragonfly"] = {"status": "unhealthy", "error": str(e)}
        health["status"] = "degraded"
    
    # 2. Check Database (PostgreSQL)
    try:
        from database import AsyncSessionLocal
        from sqlalchemy import text
        start = time.perf_counter()
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            latency = (time.perf_counter() - start) * 1000
            health["checks"]["database"] = {
                "status": "healthy", 
                "latency_ms": round(latency, 2)
            }
    except Exception as e:
        health["checks"]["database"] = {"status": "unhealthy", "error": str(e)}
        health["status"] = "degraded"

    # 3. Check Upstox API Circuit
    try:
        from utils.circuit_breaker import UPSTOX_CIRCUIT_BREAKER
        health["checks"]["upstox_api"] = {
            "status": "healthy" if str(UPSTOX_CIRCUIT_BREAKER.state) == "closed" else "degraded",
            "circuit": str(UPSTOX_CIRCUIT_BREAKER.state)
        }
    except Exception:
        health["checks"]["upstox_api"] = {"status": "unknown"}
        
    # 4. Check Resource Utilization
    try:
        import psutil
        process = psutil.Process()
        health["checks"]["resources"] = {
            "status": "healthy",
            "cpu_percent": psutil.cpu_percent(interval=None),
            "memory_rss_mb": round(process.memory_info().rss / (1024 * 1024), 2),
            "system_memory_percent": psutil.virtual_memory().percent
        }
    except Exception:
        try:
            import os
            health["checks"]["resources"] = {
                "status": "healthy",
                "pid": os.getpid()
            }
        except Exception:
            health["checks"]["resources"] = {"status": "unknown"}
    
    # Return 503 only if CRITICAL dependencies are down (DB)
    # Cache/Upstox degradation should return 200 with "degraded" body
    critical_failure = (
        health["checks"].get("database", {}).get("status") == "unhealthy"
    )
    
    if critical_failure:
        return JSONResponse(status_code=503, content=health)
    
    return health

@router.get("/ready")
async def readiness_check():
    """Readiness check for load balancers."""
    try:
        from services.dragonfly_client import get_cache
        if not get_cache().is_available():
            return JSONResponse(status_code=503, content={"status": "not_ready", "reason": "cache_unavailable"})
    except:
        pass
    return {"status": "ready"}
