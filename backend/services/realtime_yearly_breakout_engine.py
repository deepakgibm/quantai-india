
"""
Real-Time Yearly Breakout Engine
Monitors live prices against 52-week High/Low levels.
Populates CacheKeys.breakout() for HP API.
"""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from services.upstox_price_resolver import get_upstox_price_resolver
from services.websocket_feed_manager import get_websocket_feed_manager
from services.db_data_fetcher import get_db_data_fetcher
from services.dragonfly_client import get_cache, CacheKeys
from utils.symbol_utils import _symbol_manager

logger = logging.getLogger(__name__)

class RealTimeYearlyBreakoutEngine:
    """
    Monitors all Nifty 500 stocks for 52-week breakouts in real-time.
    Initialization: Loads 52-week High/Low from DB.
    Run Loop: Processes ticks, updates state, writes to Redis.
    """
    
    def __init__(self):
        self.feed_manager = get_websocket_feed_manager()
        self.levels: Dict[str, Dict] = {} # symbol -> {high_52w: float, low_52w: float, industry: str}
        self.breakouts: Dict[str, Dict] = {} # symbol -> BreakoutData
        self._is_initialized = False
        
        # Register for tick updates
        from services.upstox_ws_manager import get_upstox_ws_manager
        get_upstox_ws_manager().add_callback(self._on_tick_raw)

    async def initialize(self):
        """Load 52-week levels from DB and start monitoring."""
        if self._is_initialized:
            return
            
        logger.info("Initializing Real-Time Yearly Breakout Engine")
        
        # 1. Load 52-week levels (Heavy DB query, do once)
        await self._load_levels_from_db()
        
        try:
            # 2. Ensure Feed Active
            await self.feed_manager.ensure_active()
            
            # 3. Start Cache Loop
            asyncio.create_task(self._cache_write_loop())
        except Exception as e:
            logger.error(f"Failed to start websocket feed in RealTimeYearlyBreakoutEngine: {e}")
            
        self._is_initialized = True
        
    async def _load_levels_from_db(self):
        """Fetch 52-week High/Low for all active symbols."""
        # Ideally, we query stock_candle_history.
        # For MVP speed, we can assume YearlyBreakoutEngine has run recently and cached its results,
        # OR we can query the DB. 
        # Let's query DB for robustness.
        
        # We need a service/function to get these stats.
        # Since I can't easily write complex SQL here without raw connection, 
        # I'll try to rely on 'instrument_master' if it had 52w data, but it doesn't.
        # I'll rely on `YearlyBreakoutEngine` to perform an initial scan/load if cache is empty,
        # OR I'll create a helper to fetch from DB.
        
        # Fallback: Use `YearlyBreakoutEngine` to seed the data if levels are empty.
        # But `YearlyBreakoutEngine` is slow (API calls).
        # We need to compute from DB.
        
        # Let's write a direct DB query for efficiency.
        try:
            from sqlalchemy import text
            from database import get_db_session_context
            
            async with get_db_session_context() as session:
                # Query max high and min low for last 365 days AND latest close
                # Use a CTE to get the latest price efficiently
                query = text("""
                    WITH stats AS (
                        SELECT 
                            mk.symbol, 
                            MAX(sch.high) as year_high, 
                            MIN(sch.low) as year_low
                        FROM stock_candle sch
                        JOIN instrument_master mk ON sch.instrument_id = mk.instrument_id
                        WHERE sch.candle_ts > NOW() - INTERVAL '365 days'
                        GROUP BY mk.symbol
                    ),
                    latest AS (
                        SELECT DISTINCT ON (mk.symbol) 
                            mk.symbol, 
                            sch.close as last_price,
                            sch.candle_ts
                        FROM stock_candle sch
                        JOIN instrument_master mk ON sch.instrument_id = mk.instrument_id
                        ORDER BY mk.symbol, sch.candle_ts DESC
                    )
                    SELECT 
                        s.symbol, 
                        s.year_high, 
                        s.year_low, 
                        l.last_price
                    FROM stats s
                    JOIN latest l ON s.symbol = l.symbol
                """)
                
                result = await session.execute(query)
                rows = result.fetchall()
                
                count = 0
                breakout_count = 0
                for row in rows:
                    if row.symbol:
                        high_52w = float(row.year_high) if row.year_high else 0
                        low_52w = float(row.year_low) if row.year_low else 0
                        ltp = float(row.last_price) if row.last_price else 0
                        
                        # Store Levels
                        self.levels[row.symbol] = {
                            "high_52w": high_52w,
                            "low_52w": low_52w,
                            "industry": _symbol_manager.get_stock_sector(row.symbol)
                        }
                        
                        # CHECK FOR BREAKOUTS IMMEDIATELY
                        breakout_type = "NONE"
                        breakout_pct = 0.0
                        
                        if high_52w > 0 and ltp >= high_52w * 0.99:
                            breakout_type = "52W_HIGH" if ltp > high_52w else "Yearly High"
                            breakout_pct = ((ltp - high_52w) / high_52w) * 100
                            
                        elif low_52w > 0 and ltp <= low_52w * 1.01:
                            breakout_type = "52W_LOW" if ltp < low_52w else "Yearly Low"
                            breakout_pct = ((ltp - low_52w) / low_52w) * 100
                            
                        if breakout_type != "NONE":
                            self.breakouts[row.symbol] = {
                                "symbol": row.symbol,
                                "ltp": ltp,
                                "high_52w": high_52w,
                                "low_52w": low_52w,
                                "prev_close": ltp, # Approximate since we don't have prev close immediate
                                "change_pct": 0.0, # Can't calc without prev day close
                                "breakout_type": breakout_type,
                                "breakout_pct": round(breakout_pct, 2),
                                "volume_ratio": 1.0, 
                                "volume_strength": "Normal",
                                "industry": self.levels[row.symbol]["industry"],
                                "timestamp": datetime.now().isoformat()
                            }
                            breakout_count += 1
                        
                        count += 1
                
                logger.info(f"Loaded 52-week levels for {count} symbols. Found {breakout_count} initial breakouts.")
                
        except Exception as e:
            logger.error(f"Failed to load 52-week levels from DB: {e}")

    def bulk_update(self, breakouts: List[Dict]):
        """
        Force update internal breakout state with a batch of breakouts (e.g. from manual scan).
        This synchronizes the WebSocket feed with REST refreshes.
        """
        if not breakouts:
            return
            
        logger.info(f"Bulk updating RealTimeYearlyBreakoutEngine state with {len(breakouts)} items")
        for item in breakouts:
            symbol = item.get("symbol")
            if not symbol:
                continue
                
            # Update internal breakout state
            self.breakouts[symbol] = {
                **item,
                "timestamp": item.get("timestamp", datetime.now().isoformat())
            }

    def _on_tick_raw(self, raw_tick: Dict):
        try:
            symbol = raw_tick.get("symbol")
            if not symbol or symbol not in self.levels:
                return
                
            ltp = raw_tick.get("last_price", 0)
            if ltp <= 0: return
            
            levels = self.levels[symbol]
            high_52w = levels["high_52w"]
            low_52w = levels["low_52w"]
            
            # Update levels if new high/low (Dynamic)
            if ltp > high_52w:
                levels["high_52w"] = ltp
                high_52w = ltp
            if ltp < low_52w and low_52w > 0:
                levels["low_52w"] = ltp
                low_52w = ltp
                
            # Check for Breakout
            breakout_type = "NONE"
            breakout_pct = 0.0
            
            # Simple Logic: LTP close to High or Low
            # Near High (within 1%) or Breaking High
            if high_52w > 0 and ltp >= high_52w * 0.99:
                breakout_type = "52W_HIGH" if ltp > high_52w else "Yearly High"
                breakout_pct = ((ltp - high_52w) / high_52w) * 100
                
            elif low_52w > 0 and ltp <= low_52w * 1.01:
                breakout_type = "52W_LOW" if ltp < low_52w else "Yearly Low"
                breakout_pct = ((ltp - low_52w) / low_52w) * 100
            
            if breakout_type != "NONE":
                # Create/Update Breakout Record
                prev_close = raw_tick.get("prev_close") or raw_tick.get("previous_close") or ltp
                change_pct = ((ltp - prev_close) / prev_close) * 100
                
                self.breakouts[symbol] = {
                    "symbol": symbol,
                    "ltp": ltp,
                    "high_52w": high_52w,
                    "low_52w": low_52w,
                    "prev_close": prev_close,
                    "change_pct": round(change_pct, 2),
                    "breakout_type": breakout_type,
                    "breakout_pct": round(breakout_pct, 2),
                    "volume_ratio": 1.0, # Placeholder, need avg volume
                    "volume_strength": "Normal",
                    "industry": levels["industry"],
                    "timestamp": datetime.now().isoformat()
                }
            elif symbol in self.breakouts:
                # If it fell out of breakout zone, keep it for a while or remove?
                # For now, let's keep it but update price
                # Or remove if it's too far? 
                # Let's just update the price
                 self.breakouts[symbol].update({
                    "ltp": ltp,
                    "timestamp": datetime.now().isoformat()
                })
                
        except Exception as e:
            logger.error(f"Error processing breakout tick: {e}")

    async def _cache_write_loop(self):
        """Periodically cache breakout results."""
        cache = get_cache()
        while True:
            try:
                if self.breakouts:
                    data = list(self.breakouts.values())
                    # Cache to CacheKeys.breakout()
                    # Frontend expects { "high_breakouts": [], "low_breakdowns": [] } structure OR list?
                    # /hp/breakout returns { "type": "breakout", "data": [...] }
                    # Week52Breakout.tsx consumes /api/scanner/week52-breakouts which expects { high_breakouts: ... }
                    
                    # But the HP endpoint returns a flat list "data".
                    # I should match what the HP endpoint expects.
                    cache.set(CacheKeys.breakout(), data, ttl=60)
            except Exception as e:
                logger.error(f"Breakout cache write error: {e}")
            
            await asyncio.sleep(1)

# Singleton
_rt_breakout_engine = None

def get_realtime_yearly_breakout_engine() -> RealTimeYearlyBreakoutEngine:
    global _rt_breakout_engine
    if _rt_breakout_engine is None:
        _rt_breakout_engine = RealTimeYearlyBreakoutEngine()
    return _rt_breakout_engine

async def start_realtime_breakout_service():
    try:
        engine = get_realtime_yearly_breakout_engine()
        await engine.initialize()
    except Exception as e:
        logger.error(f"Failed to start realtime breakout service: {e}")
