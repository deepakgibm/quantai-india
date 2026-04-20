"""
Market Data Publisher
Broadcasts real-time market ticks to Redis Pub/Sub channels.
"""

import logging
from typing import Dict, Any
from services.dragonfly_client import get_cache

logger = logging.getLogger(__name__)

# Channel name for all market ticks
MARKET_TICKS_CHANNEL = "qai:market:ticks"

async def publish_tick(tick_data: Dict[str, Any]):
    """
    Publish a single market tick to the Redis Pub/Sub channel.
    
    Args:
        tick_data: Dictionary containing tick information (symbol, ltp, etc.)
    """
    cache = get_cache()
    try:
        # Publish to the global channel
        await cache.publish_async(MARKET_TICKS_CHANNEL, tick_data)
        
        # Also publish to a symbol-specific channel for granular subscriptions
        symbol_channel = f"qai:market:tick:{tick_data.get('symbol', 'unknown')}"
        await cache.publish_async(symbol_channel, tick_data)
        
    except Exception as e:
        logger.error(f"Failed to publish tick: {e}")
