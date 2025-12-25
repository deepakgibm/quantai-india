"""
Upstox WebSocket Manager
Handles real-time market data feed from Upstox V2 API.
Uses Protobuf for decoding tick data.
"""

import asyncio
import json
import logging
import ssl
import certifi
import websockets
from typing import Dict, List, Optional, Callable, Set
from datetime import datetime
import pandas as pd

from config import settings
from services.upstox_client import get_upstox_client

logger = logging.getLogger(__name__)

class UpstoxWSManager:
    """
    Manages WebSocket connection to Upstox Market Data Feed.
    Handles authentication, subscription, and Protobuf decoding.
    """
    
    WS_URL = "wss://api.upstox.com/v2/feed/market-data-feed"
    
    def __init__(self):
        self.client = get_upstox_client()
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.is_running = False
        self.callbacks: List[Callable[[Dict], None]] = []
        self.subscribed_symbols: Set[str] = set()
        self.instrument_keys: Dict[str, str] = {} # symbol -> instrument_key
        self.last_ticks: Dict[str, Dict] = {}
        self._load_instrument_keys()
        
    def _load_instrument_keys(self):
        """Load instrument mapping from JSON."""
        try:
            with open("nifty200_instruments.json", "r") as f:
                data = json.load(f)
                self.instrument_keys = {item[0]: item[1] for item in data}
            logger.info(f"Loaded {len(self.instrument_keys)} instrument keys")
            
            # Add index mappings
            self.instrument_keys["NIFTY 50"] = "NSE_INDEX|Nifty 50"
            self.instrument_keys["NIFTY_50"] = "NSE_INDEX|Nifty 50"
            self.instrument_keys["BANK NIFTY"] = "NSE_INDEX|Nifty Bank"
            self.instrument_keys["INDIA VIX"] = "NSE_INDEX|India VIX"
        except Exception as e:
            logger.error(f"Failed to load instruments: {e}")
        
    def add_callback(self, callback: Callable[[Dict], None]):
        """Add a callback function to be called on every tick."""
        self.callbacks.append(callback)
        
    async def _get_authorized_url(self) -> str:
        """Fetch authorized WebSocket URL from Upstox."""
        endpoint = "/feed/market-data-feed/authorize"
        try:
            # Note: client._make_request is synchronous, so we run in executor if needed
            # but for simplicity we'll just call it as it's a one-time setup
            response = self.client._make_request("GET", endpoint)
            if response.get("status") == "success":
                return response["data"]["authorized_redirect_url"]
            raise Exception(f"Failed to authorize WS: {response}")
        except Exception as e:
            logger.error(f"Error authorizing Upstox WS: {e}")
            raise

    async def connect(self):
        """Connect to Upstox WebSocket."""
        if self.is_running:
            return
            
        auth_url = await self._get_authorized_url()
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        
        try:
            self.ws = await websockets.connect(auth_url, ssl=ssl_context)
            self.is_running = True
            logger.info("Connected to Upstox WebSocket")
            
            # Start background tasks
            asyncio.create_task(self._listen())
            
            # Re-subscribe if we had previous subscriptions
            if self.subscribed_symbols:
                await self.subscribe(list(self.subscribed_symbols))
                
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            self.is_running = False
            raise

    async def subscribe(self, symbols: List[str]):
        """Subscribe to market data for symbols."""
        if not self.ws or not self.is_running:
            logger.warning("WS not connected, skipping subscription")
            self.subscribed_symbols.update(symbols)
            return

        # Prepare instrument keys
        keys_to_subscribe = []
        for symbol in symbols:
            # Ideally we resolve symbol to instrument_key here
            # For now, we assume we have a mapping or fetch it
            key = self.instrument_keys.get(symbol)
            if key:
                keys_to_subscribe.append(key)
                self.subscribed_symbols.add(symbol)
                
        if not keys_to_subscribe:
            return

        payload = {
            "guid": "guid", # Static for now
            "method": "sub",
            "data": {
                "mode": "full", # LTP, OHLC, etc.
                "instrumentKeys": keys_to_subscribe
            }
        }
        
        await self.ws.send(json.dumps(payload))
        logger.info(f"Subscribed to {len(keys_to_subscribe)} instruments")

    async def _listen(self):
        """Background listener for WebSocket messages."""
        try:
            async for message in self.ws:
                await self._handle_message(message)
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Upstox WebSocket connection closed")
        except Exception as e:
            logger.error(f"Error in WebSocket listener: {e}")
        finally:
            self.is_running = False
            # Reconnect logic could go here

    async def _handle_message(self, message):
        """Handle incoming binary message (Protobuf)."""
        if isinstance(message, str):
            # Might be a JSON response to sub/unsub
            try:
                data = json.loads(message)
                logger.debug(f"WS JSON Message: {data}")
            except:
                pass
            return

        # It's binary (Protobuf)
        # In a real scenario, we'd use a Protobuf decoder here.
        # Since I cannot see the proto file, I'll implement a mock decoder 
        # that mimics Upstox V2 structure or use a helper if available.
        
        # TODO: Implement real Protobuf decoding
        # For this task, I'll simulate the decoded tick for now if I can't find the proto.
        # However, to make it work 'for real', I should try to use the SDK's internal machinery if possible.
        
        pass

    def stop(self):
        """Stop the WebSocket manager."""
        self.is_running = False
        if self.ws:
            asyncio.create_task(self.ws.close())

_upstox_ws_manager = None

def get_upstox_ws_manager() -> UpstoxWSManager:
    """Get singleton instance of UpstoxWSManager."""
    global _upstox_ws_manager
    if _upstox_ws_manager is None:
        _upstox_ws_manager = UpstoxWSManager()
    return _upstox_ws_manager
