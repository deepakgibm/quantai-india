import json
import asyncio
import logging
from typing import Callable, List, Dict, Any
from services.cache import get_cache_manager

logger = logging.getLogger(__name__)

class PriceEventPublisher:
    """
    Handles publishing price updates via Redis Pub/Sub and distributes
    them to local async/thread callbacks for real-time WebSocket feeds.
    """
    CHANNEL_NAME = "qai:price_updates"

    def __init__(self):
        self._cache_mgr = get_cache_manager()
        self._local_subscribers: List[Callable[[Dict[str, Any]], None]] = []
        self._listener_task: Optional[asyncio.Task] = None
        self._is_listening = False

    def subscribe_local(self, callback: Callable[[Dict[str, Any]], None]):
        """Register a callback for price events in the current process."""
        if callback not in self._local_subscribers:
            self._local_subscribers.append(callback)
        # Lazily start Redis Pub/Sub listener when a local subscriber registers
        if not self._is_listening:
            self.start_listener()

    def unsubscribe_local(self, callback: Callable[[Dict[str, Any]], None]):
        if callback in self._local_subscribers:
            self._local_subscribers.remove(callback)

    def publish(self, symbol: str, price_data: Dict[str, Any]):
        """Publish a price update to all subscribers process-wide."""
        payload = {
            "symbol": symbol.upper(),
            "price_data": price_data,
            "timestamp": price_data.get("timestamp")
        }
        
        # 1. Distribute locally first for minimal latency
        for sub in self._local_subscribers:
            try:
                sub(payload)
            except Exception as e:
                logger.error(f"EventPublisher: Local subscriber error: {e}")
                
        # 2. Publish to Redis Pub/Sub for other processes/workers
        if self._cache_mgr.is_available():
            try:
                # We get the underlying redis connection from the cache client wrapper
                client = self._cache_mgr._client
                if hasattr(client, '_async_client') and client._async_client:
                    # Async task
                    asyncio.create_task(self._publish_redis_async(payload))
                elif hasattr(client, '_sync_client') and client._sync_client:
                    # Sync publish
                    client._sync_client.publish(self.CHANNEL_NAME, json.dumps(payload))
            except Exception as e:
                logger.warning(f"EventPublisher: Redis publish failed: {e}")

    async def _publish_redis_async(self, payload: dict):
        try:
            client = self._cache_mgr._client._async_client
            await client.publish(self.CHANNEL_NAME, json.dumps(payload))
        except Exception as e:
            logger.warning(f"EventPublisher: Async Redis publish failed: {e}")

    def start_listener(self):
        """Start listening to Redis Pub/Sub to sync other process updates."""
        if self._is_listening:
            return
        self._is_listening = True
        try:
            loop = asyncio.get_running_loop()
            self._listener_task = loop.create_task(self._redis_sub_loop())
        except RuntimeError:
            # No running loop (e.g. in script)
            pass

    async def _redis_sub_loop(self):
        logger.info("EventPublisher: Starting Redis Pub/Sub loop")
        while self._is_listening:
            if not self._cache_mgr.is_available():
                await asyncio.sleep(5)
                continue
                
            try:
                client = self._cache_mgr._client
                await client._ensure_async_connected()
                if not client._async_client:
                    await asyncio.sleep(5)
                    continue
                    
                pubsub = client._async_client.pubsub()
                await pubsub.subscribe(self.CHANNEL_NAME)
                
                while self._is_listening:
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if message and message['type'] == 'message':
                        try:
                            data = json.loads(message['data'])
                            # Notify local subscribers of external events
                            for sub in self._local_subscribers:
                                sub(data)
                        except Exception as parse_err:
                            logger.error(f"EventPublisher: Fail parsing Redis msg: {parse_err}")
                    await asyncio.sleep(0.01)
            except Exception as e:
                logger.warning(f"EventPublisher: Sub loop error: {e}, retrying in 5s")
                await asyncio.sleep(5)

    def stop(self):
        self._is_listening = False
        if self._listener_task:
            self._listener_task.cancel()

_price_event_publisher = None

def get_price_event_publisher() -> PriceEventPublisher:
    global _price_event_publisher
    if _price_event_publisher is None:
        _price_event_publisher = PriceEventPublisher()
    return _price_event_publisher
