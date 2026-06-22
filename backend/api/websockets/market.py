from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import json
import logging
from typing import Dict

from services.dragonfly_client import get_cache

logger = logging.getLogger(__name__)

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        # Maps active websocket connections to their metadata (including sequence counter)
        self.active_connections: Dict[WebSocket, Dict] = {}
        # Keeps track of global redis pubsub listener task
        self.pubsub_task = None
        # Heartbeat task
        self.heartbeat_task = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[websocket] = {
            "subscriptions": set(),
            "sequence": 0,
            "last_ping_id": None,
            "last_pong_time": asyncio.get_event_loop().time()
        }
        logger.info(f"WebSocket Client connected: {websocket.client}")
        if not self.pubsub_task:
            self._start_redis_listener()
        if not self.heartbeat_task:
            self._start_heartbeat()

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            del self.active_connections[websocket]
            logger.info("WebSocket Client disconnected")

    async def handle_message(self, websocket: WebSocket, message: dict):
        action = message.get("action")
        symbols = message.get("symbols", [])
        
        if action == "pong":
            ping_id = message.get("id")
            meta = self.active_connections.get(websocket)
            if meta and meta.get("last_ping_id") == ping_id:
                meta["last_pong_time"] = asyncio.get_event_loop().time()
            return

        if not isinstance(symbols, list):
            return

        if action == "subscribe":
            for symbol in symbols:
                self.active_connections[websocket]["subscriptions"].add(symbol)
            await websocket.send_json({"status": "subscribed", "symbols": list(self.active_connections[websocket]["subscriptions"])})
            
        elif action == "unsubscribe":
            for symbol in symbols:
                self.active_connections[websocket]["subscriptions"].discard(symbol)
            await websocket.send_json({"status": "unsubscribed", "symbols": list(self.active_connections[websocket]["subscriptions"])})

    async def broadcast(self, symbol: str, data: dict):
        if not self.active_connections:
            return
            
        # Pre-serialize the JSON payload once for efficiency
        payload = {
            "event": "market_tick",
            "symbol": symbol,
            "data": data,
            "ts": data.get("timestamp")
        }
        serialized_payload = json.dumps(payload)
        
        for connection, meta in list(self.active_connections.items()):
            if symbol in meta["subscriptions"]:
                try:
                    await connection.send_text(serialized_payload)
                except Exception as e:
                    logger.error(f"Error broadcasting to client: {e}")
                    self.disconnect(connection)
                    
    def _start_heartbeat(self):
        import uuid
        async def heartbeat_loop():
            while True:
                try:
                    await asyncio.sleep(15) # 15 second heartbeat
                    if not self.active_connections:
                        continue
                        
                    now = asyncio.get_event_loop().time()
                    for connection, meta in list(self.active_connections.items()):
                        # If a client fails to pong within 20 seconds, terminate the connection.
                        # (Connection starts with last_pong_time = connection time).
                        if now - meta.get("last_pong_time", now) > 20:
                            logger.warning(f"Closing zombie connection (no pong for >20s): {connection.client}")
                            self.disconnect(connection)
                            try:
                                await connection.close()
                            except Exception:
                                pass
                            continue
                        
                        # Send next ping
                        ping_id = str(uuid.uuid4())
                        meta["last_ping_id"] = ping_id
                        try:
                            await connection.send_json({"type": "ping", "id": ping_id})
                        except Exception:
                            self.disconnect(connection)
                except Exception as e:
                    logger.error(f"Heartbeat loop error: {e}")
                    await asyncio.sleep(5)
        
        self.heartbeat_task = asyncio.create_task(heartbeat_loop())

    def _start_redis_listener(self):
        cache = get_cache()
        if not cache.is_available():
            logger.warning("Cache unavailable, cannot start Redis pubsub listener")
            return

        async def redis_listener():
            try:
                # We subscribe to a pattern to get all market quotes
                if hasattr(cache, "_async_client") and cache._async_client:
                    pubsub = cache._async_client.pubsub()
                    await pubsub.psubscribe("market.quote.*")
                    logger.info("Started Redis PubSub listener for WebSocket gateway")
                    async for message in pubsub.listen():
                        if message["type"] == "pmessage":
                            channel = message["channel"]
                            symbol = channel.split(".")[-1]
                            data = json.loads(message["data"])
                            await self.broadcast(symbol, data)
            except asyncio.CancelledError:
                logger.info("Redis listener cancelled")
            except Exception as e:
                logger.error(f"Redis listener error: {e}")
                self.pubsub_task = None
                
        self.pubsub_task = asyncio.create_task(redis_listener())

manager = ConnectionManager()

@router.websocket("/live")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket Endpoint for live market data.
    Clients can subscribe via:
    {"action": "subscribe", "symbols": ["RELIANCE", "TCS"]}
    """
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                await manager.handle_message(websocket, message)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON format"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket exception: {e}")
        manager.disconnect(websocket)
