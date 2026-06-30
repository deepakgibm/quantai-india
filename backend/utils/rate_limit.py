from fastapi import Request, WebSocket, HTTPException, status
from services.dragonfly_client import get_cache
import logging

logger = logging.getLogger(__name__)

def rate_limit(limit: int, window: int, name: str = "default"):
    """
    Atomic Redis-based rate limiter middleware/dependency using sliding window counter.
    limit: Number of requests allowed
    window: Time window in seconds
    """
    async def dependency(request: Request = None, websocket: WebSocket = None):
        # Handle both HTTP and WebSocket
        conn = request or websocket
        if not conn:
            return
            
        cache = get_cache()
        await cache._ensure_async_connected()
        
        # If Dragonfly/Redis is not running, fail open in development/safe mode
        if not cache._is_connected_async:
            return
            
        redis = cache._async_client
        
        try:
            client_ip = conn.client.host if conn.client else "unknown"
        except AttributeError:
            return
        
        key = f"qai:ratelimit:{name}:{client_ip}"
        
        try:
            # Atomic sliding window increment using Redis pipeline
            async with redis.pipeline(transaction=True) as pipe:
                pipe.incr(key)
                pipe.ttl(key)
                res = await pipe.execute()
                
            count = res[0]
            ttl = res[1]
            
            # Set TTL if new key
            if count == 1 or ttl == -1:
                await redis.expire(key, window)
                ttl = window
                
            if count > limit:
                logger.warning(f"Rate limit exceeded for {client_ip} on {name}")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many requests. Please try again in {ttl if ttl > 0 else window} seconds."
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Rate limit error: {e}")
            # Fail open to prevent service outages on cache failure
            pass
            
    return dependency
