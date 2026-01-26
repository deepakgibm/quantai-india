"""
Background Scanner Service
Runs independently from FastAPI, processes market data, updates snapshots.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import threading

from engine.state import get_state_manager
from engine.indicators import compute_indicators_for_symbol
from engine.strategy_engine import evaluate_all_strategies

logger = logging.getLogger(__name__)


class ScannerService:
    """
    Background service that:
    1. Listens to market data (WebSocket or REST polling)
    2. Updates in-memory state
    3. Computes indicators once per symbol
    4. Evaluates strategies
    5. Writes results to scanner_snapshot table
    
    FastAPI handlers NEVER compute anything - they read snapshots.
    """
    
    def __init__(self):
        self._is_running = False
        self._scan_interval = 5  # seconds between scans
        self._state_manager = get_state_manager()
        self._last_scan_time: Optional[datetime] = None
        self._scan_results: Dict[str, Dict[str, Any]] = {}  # symbol -> snapshot
        self._lock = threading.Lock()
    
    async def start(self):
        """Start the background scanner service."""
        if self._is_running:
            logger.warning("Scanner service already running")
            return
        
        self._is_running = True
        logger.info("Starting background scanner service")
        
        # Initial warm-up from database
        await self._warm_up()
        
        # Start scan loop
        asyncio.create_task(self._scan_loop())
    
    async def stop(self):
        """Stop the background scanner service."""
        self._is_running = False
        logger.info("Stopping background scanner service")
    
    async def _warm_up(self):
        """Load initial data from database using actual symbols in DB."""
        import psycopg2
        from config import settings
        
        logger.info("Starting warm-up from database")
        
        try:
            conn = psycopg2.connect(settings.SYNC_DATABASE_URL)
            cur = conn.cursor()
            
            # Get all distinct symbols from database (limit to avoid overload)
            cur.execute("SELECT DISTINCT symbol FROM stock_data LIMIT 200")
            symbols = [row[0] for row in cur.fetchall()]
            conn.close()
            
            logger.info(f"Found {len(symbols)} symbols in database")
            
            if symbols:
                # Run warm-up in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    self._state_manager.warm_up_from_db,
                    symbols,
                    "1d",  # Use daily interval for main analysis
                    200
                )
            
            logger.info(f"Warm-up complete: {self._state_manager.get_symbol_count()} symbols loaded")
            
        except Exception as e:
            logger.error(f"Warm-up failed: {e}")

    
    async def _scan_loop(self):
        """Main scan loop - runs continuously in background thread."""
        while self._is_running:
            try:
                # Run scan cycle in thread pool to avoid blocking event loop
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._run_scan_cycle_sync)
            except Exception as e:
                logger.error(f"Scan cycle error: {e}")
            
            await asyncio.sleep(self._scan_interval)
    
    def _run_scan_cycle_sync(self):
        """
        Execute one scan cycle across all symbols.
        This runs in a separate thread, not blocking the event loop.
        """
        start_time = datetime.now()
        
        symbols = self._state_manager.get_all_symbols()
        if not symbols:
            logger.debug("No symbols in state, skipping scan cycle")
            return
        
        signals_found = 0
        
        for symbol in symbols:
            try:
                # Compute indicators (cached per symbol)
                indicators = compute_indicators_for_symbol(symbol, "1d")
                if not indicators:
                    continue
                
                # Evaluate all strategies
                signals = evaluate_all_strategies(symbol, "1d")
                
                # Get symbol state
                symbol_state = self._state_manager.get_symbol(symbol)
                if not symbol_state:
                    continue
                
                # Build snapshot
                snapshot = {
                    "symbol": symbol,
                    "interval": "1d",
                    "ltp": symbol_state.ltp,
                    "prev_close": symbol_state.prev_close,
                    "change_pct": symbol_state.change_pct,
                    "indicators": indicators.to_dict(),
                    "active_strategies": [s.strategy_name for s in signals],
                    "signal_types": [s.signal_type.value for s in signals],
                    "signal_strength": max([s.confidence for s in signals], default=0),
                    "momentum_bucket": self._get_momentum_bucket(symbol_state.change_pct),
                    "trend_direction": self._get_trend_direction(indicators),
                    "updated_at": datetime.now().isoformat()
                }
                
                with self._lock:
                    self._scan_results[symbol] = snapshot
                
                signals_found += len(signals)
                
            except Exception as e:
                logger.error(f"Scan error for {symbol}: {e}")
        
        duration = (datetime.now() - start_time).total_seconds()
        self._last_scan_time = datetime.now()
        
        logger.info(f"Scan cycle complete: {len(symbols)} symbols, {signals_found} signals, {duration:.2f}s")

    
    def _get_momentum_bucket(self, change_pct: float) -> str:
        """Map change percentage to momentum bucket."""
        abs_change = abs(change_pct)
        is_bullish = change_pct >= 0
        
        if abs_change >= 5.0:
            return "EXTREME_BULLISH" if is_bullish else "EXTREME_BEARISH"
        elif abs_change >= 3.0:
            return "STRONG_BULLISH" if is_bullish else "STRONG_BEARISH"
        elif abs_change >= 1.0:
            return "MODERATE_BULLISH" if is_bullish else "MODERATE_BEARISH"
        else:
            return "NEUTRAL"
    
    def _get_trend_direction(self, indicators) -> str:
        """Determine trend direction from indicators."""
        if indicators.ema_9 > indicators.ema_21 > indicators.ema_50:
            return "BULLISH"
        elif indicators.ema_9 < indicators.ema_21 < indicators.ema_50:
            return "BEARISH"
        else:
            return "NEUTRAL"
    
    def get_snapshot(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get pre-computed snapshot for a symbol."""
        with self._lock:
            return self._scan_results.get(symbol)
    
    def get_all_snapshots(self) -> List[Dict[str, Any]]:
        """Get all pre-computed snapshots."""
        with self._lock:
            return list(self._scan_results.values())
    
    def get_filtered_snapshots(
        self,
        signal_type: Optional[str] = None,
        momentum_bucket: Optional[str] = None,
        min_confidence: float = 0
    ) -> List[Dict[str, Any]]:
        """Get snapshots filtered by criteria."""
        with self._lock:
            results = list(self._scan_results.values())
        
        if signal_type:
            results = [r for r in results if signal_type in (r.get("signal_types") or [])]
        
        if momentum_bucket:
            results = [r for r in results if r.get("momentum_bucket") == momentum_bucket]
        
        if min_confidence > 0:
            results = [r for r in results if r.get("signal_strength", 0) >= min_confidence]
        
        return results
    
    def get_status(self) -> Dict[str, Any]:
        """Get scanner service status."""
        return {
            "is_running": self._is_running,
            "symbol_count": len(self._scan_results),
            "last_scan_time": self._last_scan_time.isoformat() if self._last_scan_time else None,
            "scan_interval": self._scan_interval,
            "state_manager": self._state_manager.get_status()
        }


# Singleton instance
_scanner_service: Optional[ScannerService] = None


def get_scanner_service() -> ScannerService:
    """Get the global scanner service instance."""
    global _scanner_service
    if _scanner_service is None:
        _scanner_service = ScannerService()
    return _scanner_service


async def start_scanner_service():
    """Start the background scanner service."""
    service = get_scanner_service()
    await service.start()


async def stop_scanner_service():
    """Stop the background scanner service."""
    service = get_scanner_service()
    await service.stop()
