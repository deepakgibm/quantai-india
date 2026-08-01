"""
Standalone Market Data Orchestrator
Adapted for Microservice Architecture — Publishes real-time ticks to Redis.
"""

import asyncio
import logging
import json
import os
from datetime import datetime
from typing import Dict, Optional

from services.upstox_ws_manager import get_upstox_ws_manager, UpstoxWSManager
from services.rest_data_fetcher import (
    get_rest_data_fetcher, 
    RESTDataFetcher
)
from services.db_data_fetcher import get_db_data_fetcher, DatabaseDataFetcher
from services.market_data_service.publisher import publish_tick
from utils.market_state import is_market_open

logger = logging.getLogger(__name__)

class DataSource:
    WEBSOCKET = "WS"
    REST = "REST"
    DATABASE = "DB"
    NONE = "NONE"

class MarketDataOrchestratorMS:
    """
    Microservice version of Market Data Orchestrator.
    Manages WebSocket + REST fallback and broadcasts to Redis Pub/Sub.
    """
    
    WS_TIMEOUT_SECONDS = 3.0
    RECONNECT_INTERVAL_SECONDS = 30
    VALID_TICKS_FOR_RECOVERY = 3
    
    def __init__(self):
        self.ws_manager: UpstoxWSManager = get_upstox_ws_manager()
        self.rest_fetcher: RESTDataFetcher = get_rest_data_fetcher()
        self.db_fetcher: DatabaseDataFetcher = get_db_data_fetcher()
        
        self.current_source = DataSource.NONE
        self.last_tick_time: Optional[datetime] = None
        self.consecutive_valid_ticks = 0
        
        self.is_running = False
        self._health_check_task: Optional[asyncio.Task] = None
        self._reconnect_task: Optional[asyncio.Task] = None
        self._rest_poll_task: Optional[asyncio.Task] = None
        self._db_poll_task: Optional[asyncio.Task] = None
        
        self._symbols = []
        self._load_symbols()
        
    def _load_symbols(self):
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "nifty200_instruments.json")
        try:
            with open(config_path, "r") as f:
                data = json.load(f)
                self._symbols = [(item[0], item[1]) for item in data]
            logger.info(f"Orchestrator MS loaded {len(self._symbols)} symbols")
        except Exception as e:
            logger.error(f"Failed to load symbols: {e}")

    async def start(self):
        self.is_running = True
        logger.info("Starting Market Data Orchestrator Microservice")
        
        # Initial connection attempt based on market hours
        if is_market_open():
            try:
                await self._connect_websocket()
            except Exception as e:
                logger.warning(f"Initial WS failed: {e}, using REST")
                await self._switch_to_rest()
        else:
            logger.info("Market is CLOSED. Starting with Database source.")
            await self._switch_to_db()
            
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def _connect_websocket(self):
        self.ws_manager.add_callback(self._on_ws_tick)
        await self.ws_manager.connect()
        if self.ws_manager.is_running:
            self.current_source = DataSource.WEBSOCKET
            self.last_tick_time = datetime.now()
            await self.ws_manager.subscribe([s[0] for s in self._symbols[:50]])
        else:
            raise Exception("WebSocket failed to start")

    async def _switch_to_rest(self):
        self.current_source = DataSource.REST
        if self._rest_poll_task and not self._rest_poll_task.done():
            self._rest_poll_task.cancel()
        self._rest_poll_task = asyncio.create_task(self._rest_poll_loop())

    async def _rest_poll_loop(self):
        while self.is_running and self.current_source == DataSource.REST:
            try:
                ticks = await self.rest_fetcher.fetch_quotes(self._symbols[:50])
                for symbol, tick in ticks.items():
                    await publish_tick(tick.to_dict())
            except Exception as e:
                logger.error(f"REST poll error: {e}")
            await asyncio.sleep(self.rest_fetcher.poll_interval)

    async def _switch_to_db(self):
        self.current_source = DataSource.DATABASE
        if self._db_poll_task and not self._db_poll_task.done():
            self._db_poll_task.cancel()
        if self._rest_poll_task and not self._rest_poll_task.done():
            self._rest_poll_task.cancel()
        self._db_poll_task = asyncio.create_task(self._db_poll_loop())

    async def _db_poll_loop(self):
        logger.info("Starting Database polling loop (Market Closed)")
        while self.is_running and self.current_source == DataSource.DATABASE:
            try:
                ticks = self.db_fetcher.fetch_latest_data([s[1] for s in self._symbols[:50]])
                for symbol, tick in ticks.items():
                    # DatabaseTick needs to be compatible with expected Pub/Sub format
                    # Most frontend components expect 'symbol', 'ltp', 'change_pct'
                    await publish_tick(tick.to_dict())
            except Exception as e:
                logger.error(f"DB poll error: {e}")
            # Poll less frequently for DB data (e.g. every minute)
            await asyncio.sleep(60)

    async def _on_ws_tick(self, raw_tick: Dict):
        self.last_tick_time = datetime.now()
        self.consecutive_valid_ticks += 1
        # Broadcast to Pub/Sub
        asyncio.create_task(publish_tick(raw_tick))

    async def _health_check_loop(self):
        while self.is_running:
            await asyncio.sleep(1)
            if self.current_source == DataSource.WEBSOCKET and self.last_tick_time:
                if (datetime.now() - self.last_tick_time).total_seconds() > self.WS_TIMEOUT_SECONDS:
                    logger.warning("WS Timeout in MS Orchestrator, falling back to REST")
                    await self._switch_to_rest()

    async def _reconnect_loop(self):
        while self.is_running:
            await asyncio.sleep(self.RECONNECT_INTERVAL_SECONDS)
            
            market_open = is_market_open()
            
            # Transition: Market just OPENED or we are in REST during open market
            if market_open and self.current_source in [DataSource.REST, DataSource.DATABASE]:
                try:
                    logger.info(f"Attempting to upgrade to WebSocket (Market Open: {market_open})")
                    await self._connect_websocket()
                    self.current_source = DataSource.WEBSOCKET
                    if self._rest_poll_task: self._rest_poll_task.cancel()
                    if self._db_poll_task: self._db_poll_task.cancel()
                except Exception:
                    if self.current_source == DataSource.DATABASE:
                        logger.info("WS upgrade failed and market is open, switching to REST")
                        await self._switch_to_rest()
            
            # Transition: Market just CLOSED
            elif not market_open and self.current_source != DataSource.DATABASE:
                logger.info("Market is CLOSED. Switching to Database source.")
                await self._switch_to_db()
                if self.ws_manager.is_running:
                    self.ws_manager.stop()

    async def stop(self):
        self.is_running = False
        if self._health_check_task: self._health_check_task.cancel()
        if self._reconnect_task: self._reconnect_task.cancel()
        if self._rest_poll_task: self._rest_poll_task.cancel()
        if self._db_poll_task: self._db_poll_task.cancel()
        self.ws_manager.stop()
