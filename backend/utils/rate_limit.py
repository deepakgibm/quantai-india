from fastapi import Request, WebSocket, HTTPException, status
from services.dragonfly_client import get_cache
import logging
from typing import Union

logger = logging.getLogger(__name__)

def rate_limit(limit: int, window: int, name: str = "default"):
    """
    Simple Redis-based rate limiter middleware/dependency.
    limit: Number of requests allowed
    window: Time window in seconds
    """
    async def dependency(request: Request = None, websocket: WebSocket = None):
        # Handle both HTTP and WebSocket
        conn = request or websocket
        if not conn:
            return
            
        cache = get_cache()
        if not cache.is_available():
            # If cache is down, we don't block for now in this implementation
            # or we could fail-closed. High-sec apps fail-closed.
            return
            
        # Use client IP as identifier
        try:
            client_ip = conn.client.host
        except AttributeError:
            return
        
        key = f"qai:ratelimit:{name}:{client_ip}"
        
        try:
            current = cache.get(key)
            if current is None:
                cache.set(key, 1, ttl=window)
                return
                
            if int(current) >= limit:
                logger.warning(f"Rate limit exceeded for {client_ip} on {name}")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please try again later."
                )
                
            # Increment is not atomic in the current CacheManager API (no INCR)
            # But for simple rate limiting it's often close enough, 
            # or we add INCR to CacheManager.
            # Let's add 1 to the current and set it back.
            cache.set(key, int(current) + 1, ttl=window)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Rate limit error: {e}")
            # Fail open if cache error occurs, to not block users due to infra issues
            pass
            
    return dependency
