"""
Redis-Backed Rate Limiting for Enterprise Security.
Provides token bucket rate limiting for authentication endpoints.
"""

from fastapi import Request, HTTPException, status
from services.dragonfly_client import get_cache

async def rate_limit_auth(request: Request) -> None:
    """
    Rate limit auth endpoints to prevent brute-force attacks.
    Limits to 5 attempts per minute per IP address.
    """
    client_ip = request.client.host if request.client else "unknown"
    cache = get_cache()
    
    # Make sure cache client is connected
    await cache._ensure_async_connected()
    
    # If Dragonfly/Redis is not running (e.g. local offline dev), skip checks
    if not cache._is_connected_async:
        return
        
    redis = cache._async_client
    key = f"rate_limit:auth:{client_ip}"
    
    # sliding window configuration
    limit = 5
    window = 60
    
    try:
        # Increment request count
        async with redis.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.ttl(key)
            res = await pipe.execute()
            
        count = res[0]
        ttl = res[1]
        
        # Set expire time if key was just created
        if count == 1 or ttl == -1:
            await redis.expire(key, window)
            ttl = window
            
        if count > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many authentication attempts. Please try again in {ttl if ttl > 0 else window} seconds."
            )
    except HTTPException:
        raise
    except Exception as e:
        # Fail open in case of Redis exceptions so we don't block legitimate logins
        import logging
        logging.getLogger(__name__).warning(f"Rate limiting failure: {e}")
        return
