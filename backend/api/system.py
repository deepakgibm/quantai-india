from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from datetime import datetime
import httpx
import logging
import firebase_admin

from database import AsyncSessionLocal
from services.dragonfly_client import get_cache
from services.upstox_client import get_upstox_client
from config import settings
from utils.rate_limit import rate_limit

logger = logging.getLogger(__name__)
router = APIRouter(
    tags=["System Diagnostics"],
    dependencies=[Depends(rate_limit(60, 60, "system_health"))]
)

@router.get("/upstox-health")
async def get_upstox_health():
    """
    Check Upstox connection and API reachability.
    Response:
    {
      "status": "healthy",
      "token_valid": true,
      "api_reachable": true,
      "last_checked": ""
    }
    """
    client = get_upstox_client()
    token_valid = False
    api_reachable = False
    
    if client.access_token:
        try:
            async with httpx.AsyncClient() as httpx_client:
                headers = {
                    "Accept": "application/json",
                    "Authorization": f"Bearer {client.access_token}"
                }
                if settings.UPSTOX_API_KEY:
                    headers["Api-Key"] = settings.UPSTOX_API_KEY
                
                resp = await httpx_client.get("https://api.upstox.com/v2/user/profile", headers=headers, timeout=5.0)
                api_reachable = True
                if resp.status_code == 200:
                    token_valid = True
                elif resp.status_code == 401:
                    token_valid = False
                else:
                    token_valid = False
        except httpx.RequestError as e:
            logger.warning(f"Upstox API reachable check failed: {e}")
            api_reachable = False
            token_valid = False
    else:
        # No access token, check general internet connectivity
        try:
            async with httpx.AsyncClient() as httpx_client:
                resp = await httpx_client.get("https://api.upstox.com/v2/login/authorization/dialog", timeout=5.0)
                api_reachable = True
        except httpx.RequestError:
            api_reachable = False
            
    is_healthy = api_reachable and token_valid
    
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "token_valid": token_valid,
        "api_reachable": api_reachable,
        "last_checked": datetime.now().isoformat()
    }

@router.get("/health")
async def get_system_health():
    """
    Get unified system health monitor status.
    Return:
    {
      "backend": "healthy",
      "database": "healthy",
      "redis": "healthy",
      "upstox": "healthy",
      "firebase": "healthy",
      "websocket": "healthy",
      "version": "2.0.0"
    }
    """
    # 1. Database Check
    db_healthy = "healthy"
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"System health DB check failed: {e}")
        db_healthy = "unhealthy"
        
    # 2. Redis/Dragonfly Check
    redis_healthy = "healthy"
    try:
        cache = get_cache()
        if not cache.is_available():
            redis_healthy = "unhealthy"
    except Exception as e:
        logger.error(f"System health Redis check failed: {e}")
        redis_healthy = "unhealthy"
        
    # 3. Upstox Check
    upstox_healthy = "healthy"
    try:
        client = get_upstox_client()
        if not client.access_token:
            upstox_healthy = "unhealthy"
    except Exception:
        upstox_healthy = "unhealthy"
        
    # 4. Firebase Check
    firebase_healthy = "healthy"
    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_healthy = "unhealthy"
        
    # 5. Websocket Check (healthy if both backend and Redis are healthy)
    websocket_healthy = "healthy" if (redis_healthy == "healthy" and db_healthy == "healthy") else "unhealthy"
    
    return {
        "backend": "healthy",
        "database": db_healthy,
        "redis": redis_healthy,
        "upstox": upstox_healthy,
        "firebase": firebase_healthy,
        "websocket": websocket_healthy,
        "version": "2.0.0"
    }
