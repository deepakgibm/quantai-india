import asyncio
import json
import logging
import os
import ssl
import certifi
import websockets
import httpx
from typing import Dict, List, Optional, Set

from services.upstox_client import get_upstox_client
from utils.upstox_proto import decode_market_data
from services.auth.token_manager import TokenManagerService
from database import SessionLocal
from services.market_feed_service.producer import KafkaProducerWrapper

logger = logging.getLogger(__name__)

class UpstoxFeedClient:
    def __init__(self, producer: KafkaProducerWrapper):
        self.producer = producer
        self.client = get_upstox_client()
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.is_running = False
        self.subscribed_symbols: Set[str] = set()
        self.instrument_keys: Dict[str, str] = {}
        self.key_to_symbol: Dict[str, str] = {}
        self._load_instrument_keys()

    def _load_instrument_keys(self):
        try:
            # Look up instruments
            path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "nifty200_instruments.json")
            if not os.path.exists(path):
                path = "nifty200_instruments.json"
            if os.path.exists(path):
                with open(path, "r") as f:
                    data = json.load(f)
                    self.instrument_keys = {item[0].upper(): item[1] for item in data}
            else:
                logger.warning("nifty200_instruments.json not found in market_feed_service initialization")
            
            # Index mappings
            self.instrument_keys["NIFTY 50"] = "NSE_INDEX|Nifty 50"
            self.instrument_keys["NIFTY_50"] = "NSE_INDEX|Nifty 50"
            self.instrument_keys["BANK NIFTY"] = "NSE_INDEX|Nifty Bank"
            self.instrument_keys["INDIA VIX"] = "NSE_INDEX|India VIX"
            
            logger.info(f"Loaded {len(self.instrument_keys)} instrument keys for feed client")
        except Exception as e:
            logger.error(f"Failed to load instruments: {e}")
        
        self.key_to_symbol = {v: k for k, v in self.instrument_keys.items()}

    async def _get_authorized_url(self) -> str:
        db = SessionLocal()
        try:
            manager = TokenManagerService(db)
            analytics_token = manager.get_analytics_token()
        finally:
            db.close()
            
        if not analytics_token:
            logger.error("NO ANALYTICS TOKEN AVAILABLE! Market Feed WS cannot connect.")
            raise Exception("Analytics Token Missing")

        endpoint = "https://api.upstox.com/v3/feed/market-data-feed/authorize"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {analytics_token}",
            "Api-Key": os.getenv("UPSTOX_API_KEY", "")
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(endpoint, headers=headers)
            if response.status_code == 401:
                logger.critical("UPSTOX AUTH FAILURE: 401 Unauthorized on WS Authorization endpoint.")
                raise PermissionError("Upstox Unauthorized: Check Analytics Token/API Key")
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "success":
                return data["data"].get("authorized_redirect_uri") or data["data"].get("authorized_redirect_url")
            raise Exception(f"Failed to authorize WS: {data}")

    async def start(self):
        self.is_running = True
        asyncio.create_task(self._connection_loop())

    async def stop(self):
        self.is_running = False
        if self.ws:
            await self.ws.close()

    async def _connection_loop(self):
        attempt = 0
        while self.is_running:
            try:
                auth_url = await self._get_authorized_url()
                ssl_context = ssl.create_default_context(cafile=certifi.where())
                
                self.ws = await websockets.connect(
                    auth_url, 
                    ssl=ssl_context,
                    ping_interval=30,
                    ping_timeout=10
                )
                logger.info("Connected to Upstox WebSocket feed client")
                attempt = 0 # reset retry count
                
                # Subscribe to all loaded instruments
                if self.instrument_keys:
                    await self.subscribe(list(self.instrument_keys.keys()))
                
                # Listen loop
                async for message in self.ws:
                    if not self.is_running:
                        break
                    await self._handle_message(message)
                    
            except Exception as e:
                attempt += 1
                wait_time = min(30, 2 ** attempt)
                logger.error(f"WebSocket feed client connection error (attempt {attempt}): {e}. Retrying in {wait_time}s")
                await asyncio.sleep(wait_time)

    async def subscribe(self, symbols: List[str]):
        if not self.ws or not self.is_running:
            return
        keys = []
        for symbol in symbols:
            key = self.instrument_keys.get(symbol.upper())
            if key:
                keys.append(key)
                self.subscribed_symbols.add(symbol.upper())
        if not keys:
            return
        payload = {
            "guid": "guid",
            "method": "sub",
            "data": {
                "mode": "full",
                "instrumentKeys": keys
            }
        }
        await self.ws.send(json.dumps(payload))
        logger.info(f"WS Feed Client Subscribed to {len(keys)} instruments")

    async def _handle_message(self, message):
        if isinstance(message, str):
            return
        try:
            ticks = decode_market_data(message)
            for key, tick in ticks.items():
                symbol = self.key_to_symbol.get(key)
                if not symbol:
                    continue
                tick["symbol"] = symbol
                # Publish to Kafka ticks.raw topic
                await self.producer.send_msg("ticks.raw", tick)
        except Exception as e:
            logger.error(f"Error handling feed WS tick message: {e}")
