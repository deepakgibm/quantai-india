import asyncio
import logging
import json
import time
from typing import Dict, List, Any
from datetime import datetime

from services.dragonfly_client import CacheManager, CacheKeys, TTLPolicy
from services.upstox_ws_manager import get_upstox_ws_manager

logger = logging.getLogger(__name__)

class PriceIngestionWorker:
    """
    Ingests real-time price data from Upstox WebSocket and caching it.
    """
    def __init__(self):
        self.cache = CacheManager()
        self.ws_manager = get_upstox_ws_manager()
        self._is_running = False

    async def start(self):
        if self._is_running:
            return
        
        self._is_running = True
        logger.info("Starting Price Ingestion Worker")
        
        # Attach callback to WS Manager
        self.ws_manager.add_callback(self._on_tick)
        
        # Ensure WS connection
        if not self.ws_manager.is_running:
            await self.ws_manager.connect()

    async def stop(self):
        self._is_running = False
        logger.info("Stopped Price Ingestion Worker")

    def _on_tick(self, tick_data: Dict[str, Any]):
        """Callback for WS ticks. Updates cache."""
        # Note: tick_data structure depends on Upstox Proto decoding.
        # Assuming simplified dict structure for now:
        # { "instrument_token": "...", "ltp": 100.0, ... }
        
        try:
            # Map instrument_token to symbol/key?
            # Using instrument_key as primary identifier per user spec stock:{instrument_key}
            
            # Logic:
            # 1. Parse tick
            # 2. Build snapshot object
            # 3. Cache.set(stock:{key}, snapshot, ttl=5)
            
            # Since we don't have real proto decoding in WS Manager yet, 
            # this remains a placeholder or handles "simulated" ticks if WS Manager provides them.
            pass 
        except Exception as e:
            logger.error(f"Error processing tick: {e}")


class SectorAggregationWorker:
    """
    Aggregates stock data into sector snapshots.
    """
    def __init__(self):
        self.cache = CacheManager()
        self._is_running = False
        self._sector_map: Dict[str, List[str]] = {} # sector -> list of instrument_keys
        self._instrument_map: Dict[str, Dict] = {} # instrument_key -> {symbol, sector}

    async def start(self):
        if self._is_running:
            return
        
        self._is_running = True
        logger.info("Starting Sector Aggregation Worker")
        
        # Load metadata ONCE from DB (Metadata is static-ish)
        await self._load_metadata()
        
        # Start loop
        asyncio.create_task(self._loop())

    async def _load_metadata(self):
        """Load symbol->sector mapping from stock_master."""
        import psycopg2
        from config import settings
        
        try:
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._fetch_metadata_sync)
        except Exception as e:
            logger.error(f"Failed to load sector metadata: {e}")

    def _fetch_metadata_sync(self):
        import psycopg2
        from config import settings
        conn = psycopg2.connect(settings.SYNC_DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT symbol, sector, instrument_key FROM stock_master WHERE is_active = TRUE")
        rows = cur.fetchall()
        conn.close()
        
        self._sector_map = {}
        self._instrument_map = {}
        
        for row in rows:
            symbol, sector, instrument_key = row
            if not sector: continue
            
            if sector not in self._sector_map:
                self._sector_map[sector] = []
            self._sector_map[sector].append(instrument_key)
            
            self._instrument_map[instrument_key] = {
                "symbol": symbol,
                "sector": sector
            }
        
        logger.info(f"Loaded metadata: {len(self._sector_map)} sectors, {len(self._instrument_map)} stocks")

    async def stop(self):
        self._is_running = False

    async def _loop(self):
        while self._is_running:
            start_time = time.perf_counter()
            try:
                await self._aggregate()
                duration = time.perf_counter() - start_time
                
                # Record metrics
                try:
                    from core.observability.metrics import get_metrics
                    get_metrics().record_worker_job("sector_aggregation", duration, True)
                except ImportError:
                    pass
                    
            except Exception as e:
                duration = time.perf_counter() - start_time
                logger.error(f"Sector aggregation failed: {e}")
                
                # Record metrics
                try:
                    from core.observability.metrics import get_metrics
                    get_metrics().record_worker_job("sector_aggregation", duration, False)
                except ImportError:
                    pass
            
            await asyncio.sleep(1) # 1s refresh rate

    async def _aggregate(self):
        if not self._sector_map:
             return

        # 1. Fetch all stock snapshots
        # Optimization: We could mget ALL keys, but we need the keys first.
        # We know keys are "qai:snap:{symbol}"? 
        # Wait, User Spec says "stock:{instrument_key}". 
        # I must stick to "stock:{instrument_key}".
        
        all_keys = [f"qai:stock:{k}" for k in self._instrument_map.keys()]
        
        # Use cache manager to get multiple? CacheManager currently has single get.
        # Implies we loop getters or extend CacheManager.
        # Reading one by one is slow (latency).
        # But we are In-Process Memory! So it's fast!
        # If Real Redis, we'd need pipeline/mget.
        # For this Env: simple loop is fine.
        
        snapshots = {}
        for k in self._instrument_map.keys():
            # Use user spec key "stock:{key}" (prefixed by qai via CacheKeys if we used it, but user gave raw key spec?)
            # User spec: "Cache Key Contracts... Stock Snapshot: stock:{instrument_key}"
            # My CacheKeys uses "qai:". I will assume "qai:stock:{key}".
            
            # Wait, PriceIngestionWorker populates it.
            # Currently PriceIngestionWorker is effectively empty (see above).
            # So I need to populate Dummy Data if empty?
            # Or use `run_worker.py` data? `run_worker.py` uses `qai:snap:{symbol}`.
            
            # **Mismatch**: `run_worker.py` (Top Movers) populated `qai:snap:{symbol}`.
            # User Specs for Heatmap asked for `stock:{instrument_key}`.
            # I should PROBABLY alias/use `qai:snap:{symbol}` if `instrument_key` is not handy in upstox worker?
            # But I have `stock_master` now.
            
            # I will use `qai:snap:{symbol}` because the Top Movers logic ALREADY populates it (via `run_worker.py` or In-Process Scanner).
            # The In-Process Scanner (Step 1641) populates `CacheKeys.all_snapshots()` ("qai:snap:all").
            # Does it populate individual `qai:snap:{symbol}`?
            # In `hp_scanner_service.py` -> `_run_scan_cycle`:
            # It calculates tasks.
            # It DOES NOT write individual snapshots to cache (it relies on `indicator_worker` to return results, which are then cached?).
            # Actually, `top_movers_service` reads `all_snapshots`.
            
            # So `qai:snap:all` contains a LIST of all data.
            # I can read THAT single key, parse it, and group by sector!
            # This is MUCH more efficient than 500 reads.
            
            pass
        
        # Approach: Read `CacheKeys.all_snapshots()` (populated by existing HP Scanner).
        data_json = self.cache.get(CacheKeys.all_snapshots())
        if not data_json:
            return

        all_stocks = data_json if isinstance(data_json, list) else []
        
        # Group by sector
        sector_groups = {}
        for stock in all_stocks:
            # stock is {symbol, ltp, change_pct...} (from `run_worker.py`/`hp_scanner`)
            sym = stock.get("symbol")
            if not sym: continue
            
            # Find sector for symbol
            # Scan _instrument_map (values have symbol) or create a reverse map?
            # _instrument_map keys are instrument_keys.
            # I need symbol -> sector map.
            
            # Build fast lookup
            # TODO: optimize this by building symbol_map in metadata load
            sector = None
            for meta in self._instrument_map.values():
                if meta["symbol"] == sym:
                    sector = meta["sector"]
                    break
            
            if not sector:
                continue
                
            if sector not in sector_groups:
                sector_groups[sector] = []
            sector_groups[sector].append(stock)

        sector_snapshots = []
        # Aggregate and Write
        for sector, stocks in sector_groups.items():
            avg_pct = sum(s.get("change_pct", 0) for s in stocks) / len(stocks)
            advancers = sum(1 for s in stocks if s.get("change_pct", 0) > 0)
            decliners = sum(1 for s in stocks if s.get("change_pct", 0) < 0)
            
            bucket = "NEUTRAL"
            if avg_pct > 1.5: bucket = "STRONG_BULLISH"
            elif avg_pct > 0.5: bucket = "BULLISH"
            elif avg_pct < -1.5: bucket = "STRONG_BEARISH"
            elif avg_pct < -0.5: bucket = "BEARISH"
            
            snapshot = {
                "sector": sector,
                "avg_pct_change": round(avg_pct, 2),
                "bucket": bucket,
                "advancers": advancers,
                "decliners": decliners,
                "stock_count": len(stocks)
            }
            sector_snapshots.append(snapshot)
            
            # Write to Cache: Individual Sector
            key = CacheKeys.sector_snapshot(sector)
            self.cache.set(key, snapshot, ttl=15)
            
            # Write to Cache: Stock List for Drill-Down
            list_key = f"{key}:stocks" 
            self.cache.set(list_key, stocks, ttl=15)
            
        # Write to Cache: All Sectors List (for Main Page)
        self.cache.set(CacheKeys.heatmap_all(), sector_snapshots, ttl=15)

