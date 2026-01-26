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

from services.upstox_client import get_upstox_client
from utils.upstox_proto import decode_market_data

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
        self.key_to_symbol: Dict[str, str] = {}   # instrument_key -> symbol
        self.last_ticks: Dict[str, Dict] = {}
        self._load_instrument_keys()
        
    async def _resolve_instrument_keys(self, symbols: List[str]) -> List[str]:
        """Resolve instrument keys for symbols, checking cache first then DB."""
        unresolved = []
        keys = []
        
        for symbol in symbols:
            # Check cache
            key = self.instrument_keys.get(symbol.upper())
            if not key:
                # Try variants (BANK NIFTY vs BANKNIFTY)
                clean_sym = symbol.upper().replace(" ", "").replace("_", "")
                key = self.instrument_keys.get(clean_sym)
            
            if key:
                keys.append(key)
            else:
                unresolved.append(symbol.upper())
                
        if unresolved:
            try:
                from database import AsyncSessionLocal
                from sqlalchemy import text
                
                async with AsyncSessionLocal() as session:
                    query = text("SELECT symbol, instrument_key FROM instrument_master WHERE symbol = ANY(:symbols)")
                    result = await session.execute(query, {"symbols": unresolved})
                    for row in result:
                        sym, key = row[0], row[1]
                        self.instrument_keys[sym] = key
                        self.key_to_symbol[key] = sym
                        keys.append(key)
                        logger.debug(f"Resolved {sym} -> {key} from DB")
            except Exception as e:
                logger.error(f"Error resolving keys from DB: {e}")
                
        return keys

    def _load_instrument_keys(self):
        """Load initial instrument mapping from JSON."""
        try:
            with open("nifty200_instruments.json", "r") as f:
                data = json.load(f)
                self.instrument_keys = {item[0].upper(): item[1] for item in data}
            logger.info(f"Loaded {len(self.instrument_keys)} instrument keys")
            
            # Add index mappings
            self.instrument_keys["NIFTY 50"] = "NSE_INDEX|Nifty 50"
            self.instrument_keys["NIFTY_50"] = "NSE_INDEX|Nifty 50"
            self.instrument_keys["BANK NIFTY"] = "NSE_INDEX|Nifty Bank"
            self.instrument_keys["INDIA VIX"] = "NSE_INDEX|India VIX"
        except Exception as e:
            logger.error(f"Failed to load instruments: {e}")
        
        # Create reverse mapping
        self.key_to_symbol = {v: k for k, v in self.instrument_keys.items()}
        
    def add_callback(self, callback: Callable[[Dict], None]):
        """Add a callback function to be called on every tick."""
        self.callbacks.append(callback)
        
    async def _get_authorized_url(self) -> str:
        """Fetch authorized WebSocket URL from Upstox."""
        endpoint = "/feed/market-data-feed/authorize"
        try:
            # Await the async _make_request method
            response = await self.client._make_request("GET", endpoint)
            if response.get("status") == "success":
                return response["data"]["authorized_redirect_url"]
            raise Exception(f"Failed to authorize WS: {response}")
        except Exception as e:
            logger.error(f"Error authorizing Upstox WS: {e}")
            raise

    async def connect(self, max_retries: int = 5):
        """
        Connect to Upstox WebSocket with exponential backoff retry.
        
        Args:
            max_retries: Maximum connection attempts (default 5)
            
        Retry delays: 1s, 2s, 4s, 8s, 16s (exponential backoff)
        """
        if self.is_running:
            return
        
        for attempt in range(max_retries):
            try:
                auth_url = await self._get_authorized_url()
                ssl_context = ssl.create_default_context(cafile=certifi.where())
                
                self.ws = await websockets.connect(
                    auth_url, 
                    ssl=ssl_context,
                    ping_interval=30,
                    ping_timeout=10
                )
                self.is_running = True
                self._reconnect_attempts = 0
                logger.info(f"Connected to Upstox WebSocket (attempt {attempt + 1})")
                
                # Start background listener
                asyncio.create_task(self._listen())
                
                # Re-subscribe if we had previous subscriptions
                if self.subscribed_symbols:
                    await self.subscribe(list(self.subscribed_symbols))
                
                return  # Success
                
            except Exception as e:
                wait_time = 2 ** attempt  # 1, 2, 4, 8, 16 seconds
                logger.warning(f"WebSocket connection attempt {attempt + 1}/{max_retries} failed: {e}")
                
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
        
        # All retries exhausted
        self.is_running = False
        raise ConnectionError(f"WebSocket connection failed after {max_retries} attempts")

    async def subscribe(self, symbols: List[str]):
        """Subscribe to market data for symbols."""
        if not self.ws or not self.is_running:
            logger.warning("WS not connected, skipping subscription")
            self.subscribed_symbols.update(symbols)
            return

        # Resolve instrument keys (cache + DB)
        keys_to_subscribe = await self._resolve_instrument_keys(symbols)
        
        for symbol in symbols:
            self.subscribed_symbols.add(symbol.upper())
                
        if not keys_to_subscribe:
            logger.warning(f"Could not resolve any instrument keys for: {symbols}")
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
        ticks = decode_market_data(message)
        
        for key, tick in ticks.items():
            symbol = self.key_to_symbol.get(key)
            if not symbol:
                continue
                
            tick["symbol"] = symbol
            self.last_ticks[symbol] = tick
            
            # Notify callbacks
            for callback in self.callbacks:
                try:
                    callback(tick)
                except Exception as e:
                    logger.error(f"Error in WS callback for {symbol}: {e}")

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
