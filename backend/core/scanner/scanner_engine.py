"""
Scanner Engine - Core orchestrator for running scans.
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
import logging

# Import from full strategies package to trigger all tier registrations
from strategies import StrategyRegistry, ScanResult
from services.derivatives_service import DerivativesService
from core.scanner.decision_engine import DecisionEngine

logger = logging.getLogger(__name__)

from services.live_price_enricher import enrich_scanner_results
from services.db_data_fetcher import get_db_data_fetcher
from services.dragonfly_client import get_cache, cache_get, CacheKeys
from utils.market_state import is_market_open, get_trading_date
from config import settings

# Load index constituents from external config (enables updates without code changes)
try:
    from utils.index_config import get_index_constituents, get_available_indices as get_indices_from_config
    _index_config_available = True
except ImportError:
    logger.warning("Index config module not available - using fallback")
    _index_config_available = False

def _get_index_constituents_fallback(index_name: str) -> List[str]:
    """Fallback if config module is not available."""
    FALLBACK = {
        "NIFTY 50": ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "ITC", "SBIN"],
        "NIFTY 100": ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "ITC", "SBIN"],
    }
    return FALLBACK.get(index_name, [])

# Dynamic index constituents loader
def get_index_symbols(index_name: str) -> List[str]:
    """Get symbols for an index from config or fallback."""
    if _index_config_available:
        return get_index_constituents(index_name)
    return _get_index_constituents_fallback(index_name)

# Timeframe mapping for Upstox
TIMEFRAME_MAP = {
    "3m": "3minute",
    "5m": "5minute",
    "15m": "15minute",
    "30m": "30minute",
    "60m": "60minute",
    "1d": "day"
}


class ScannerEngine:
    """Main scanner orchestrator."""
    
    def __init__(self, upstox_client=None, db_session=None):
        self.upstox_client = upstox_client
        self.db_session = db_session
        self._data_cache: Dict[str, pd.DataFrame] = {}
    
    async def run_scan(
        self,
        indices: List[str],
        timeframe: str,
        strategies: List[str],
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute scan using high-performance batch processing.
        """
        results: List[ScanResult] = []
        
        # 1. Get unique symbols for all selected indices
        symbols = self._get_symbols_for_indices(indices)
        total = len(symbols)
        logger.info(f"Starting batch scan: {total} symbols, {len(strategies)} strategies")

        # 2. Batch Compute Indicators (High Performance)
        from services.indicator_compute_service import get_indicator_service
        id_service = get_indicator_service()
        lookback = 30 if timeframe != "1d" else 100
        batch_df = await id_service.compute_batch(symbols, timeframe, lookback_days=lookback)
        
        if batch_df.empty:
            logger.warning("Batch computation returned no data")
            return []

        # 3. Evaluate Strategies against Batch Data
        # Group by symbol to pass slice to strategy
        for i, (symbol, symbol_df) in enumerate(batch_df.groupby('symbol')):
            symbol_index = self._get_symbol_index(symbol, indices)
            
            for strategy_name in strategies:
                strategy_cls = StrategyRegistry.get(strategy_name)
                if not strategy_cls: continue
                
                try:
                    strategy = strategy_cls()
                    # Strategies now receive pre-computed DataFrame slice
                    result = strategy.scan(symbol_df, symbol, symbol_index, timeframe)
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.error(f"Strategy {strategy_name} failed on {symbol}: {e}")
            
            if progress_callback:
                await progress_callback(i + 1, total)

        # 4. Sorting and Post-Enrichment
        results.sort(key=lambda x: x.confidence_score, reverse=True)
        
        # Build symbol_data map for derivatives enhancement
        symbol_data = {s: df for s, df in batch_df.groupby('symbol')}
        enhanced_results = await self._enhance_with_derivatives(results, symbol_data)
        
        return enhanced_results
    
    async def _enhance_with_derivatives(
        self, 
        results: List[ScanResult],
        symbol_data: Dict[str, pd.DataFrame]
    ) -> List[Dict[str, Any]]:
        """
        Enhance scan results with derivatives data and final signals.
        
        Args:
            results: List of technical scan results
            symbol_data: Cached OHLCV data per symbol
            
        Returns:
            List of enhanced result dictionaries
        """
        derivatives_service = DerivativesService()
        decision_engine = DecisionEngine()
        
        enhanced = []
        
        for result in results:
            # Calculate price change for OI classification
            price_change_pct = self._calculate_price_change(
                symbol_data.get(result.symbol)
            )
            
            # Get derivatives data
            derivatives_data = await derivatives_service.get_derivatives_data(
                result.symbol,
                price_change_pct
            )
            
            # Generate decision
            decision = decision_engine.generate_decision(result, derivatives_data)
            
            # Build enhanced result dict
            base_dict = result.to_dict()
            decision_dict = decision.to_dict()
            
            # Merge results
            enhanced_result = {**base_dict, **decision_dict}
            enhanced.append(enhanced_result)
        
        return enhanced
    
    def _calculate_price_change(self, df: Optional[pd.DataFrame]) -> float:
        """Calculate percentage price change from OHLCV data."""
        if df is None or len(df) < 2:
            return 0.0
        
        try:
            prev_close = df['close'].iloc[-2]
            curr_close = df['close'].iloc[-1]
            if prev_close == 0:
                return 0.0
            return ((curr_close - prev_close) / prev_close) * 100
        except Exception:
            return 0.0
    
    def _get_symbols_for_indices(self, indices: List[str]) -> List[str]:
        """Get unique symbols across all selected indices."""
        symbols = set()
        for index in indices:
            symbols.update(get_index_symbols(index))
        return list(symbols)
    
    def _get_symbol_index(self, symbol: str, indices: List[str]) -> str:
        """Determine which index a symbol belongs to."""
        for index in indices:
            index_symbols = get_index_symbols(index)
            if symbol in index_symbols:
                return index
        return indices[0] if indices else "Unknown"

    
    async def _fetch_data(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data for a symbol."""
        cache_key = f"{symbol}_{timeframe}"
        
        if cache_key in self._data_cache:
            return self._data_cache[cache_key]
        
        try:
            from utils.market_state import is_market_open
            
            # Try Upstox API first if market is open
            if self.upstox_client and is_market_open():
                df = await self._fetch_from_upstox(symbol, timeframe)
                if df is not None:
                    self._data_cache[cache_key] = df
                    return df
            
            # Fallback to database
            if self.db_session:
                df = await self._fetch_from_db(symbol)
                if df is not None:
                    self._data_cache[cache_key] = df
                    return df
            
            logger.warning(f"Historical data unavailable for {symbol}; excluded from scan.")
            return None
            
        except Exception as e:
            logger.error(f"Failed to fetch data for {symbol}: {e}")
            return None
    
    async def _fetch_from_upstox(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """Fetch from Upstox API."""
        try:
            interval = TIMEFRAME_MAP.get(timeframe, "day")
            # Call upstox client - implementation depends on your client
            # df = await self.upstox_client.get_historical_data(symbol, interval)
            return None  # Placeholder
        except Exception as e:
            logger.error(f"Upstox fetch failed for {symbol}: {e}")
            return None
    
    async def _fetch_from_db(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch from database."""
        try:
            # Implementation depends on your ORM
            return None  # Placeholder
        except Exception:
            return None

    
    async def get_momentum_scan(self) -> Dict[str, Any]:
        """Get momentum scan data with caching and fallback."""
        # Check if market is closed - return snapshot
        if not is_market_open():
            cache = get_cache()
            date_str = get_trading_date().strftime("%Y-%m-%d")
            snapshot = cache.get(f"snapshot:scanner_momentum:{date_str}")
            
            if snapshot and snapshot.get("data"):
                return {
                    "type": "bucket_update",
                    "timestamp": datetime.now().isoformat(),
                    "data": snapshot["data"],
                    "status": {
                        "source": "EOD_SNAPSHOT",
                        "is_healthy": True,
                        "stock_count": len(snapshot["data"]),
                        "trade_date": date_str,
                        "market_status": "CLOSED"
                    }
                }
        
        # Market is open - use live data
        # 1. Check Route Cache (handled by caller or internal cache?)
        # Let's check internal/route cache first to avoid re-calc
        cached = self._get_cached_scan("momentum")
        if cached:
             # Enrich with live prices
            try:
                if isinstance(cached, dict) and "data" in cached and cached["data"]:
                    access_token = settings.UPSTOX_ACCESS_TOKEN
                    cached["data"] = await enrich_scanner_results(cached["data"], access_token)
            except Exception as e:
                logger.error(f"momentum: Failed to enrich cached results: {e}")
            return cached

        # 2. Check HP Engine Cache (Fastest)
        try:
            from services.dragonfly_client import get_cache, CacheKeys
            cache = get_cache()
            snapshots = await cache.get_async(CacheKeys.all_snapshots())
            if snapshots and len(snapshots) > 0:
                data = []
                for s in snapshots[:500]:
                    data.append({
                        "symbol": s.get("symbol"),
                        "ltp": s.get("ltp", 0),
                        "prev_close": s.get("prev_close", 0),
                        "change_pct": s.get("change_pct", 0),
                        "momentum_score": max(5, min(95, 50 + int(s.get("change_pct", 0) * 10))),
                        "bucket": s.get("momentum_bucket", "NEUTRAL"),
                        "direction": "UP" if s.get("change_pct", 0) > 0 else "DOWN",
                        "source": "HP_ENGINE",
                        "confidence": "HIGH" if s.get("signal_strength", 0) > 50 else "MEDIUM",
                        "active_strategies": s.get("active_strategies", []),
                        "last_update": s.get("updated_at")
                    })
                
                enriched_data = await enrich_scanner_results(data[:100])
                if len(data) > 100:
                    enriched_data.extend(data[100:])
                
                response = {
                    "type": "bucket_update",
                    "timestamp": datetime.now().isoformat(),
                    "data": enriched_data,
                    "status": {
                        "source": "HP_ENGINE_ENRICHED",
                        "is_healthy": True,
                        "stock_count": len(enriched_data),
                        "poll_interval": 5
                    }
                }
                self._set_cached_scan("momentum", response)
                return response
        except Exception as e:
            logger.error(f"momentum: HP cache read failed: {e}")

        # 3. Last resort: DB Logic
        db_fetcher = get_db_data_fetcher()
        db_data = await asyncio.to_thread(db_fetcher.fetch_latest_data)
        
        data = []
        if db_data:
            count = 0
            for symbol, tick in db_data.items():
                if count > 200: break
                data.append({
                    "symbol": tick.symbol,
                    "ltp": tick.ltp,
                    "prev_close": tick.prev_close,
                    "change_pct": tick.change_pct,
                    "momentum_score": max(5, min(95, 50 + int(tick.change_pct * 10))),
                    "bucket": self._map_bucket_to_legacy(tick.change_pct),
                    "pct_bucket": tick.bucket,
                    "direction": tick.direction,
                    "correlation": 0.5,
                    "source": "DB",
                    "confidence": "LOW",
                    "last_update": tick.timestamp
                })
                count += 1
        
        enriched_data = await enrich_scanner_results(data[:50])
        
        response = {
            "type": "bucket_update",
            "timestamp": datetime.now().isoformat(),
            "data": enriched_data,
            "status": {
                "source": "DB_ENRICHED",
                "is_healthy": len(enriched_data) > 0,
                "last_tick": datetime.now().isoformat(),
                "stock_count": len(enriched_data),
                "poll_interval": 60
            }
        }
        
        self._set_cached_scan("momentum", response)
        return response

    async def get_breakout_scan(self) -> Dict[str, Any]:
        """Get breakout scan data."""
        if not is_market_open():
            cache = get_cache()
            date_str = get_trading_date().strftime("%Y-%m-%d")
            snapshot = cache.get(f"snapshot:scanner_breakout:{date_str}")
            if snapshot and snapshot.get("data"):
                return {
                    "type": "breakout_scan",
                    "timestamp": datetime.now().isoformat(),
                    "data": snapshot["data"],
                    "count": len(snapshot["data"]),
                    "status": {"source": "EOD_SNAPSHOT", "is_healthy": True, "trade_date": date_str, "market_status": "CLOSED"}
                }

        cached = self._get_cached_scan("breakout")
        if cached:
            try:
                if isinstance(cached, dict) and "data" in cached and cached["data"]:
                    access_token = settings.UPSTOX_ACCESS_TOKEN
                    cached["data"] = await enrich_scanner_results(cached["data"], access_token)
            except Exception as e:
                logger.error(f"breakout: Failed to enrich cached results: {e}")
            return cached

        # HP Scanner Check
        try:
            hp_breakout = cache_get(CacheKeys.breakout()) if hasattr(CacheKeys, 'breakout') else None
            if hp_breakout and len(hp_breakout) > 0:
                response = {
                    "type": "breakout_scan",
                    "timestamp": datetime.now().isoformat(),
                    "data": hp_breakout[:50],
                    "count": len(hp_breakout),
                    "status": {"source": "HP_SCANNER_CACHE", "is_healthy": True, "last_update": datetime.now().isoformat()}
                }
                self._set_cached_scan("breakout", response, ttl=300)
                return response
        except Exception as e:
            logger.debug(f"HP scanner cache miss for breakout: {e}")

        # DB Fallback
        db_fetcher = get_db_data_fetcher()
        db_data = await asyncio.to_thread(db_fetcher.fetch_latest_data)
        
        breakout_stocks = []
        if db_data:
            count = 0
            for symbol, tick in db_data.items():
                if count > 200: break
                if tick.change_pct >= 2.0:
                    breakout_stocks.append({
                        "symbol": tick.symbol,
                        "ltp": tick.ltp,
                        "prev_close": tick.prev_close,
                        "change_pct": tick.change_pct,
                        "breakout_score": min(100, int(tick.change_pct * 15 + 50)),
                        "pattern": "BULLISH_BREAKOUT" if tick.change_pct >= 4.0 else "MODERATE_BREAKOUT",
                        "strength": "STRONG" if tick.change_pct >= 4.0 else "MODERATE",
                        "source": "DB",
                        "last_update": tick.timestamp
                    })
                    count += 1
        
        breakout_stocks.sort(key=lambda x: x["change_pct"], reverse=True)
        enriched_data = await enrich_scanner_results(breakout_stocks[:50])
        
        response = {
            "type": "breakout_scan",
            "timestamp": datetime.now().isoformat(),
            "data": enriched_data,
            "count": len(enriched_data),
            "status": {"source": "DB_ENRICHED", "is_healthy": len(enriched_data) > 0, "last_update": datetime.now().isoformat()}
        }
        self._set_cached_scan("breakout", response)
        return response

    async def get_reversal_scan(self) -> Dict[str, Any]:
        """Get reversal scan data."""
        if not is_market_open():
            cache = get_cache()
            date_str = get_trading_date().strftime("%Y-%m-%d")
            snapshot = cache.get(f"snapshot:scanner_reversal:{date_str}")
            if snapshot and snapshot.get("data"):
                 return {
                    "type": "reversal_scan",
                    "timestamp": datetime.now().isoformat(),
                    "data": snapshot["data"],
                    "count": len(snapshot["data"]),
                    "status": {"source": "EOD_SNAPSHOT", "is_healthy": True, "trade_date": date_str, "market_status": "CLOSED"}
                }

        cached = self._get_cached_scan("reversal")
        if cached:
            try:
                if isinstance(cached, dict) and "data" in cached and cached["data"]:
                    access_token = settings.UPSTOX_ACCESS_TOKEN
                    cached["data"] = await enrich_scanner_results(cached["data"], access_token)
            except Exception as e:
                logger.error(f"reversal: Failed to enrich cached results: {e}")
            return cached

        reversal_candidates = []
        try:
            db_fetcher = get_db_data_fetcher()
            db_data = await asyncio.wait_for(
                asyncio.to_thread(db_fetcher.fetch_latest_data),
                timeout=30.0
            )
            
            if db_data:
                count = 0
                for symbol, tick in db_data.items():
                    if count > 200: break
                    if (tick.change_pct <= -1.0 and tick.change_pct >= -4.0):
                        reversal_candidates.append({
                            "symbol": tick.symbol,
                            "ltp": tick.ltp,
                            "prev_close": tick.prev_close,
                            "change_pct": tick.change_pct,
                            "reversal_score": int(abs(tick.change_pct) * 20),
                            "pattern": "BULLISH_REVERSAL",
                            "type": "OVERSOLD_BOUNCE",
                            "strength": "STRONG" if tick.change_pct <= -3.0 else "MODERATE",
                            "source": "DB",
                            "last_update": tick.timestamp
                        })
                        count += 1
                    elif (tick.change_pct >= 3.0 and tick.change_pct <= 6.0):
                        reversal_candidates.append({
                            "symbol": tick.symbol,
                            "ltp": tick.ltp,
                            "prev_close": tick.prev_close,
                            "change_pct": tick.change_pct,
                            "reversal_score": int(tick.change_pct * 15),
                            "pattern": "BEARISH_REVERSAL",
                            "type": "OVERBOUGHT_CORRECTION",
                            "strength": "STRONG" if tick.change_pct >= 5.0 else "MODERATE",
                            "source": "DB",
                            "last_update": tick.timestamp
                        })
                        count += 1
        except Exception as e:
            logger.error(f"Reversal scanner error: {e}")
        
        reversal_candidates.sort(key=lambda x: x["reversal_score"], reverse=True)
        enriched_data = await enrich_scanner_results(reversal_candidates[:50])
        
        response = {
            "type": "reversal_scan",
            "timestamp": datetime.now().isoformat(),
            "data": enriched_data,
            "count": len(enriched_data),
            "status": {"source": "DB_ENRICHED", "is_healthy": len(enriched_data) > 0, "last_update": datetime.now().isoformat()}
        }
        self._set_cached_scan("reversal", response)
        return response

    async def get_trendfinder_scan(self) -> Dict[str, Any]:
        """Get TrendFinder scan data."""
        cached = self._get_cached_scan("trendfinder")
        if cached:
            try:
                if isinstance(cached, dict) and "data" in cached and cached["data"]:
                    access_token = settings.UPSTOX_ACCESS_TOKEN
                    cached["data"] = await enrich_scanner_results(cached["data"], access_token)
            except Exception as e:
                logger.error(f"trendfinder: Failed to enrich cached results: {e}")
            return cached

        db_fetcher = get_db_data_fetcher()
        db_data = await asyncio.to_thread(db_fetcher.fetch_latest_data)
        
        trending_stocks = []
        if db_data:
            count = 0
            for symbol, tick in db_data.items():
                if count > 200: break
                abs_change = abs(tick.change_pct)
                if abs_change >= 0.5:
                    ai_confidence = min(95, int(abs_change * 25 + 30))
                    trending_stocks.append({
                        "symbol": tick.symbol,
                        "ltp": tick.ltp,
                        "prev_close": tick.prev_close,
                        "change_pct": tick.change_pct,
                        "trend_direction": "BULLISH" if tick.change_pct > 0 else "BEARISH",
                        "trend_strength": "STRONG" if abs_change >= 3.0 else "MODERATE" if abs_change >= 1.5 else "WEAK",
                        "ai_confidence": ai_confidence,
                        "momentum_score": max(5, min(95, 50 + int(tick.change_pct * 10))),
                        "signal": "BUY" if tick.change_pct > 1.0 else "SELL" if tick.change_pct < -1.0 else "HOLD",
                        "source": "DB",
                        "last_update": tick.timestamp
                    })
                    count += 1
        
        trending_stocks.sort(key=lambda x: x["ai_confidence"], reverse=True)
        enriched_data = await enrich_scanner_results(trending_stocks[:50])
        
        response = {
            "type": "trendfinder_scan",
            "timestamp": datetime.now().isoformat(),
            "data": enriched_data,
            "count": len(enriched_data),
            "status": {
                "source": "AI_DB_ENRICHED",
                "is_healthy": len(enriched_data) > 0,
                "last_update": datetime.now().isoformat(),
                "ai_model": "TrendFinder v1.0"
            }
        }
        self._set_cached_scan("trendfinder", response)
        return response

    def _get_cached_scan(self, key: str) -> Optional[Dict]:
        """Internal helper to get cached scan result."""
        cache = get_cache()
        if not cache.is_available():
            return None
        try:
            return cache.get(f"qai:scanner:route:{key}")
        except Exception:
            return None

    def _set_cached_scan(self, key: str, data: Dict, ttl: int = 300):
        """Internal helper to set cached scan result."""
        cache = get_cache()
        if not cache.is_available():
            return
        try:
            cache.set(f"qai:scanner:route:{key}", data, ttl=ttl)
        except Exception:
            pass

    def _map_bucket_to_legacy(self, change_pct: float) -> str:
        """Map percent change to legacy bucket names."""
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

    def get_available_strategies(self) -> List[Dict[str, Any]]:
        """Get list of all available strategies."""
        return StrategyRegistry.list_strategies()
    
    def get_available_indices(self) -> List[Dict[str, Any]]:
        """Get list of available indices."""
        return [
            {"name": "NIFTY 50", "stocks": 50},
            {"name": "NIFTY 100", "stocks": 100},
            {"name": "NIFTY 200", "stocks": 200},
            {"name": "NIFTY 500", "stocks": 500}
        ]
    
    def get_available_timeframes(self) -> List[Dict[str, str]]:
        """Get list of available timeframes."""
        return [
            {"value": "3m", "label": "3 Minutes"},
            {"value": "5m", "label": "5 Minutes"},
            {"value": "15m", "label": "15 Minutes"},
            {"value": "30m", "label": "30 Minutes"},
            {"value": "60m", "label": "60 Minutes"},
            {"value": "1d", "label": "1 Day"}
        ]

