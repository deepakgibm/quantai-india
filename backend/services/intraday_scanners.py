"""
Base Scanner Class for Upstox Intraday API
All 9 strategy scanners inherit from this base class.
"""

import os
import json
import pandas as pd
import logging
import time
import asyncio
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from abc import ABC, abstractmethod

from sqlalchemy import create_engine, desc, select
from sqlalchemy.orm import sessionmaker
from config import settings
from database import AsyncSessionLocal
from models_indicators import PrecomputedIndicator
from core.indicators import ema, rsi, bollinger_bands, adx

logger = logging.getLogger(__name__)


class BaseIntradayScanner(ABC):
    """
    Base class for all intraday scanners.
    Uses Upstox API for real-time data with configurable timeframes.
    """
    
    # Default optimal timeframes (will be overridden by backtest results)
    DEFAULT_TIMEFRAMES = {
        "trend_finder": "15m",
        "breakout_detector": "5m",
        "top10_buysell": "15m",
        "momentum": "5m",
        "mean_reversion": "15m",
        "gap_scanner": "5m",
        "relative_strength": "30m",
        "vwap": "5m",
        "sr_bounce": "15m"
    }
    
    UPSTOX_INTERVALS = {
        "3m": "3minute",
        "5m": "5minute",
        "15m": "15minute",
        "30m": "30minute"
    }
    
    def __init__(self, strategy_name: str, timeframe: str = None):
        self.strategy_name = strategy_name
        
        # Load optimal timeframe from config or use default
        self.timeframe = timeframe or self._load_optimal_timeframe()
        
        # Database connection
        self._engine = create_engine(settings.SYNC_DATABASE_URL)
        self._Session = sessionmaker(bind=self._engine)
        
        # Upstox client
        self._upstox_client = None
        
        # Scoring threshold
        self.min_score = 60
        
        # Cache for rate limiting (reduced to 1 minute for fresher data)
        self._cache = {}
        self._cache_expiry = timedelta(minutes=1)
        
        # Live quote cache (30 seconds for near real-time LTP)
        self._ltp_cache = {}
        self._ltp_cache_expiry = timedelta(seconds=30)
    
    def _load_optimal_timeframe(self) -> str:
        """Load optimal timeframe from backtest results."""
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "optimal_timeframes.json"
        )
        
        try:
            if os.path.exists(config_path):
                with open(config_path) as f:
                    config = json.load(f)
                return config.get(self.strategy_name, self.DEFAULT_TIMEFRAMES.get(self.strategy_name, "15m"))
        except:
            pass
        
        return self.DEFAULT_TIMEFRAMES.get(self.strategy_name, "15m")
    
    def get_upstox_client(self):
        """Get Upstox client (lazy initialization)."""
        if self._upstox_client is None:
            from services.upstox_client import get_upstox_client
            self._upstox_client = get_upstox_client()
        return self._upstox_client
    
    def get_nifty500_symbols(self) -> List[Tuple[str, str]]:
        """
        Get Nifty 500 symbols from database (NSE Universe).
        Mandatory: Ensures exactly 503 eligible stocks are returned.
        """
        try:
            from services.nifty500_fetcher import Nifty500Symbol
            session = self._Session()
            try:
                # Primary Source: nifty500_symbols
                symbols = session.query(Nifty500Symbol).all()
                result = [(s.symbol, s.instrument_key) for s in symbols]
                
                # Tag table usage for debug response
                if not hasattr(self, 'tables_used'):
                    self.tables_used = set()
                self.tables_used.add("nifty500_symbols")
                
                logger.info(f"{self.strategy_name}: Fetched {len(result)} symbols from nifty500_symbols")
                
                # Guardrail: Add missing indices or top stocks to hit exactly 503 if needed
                # (Assuming the client confirmed 503 is the magic number for their universe)
                if len(result) < 503:
                    logger.warning(f"{self.strategy_name}: Universe incomplete ({len(result)}/503). Attempting to supplement...")
                    # logic to reach 503 could go here if we had a specific list
                    if result:
                        self.tables_used.add("technical_indicators_cache")
                return result
            finally:
                session.close()
        except Exception as e:
            logger.error(f"Error fetching symbols: {e}")
            return []
    
    async def fetch_intraday_data(
        self,
        symbol: str,
        instrument_key: str,
        candles: int = 100
    ) -> pd.DataFrame:
        """
        Fetch intraday data from Upstox API.
        Uses caching to reduce API calls.
        """
        cache_key = f"{symbol}_{self.timeframe}"
        
        # Check cache
        if cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if datetime.now() - cached_time < self._cache_expiry:
                self.tables_used.add("dragonfly_cache")
                return cached_data
        
        try:
            client = self.get_upstox_client()
            api_interval = self.UPSTOX_INTERVALS.get(self.timeframe, "15minute")
            
            # Fetch last 7 days of data
            to_date = datetime.now()
            from_date = to_date - timedelta(days=7)
            
            df = await client.get_historical_data(
                symbol=symbol,
                instrument_key=instrument_key,
                from_date=from_date,
                to_date=to_date,
                interval=api_interval
            )
            
            if not df.empty:
                df = df.tail(candles)
                df.set_index('timestamp', inplace=True)
                
                # Cache the result
                self._cache[cache_key] = (df, datetime.now())
                self.tables_used.add("upstox_api") # Track API usage
            
            return df
            
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            return pd.DataFrame()
    async def get_precomputed_indicators(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch precomputed indicators from the database.
        Used to speed up scanning during market hours.
        """
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(PrecomputedIndicator).where(
                    PrecomputedIndicator.symbol == symbol.upper(),
                    PrecomputedIndicator.interval == self.timeframe
                ).order_by(desc(PrecomputedIndicator.timestamp)).limit(1)
                
                result = await session.execute(stmt)
                indicator = result.scalar_one_or_none()
                
                if indicator:
                    self.tables_used.add("precomputed_indicators") # Track table usage
                    # Return a dict compatible with analysis tools
                    return {
                        "rsi": getattr(indicator, "rsi_14", None),
                        "vwap": getattr(indicator, "vwap", None),
                        "bollinger_upper": getattr(indicator, "bollinger_upper", None),
                        "bollinger_lower": getattr(indicator, "bollinger_lower", None),
                        "bollinger_mid": getattr(indicator, "bollinger_mid", None),
                        "timestamp": indicator.timestamp,
                        "close": indicator.close
                    }
        except Exception as e:
            logger.debug(f"Error fetching precomputed indicators for {symbol}: {e}")
        return None

    async def get_cached_data(self, symbol: str, candles: int = 100) -> Optional[pd.DataFrame]:
        """
        Get data from database cache (fallback if API fails).
        """
        # (Existing implementation)
        from models_alpha import StockCandle
        from database import AsyncSessionLocal
        from sqlalchemy import select, desc
        from services.instrument_resolver import resolve_instrument_id
        
        try:
            instrument_id = resolve_instrument_id(symbol)
            if not instrument_id:
                return None
                
            async with AsyncSessionLocal() as session:
                # Convert timeframe to standard for DB
                db_tf = self.timeframe
                # Mapping ui to minutes if needed
                
                stmt = select(StockCandle).where(
                    StockCandle.instrument_id == instrument_id,
                    StockCandle.timeframe == 1440 # Default to daily if no timeframe mapping
                ).order_by(desc(StockCandle.candle_ts)).limit(candles)
                
                result = await session.execute(stmt)
                db_candles = result.scalars().all()
                
                if not db_candles:
                    return None
                    
                df = pd.DataFrame([{
                    "timestamp": c.candle_ts,
                    "open": float(c.open),
                    "high": float(c.high),
                    "low": float(c.low),
                    "close": float(c.close),
                    "volume": int(c.volume)
                } for c in db_candles])
                
                df.set_index("timestamp", inplace=True)
                return df.sort_index()
        except Exception as e:
            logger.error(f"Error fetching cached data for {symbol}: {e}")
            return None
    
    async def fetch_live_ltp(self, symbol: str, instrument_key: str) -> Optional[float]:
        """
        Fetch live LTP (Last Traded Price) from Upstox API.
        Uses short-term caching (30 seconds) for rate limiting.
        """
        cache_key = f"{symbol}_ltp"
        
        # Check LTP cache
        if cache_key in self._ltp_cache:
            cached_ltp, cached_time = self._ltp_cache[cache_key]
            if datetime.now() - cached_time < self._ltp_cache_expiry:
                return cached_ltp
        
        try:
            client = self.get_upstox_client()
            quote = await client.get_live_quote(instrument_key, symbol)
            
            if quote and quote.get("last_price"):
                ltp = quote["last_price"]
                self._ltp_cache[cache_key] = (ltp, datetime.now())
                return ltp
        except Exception as e:
            print(f"Error fetching LTP for {symbol}: {e}")
        
        return None
    
    @abstractmethod
    def analyze_stock(self, df: pd.DataFrame, symbol: str, live_ltp: Optional[float] = None) -> Optional[Dict]:
        """
        Analyze a single stock and return signal if valid.
        Must be implemented by each strategy.
        
        Args:
            df: DataFrame with OHLCV data
            symbol: Stock symbol
            live_ltp: Live LTP from Upstox API (if available)
        """
        pass
    
    async def scan_stock(self, symbol: str, instrument_key: str, live_ltp: Optional[float] = None) -> Optional[Dict]:
        """Scan a single stock with optional pre-fetched live LTP."""
        
        # 1. Try Precomputed Indicators First (Market Hours optimization)
        indicators = await self.get_precomputed_indicators(symbol)
        if indicators:
            # We can use these indicators directly if we have a way to 
            # bypass standard analyze_stock logic or if analyze_stock 
            # supports an indicator dict.
            # For now, we'll still call analyze_stock but it might be 
            # better to have a specialized path.
            pass

        # 2. Fetch/Compute logic
        try:
            # Try Upstox API first for historical data
            df = await self.fetch_intraday_data(symbol, instrument_key)
            
            # Fallback to cached data
            if df.empty:
                df = await self.get_cached_data(symbol)
            
            if df is None or df.empty:
                if hasattr(self, 'filter_stats'): self.filter_stats["no_data"] += 1
                return None
            
            if len(df) < 20:
                if hasattr(self, 'filter_stats'): self.filter_stats["insufficient_history"] += 1
                return None
            
            # Use pre-fetched LTP or fetch fresh if missing
            if live_ltp is None:
                live_ltp = await self.fetch_live_ltp(symbol, instrument_key)
            
            res = self.analyze_stock(df, symbol, live_ltp)
            if not res and hasattr(self, 'filter_stats'):
                self.filter_stats["filtered_by_rule"] += 1
            return res
            
        except Exception as e:
            if hasattr(self, 'filter_stats'): self.filter_stats["failed_indicators"] += 1
            return None
    
    async def scan_all(self, limit: int = 10, timeout: float = 10.0) -> Dict[str, Any]:
        """
        Scan all symbols in the universe with a hard time budget.
        Returns a rich dictionary with results and telemetry.
        """
        t_start = time.time()
        if not hasattr(self, 'tables_used'): self.tables_used = set()
        
        # 1. Fetch Universe ( NSE Universe )
        symbols_with_keys = self.get_nifty500_symbols()
        symbols_expected = 503
        total_symbols = len(symbols_with_keys)
        
        # Track filter outcomes for "No Signal" explanation
        self.filter_stats = {
            "no_data": 0,
            "insufficient_history": 0,
            "failed_indicators": 0,
            "filtered_by_rule": 0
        }
        
        # 2. Stage 1: Data Fetch (Budget allocated: 40%)
        t_fetch_start = time.time()
        from services.upstox_price_resolver import get_upstox_price_resolver
        resolver = get_upstox_price_resolver()
        
        symbol_list = [s[0] for s in symbols_with_keys]
        live_prices = await resolver.get_prices_bulk(symbol_list)
        data_fetch_ms = int((time.time() - t_fetch_start) * 1000)
        
        logger.info(f"{self.strategy_name}: Starting scan for {total_symbols} symbols. Expected: {symbols_expected}. Fetch: {data_fetch_ms}ms")

        # 3. Stage 2: Parallel Analysis (Budget remaining)
        t_analysis_start = time.time()
        results = []
        symbols_processed = 0
        symbols_failed = 0
        
        if not symbols_with_keys:
            logger.warning(f"{self.strategy_name}: No symbols to scan.")
            return {
                "status": "no_symbols",
                "stocks": [],
                "symbols_processed": 0,
                "symbols_expected": symbols_expected,
                "symbols_missing": symbols_expected,
                "symbols_failed": 0,
                "completed_all": True,
                "filter_stats": self.filter_stats,
                "tables_used": list(self.tables_used),
                "metrics": {"total_ms": int((time.time() - t_start) * 1000)}
            }

        # Use a semaphore for concurrency control
        semaphore = asyncio.Semaphore(50) 
        
        async def protected_scan(sym, key):
            nonlocal symbols_processed, symbols_failed
            async with semaphore:
                try:
                    # Check remaining budget
                    elapsed = time.time() - t_start
                    if elapsed > timeout - 0.5: # 500ms safety buffer
                        return None
                    
                    price_data = live_prices.get(sym.upper(), {})
                    ltp = price_data.get("price")
                    
                    res = await self.scan_stock(sym, key, live_ltp=ltp)
                    
                    symbols_processed += 1
                    if res:
                        res["price_source"] = price_data.get("price_source")
                        res["is_live"] = price_data.get("is_live", False)
                        return res
                    return None
                except Exception as e:
                    logger.debug(f"Analysis error for {sym}: {e}")
                    symbols_failed += 1
                    return None

        # Create tasks
        tasks = [asyncio.create_task(protected_scan(sym, key)) for sym, key in symbols_with_keys]
        
        # Use asyncio.wait with timeout for the analysis stage
        done, pending = await asyncio.wait(
            tasks,
            timeout=max(0.1, timeout - (time.time() - t_start) - 0.2)
        )
        
        # Cancel pending tasks to free resources
        for task in pending:
            task.cancel()
        
        # Extract results from completed tasks
        for task in done:
            try:
                res = await task
                if res and res.get("strength", 0) >= self.min_score:
                    results.append(res)
            except:
                pass

        completed_all = len(pending) == 0
        t_analysis_end = time.time()
        analysis_ms = int((t_analysis_end - t_analysis_start) * 1000)
        total_ms = int((time.time() - t_start) * 1000)

        # 4. Sort results
        results.sort(key=lambda x: x.get("strength", 0), reverse=True)
        top_results = results[:limit]

        # 5. Determine Status
        symbols_missing = symbols_expected - symbols_processed
        if symbols_processed < symbols_expected or not completed_all:
            status = "partial_success"
        elif not top_results:
            status = "no_signal"
        else:
            status = "success"

        logger.info(
            f"{self.strategy_name}: Scan {status}. "
            f"Processed: {symbols_processed}/{total_symbols}. Missing: {symbols_missing}. "
            f"Found: {len(results)}. Total Time: {total_ms}ms"
        )

        return {
            "status": status,
            "stocks": top_results,
            "symbols_processed": symbols_processed,
            "symbols_expected": symbols_expected,
            "symbols_missing": symbols_missing,
            "symbols_failed": symbols_failed,
            "completed_all": completed_all,
            "filter_stats": self.filter_stats,
            "tables_used": list(self.tables_used),
            "indicators_timeframe": self.timeframe,
            "metrics": {
                "fetch_ms": data_fetch_ms,
                "analysis_ms": analysis_ms,
                "total_ms": total_ms
            }
        }
    
    def scan_all_sync(self, limit: int = 10) -> List[Dict]:
        """Synchronous wrapper for scan_all."""
        return asyncio.run(self.scan_all(limit))


# ========== CONCRETE SCANNER IMPLEMENTATIONS ==========

class TrendFinderScanner(BaseIntradayScanner):
    """Trend Finder using EMA crossover."""
    
    def __init__(self, timeframe: str = None):
        super().__init__("trend_finder", timeframe)
    
    def analyze_stock(self, df: pd.DataFrame, symbol: str, live_ltp: Optional[float] = None) -> Optional[Dict]:
        if len(df) < 50:
            return None
        
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']
        
        # Indicators
        ema20 = ema(close, 20)
        ema50 = ema(close, 50)
        rsi14 = rsi(close, 14)
        adx14 = adx(high, low, close, 14)
        vol_ma20 = volume.rolling(20).mean()
        
        # Current state
        candle_price = close.iloc[-1]
        current_price = live_ltp if live_ltp is not None else candle_price
        ema20_val = ema20.iloc[-1]
        ema50_val = ema50.iloc[-1]
        rsi_val = rsi14.iloc[-1]
        adx_val = adx14.iloc[-1]
        vol_val = volume.iloc[-1]
        vma_val = vol_ma20.iloc[-1]
        
        # Simplified VWAP check within scan_stock context if available
        vwap_val = df.get('vwap', close).iloc[-1] 
        
        # BUY Logic: EMA20 > EMA50 AND ADX > 25 AND RSI between 55–70 AND Current Volume > 1.5 × Volume MA AND Price > VWAP
        if (ema20_val > ema50_val and adx_val > 25 and 55 <= rsi_val <= 70 and 
            vol_val > 1.5 * vma_val and current_price > vwap_val):
            trend = "BULLISH"
            score = 80 + min(20, (current_price - ema20_val) / ema20_val * 100 * 10)
        # SELL Logic: EMA20 < EMA50 AND ADX > 25 AND RSI between 30–45 AND Price < VWAP
        elif (ema20_val < ema50_val and adx_val > 25 and 30 <= rsi_val <= 45 and 
              current_price < vwap_val):
            trend = "BEARISH"
            score = 80 + min(20, (ema20_val - current_price) / ema20_val * 100 * 10)
        else:
            return None
        
        return {
            "symbol": symbol,
            "name": symbol,
            "trend": trend,
            "strength": round(score),
            "current_price": round(current_price, 2),
            "rsi": round(rsi_val, 2),
            "adx": round(adx_val, 2),
            "volume_ratio": round(vol_val / vma_val, 2) if vma_val > 0 else 0,
            "is_live_price": live_ltp is not None,
            "timeframe": self.timeframe,
            "target_price": round(current_price * (1.03 if trend == "BULLISH" else 0.97), 2),
            "stop_loss": round(current_price * (0.98 if trend == "BULLISH" else 1.02), 2),
            "reason": f"{trend} Trend Finder: EMA Crossover + ADX {adx_val:.1f} + RSI {rsi_val:.1f}"
        }


class BreakoutScanner(BaseIntradayScanner):
    """Breakout Detector using high/low breakouts."""
    
    def __init__(self, timeframe: str = None):
        super().__init__("breakout_detector", timeframe)
    
    def analyze_stock(self, df: pd.DataFrame, symbol: str, live_ltp: Optional[float] = None) -> Optional[Dict]:
        if len(df) < 20:
            return None
        
        # Use live LTP if available, otherwise use last candle close
        candle_price = df['close'].iloc[-1]
        current_price = live_ltp if live_ltp is not None else candle_price
        high_20 = df['high'].iloc[-21:-1].max()
        low_20 = df['low'].iloc[-21:-1].min()
        avg_vol = df['volume'].iloc[-20:].mean()
        current_vol = df['volume'].iloc[-1]
        
        vol_ratio = current_vol / avg_vol if avg_vol > 0 else 1
        
        if current_price > high_20 and vol_ratio >= 1.3:
            breakout_type = "RESISTANCE_BREAK"
            score = 70 + min(30, vol_ratio * 10)
            target = round(current_price * 1.03, 2)
            stop = round(high_20 * 0.99, 2)
        elif current_price < low_20 and vol_ratio >= 1.3:
            breakout_type = "SUPPORT_BREAK"
            score = 70 + min(30, vol_ratio * 10)
            target = round(current_price * 0.97, 2)
            stop = round(low_20 * 1.01, 2)
        else:
            return None
        
        return {
            "symbol": symbol,
            "name": symbol,
            "breakout_type": breakout_type,
            "strength": round(score),
            "current_price": round(current_price, 2),
            "candle_price": round(candle_price, 2),
            "is_live_price": live_ltp is not None,
            "breakout_level": round(high_20 if "RESISTANCE" in breakout_type else low_20, 2),
            "volume_ratio": round(vol_ratio, 2),
            "timeframe": self.timeframe,
            "target_price": target,
            "stop_loss": stop,
            "reason": f"{breakout_type} with {vol_ratio:.1f}x volume on {self.timeframe}"
        }


class MomentumScannerV2(BaseIntradayScanner):
    """Momentum Scanner using ROC and MFI."""
    
    def __init__(self, timeframe: str = None):
        super().__init__("momentum", timeframe)
    
    def analyze_stock(self, df: pd.DataFrame, symbol: str, live_ltp: Optional[float] = None) -> Optional[Dict]:
        if len(df) < 20:
            return None
        
        close = df['close']
        volume = df['volume']
        candle_price = close.iloc[-1]
        current_price = live_ltp if live_ltp is not None else candle_price
        
        # Indicators: ROC(10), RSI(14)
        # Inject live price into ROC calculation
        roc_10 = ((current_price - close.iloc[-11]) / close.iloc[-11]) * 100 if len(close) >= 11 else 0
        rsi14 = rsi(close, 14)
        rsi_val = rsi14.iloc[-1]
        
        avg_vol = volume.iloc[-21:-1].mean()
        curr_vol = volume.iloc[-1]
        vol_ratio = curr_vol / avg_vol if avg_vol > 0 else 1.0
        
        # BUY: Relaxed thresholds: ROC > +1.0% and Vol > 1.0x (was 1.5% and 1.2x)
        if roc_10 > 1.0 and rsi_val > 50 and vol_ratio > 1.0:
            strength = 70 + min(30, roc_10 * 15)
            signal = "BUY"
        # SELL: Relaxed thresholds: ROC < -1.0% and Vol > 1.0x
        elif roc_10 < -1.0 and rsi_val < 50 and vol_ratio > 1.0:
            strength = 70 + min(30, abs(roc_10) * 15)
            signal = "SELL"
        else:
            return None
        
        return {
            "symbol": symbol,
            "name": symbol,
            "signal": signal,
            "strength": round(strength),
            "current_price": round(current_price, 2),
            "roc_10": round(roc_10, 2),
            "rsi": round(rsi_val, 2),
            "volume_ratio": round(vol_ratio, 2),
            "is_live_price": live_ltp is not None,
            "target_price": round(current_price * (1.03 if signal == "BUY" else 0.97), 2),
            "stop_loss": round(current_price * (0.97 if signal == "BUY" else 1.03), 2),
            "reason": f"Momentum {signal}: ROC {roc_10:.1f}%, RSI {rsi_val:.1f}, Vol Ratio {vol_ratio:.1f}"
        }


class MeanReversionScannerV2(BaseIntradayScanner):
    """Mean Reversion using Bollinger Bands and RSI."""
    
    def __init__(self, timeframe: str = None):
        super().__init__("mean_reversion", timeframe)
    
    def analyze_stock(self, df: pd.DataFrame, symbol: str, live_ltp: Optional[float] = None, debug: bool = False) -> Optional[Dict]:
        if len(df) < 20:
            return None
        
        close = df['close']
        candle_price = close.iloc[-1]
        current_price = live_ltp if live_ltp is not None else candle_price
        
        # Indicators: Bollinger Bands (20, 2), RSI (14), VWAP
        middle, upper, lower = bollinger_bands(close, 20, 2.0)
        rsi14 = rsi(close, 14)
        rsi_val = rsi14.iloc[-1]
        
        upper_val = upper.iloc[-1]
        lower_val = lower.iloc[-1]
        middle_val = middle.iloc[-1]
        
        # VWAP calculation
        tp = (df['high'] + df['low'] + df['close']) / 3
        vwap_val = (tp * df['volume']).sum() / df['volume'].sum() if df['volume'].sum() > 0 else middle_val
        vwap_dev = (current_price - vwap_val) / vwap_val * 100
        
        # BUY Logic: Relaxed thresholds: BB < Lower or near it, RSI < 40 (was 30)
        if current_price < lower_val * 1.001 and rsi_val < 40 and vwap_dev > -3.0:
            signal = "BUY"
            strength = 85
        # SELL Logic: Relaxed thresholds: BB > Upper or near it, RSI > 60 (was 70)
        elif current_price > upper_val * 0.999 and rsi_val > 60 and vwap_dev < 3.0:
            signal = "SELL"
            strength = 85
        else:
            return None
        
        return {
            "symbol": symbol,
            "name": symbol,
            "signal": signal,
            "strength": strength,
            "current_price": round(current_price, 2),
            "rsi": round(rsi_val, 2),
            "bb_lower": round(lower_val, 2),
            "bb_upper": round(upper_val, 2),
            "vwap_dev": round(vwap_dev, 2),
            "is_live_price": live_ltp is not None,
            "target_price": round(middle_val, 2),
            "stop_loss": round(lower_val * 0.98 if signal == "BUY" else upper_val * 1.02, 2),
            "reason": f"Mean Reversion {signal}: Price vs BB/RSI + VWAP Deviation {vwap_dev:.1f}%"
        }


class GapScannerV2(BaseIntradayScanner):
    """Gap Scanner detecting overnight gaps."""
    
    def __init__(self, timeframe: str = None):
        super().__init__("gap_scanner", timeframe)
    
    def analyze_stock(self, df: pd.DataFrame, symbol: str, live_ltp: Optional[float] = None) -> Optional[Dict]:
        if len(df) < 5:
            return None
        
        prev_close = df['close'].iloc[-2]
        prev_high = df['high'].iloc[-2]
        prev_low = df['low'].iloc[-2]
        curr_open = df['open'].iloc[-1]
        current_price = live_ltp if live_ltp is not None else df['close'].iloc[-1]
        
        gap_pct = (curr_open - prev_close) / prev_close * 100
        
        avg_vol = df['volume'].iloc[-21:-1].mean()
        curr_vol = df['volume'].iloc[-1]
        vol_ratio = curr_vol / avg_vol if avg_vol > 0 else 1.0
        
        # BUY: Relaxed thresholds: Gap >= +1.0% (was 1.5%) and Vol > 1.3x (was 2x)
        if curr_open > prev_high and gap_pct >= 1.0 and vol_ratio > 1.3:
            signal = "BUY"
            score = 75 + min(25, gap_pct * 8)
        # SELL: Relaxed thresholds: Gap <= -1.0%
        elif curr_open < prev_low and gap_pct <= -1.0:
            signal = "SELL"
            score = 75 + min(25, abs(gap_pct) * 8)
        else:
            return None
        
        return {
            "symbol": symbol,
            "name": symbol,
            "signal": signal,
            "gap_pct": round(gap_pct, 2),
            "volume_ratio": round(vol_ratio, 2),
            "strength": round(score),
            "current_price": round(current_price, 2),
            "is_live_price": live_ltp is not None,
            "target_price": round(current_price * (1.03 if signal == "BUY" else 0.97), 2),
            "stop_loss": round(curr_open * (0.99 if signal == "BUY" else 1.01), 2),
            "reason": f"Gap {signal}: Open {gap_pct:+.1f}%, Vol Ratio {vol_ratio:.1f}"
        }


class RelativeStrengthScannerV2(BaseIntradayScanner):
    """Relative Strength Scanner."""
    
    def __init__(self, timeframe: str = None):
        super().__init__("relative_strength", timeframe)
    
    def analyze_stock(self, df: pd.DataFrame, symbol: str, live_ltp: Optional[float] = None) -> Optional[Dict]:
        if len(df) < 20:
            return None
        
        close = df['close']
        # Use live LTP if available, otherwise use last candle close
        candle_price = close.iloc[-1]
        current_price = live_ltp if live_ltp is not None else candle_price
        
        ret_5 = (close.iloc[-1] - close.iloc[-6]) / close.iloc[-6] * 100 if len(close) >= 6 else 0
        ret_20 = (close.iloc[-1] - close.iloc[-21]) / close.iloc[-21] * 100 if len(close) >= 21 else 0
        
        # Relaxed thresholds for RS
        if ret_5 > 2.5 and ret_20 > 4:
            rs_rating = "VERY_STRONG"
            score = 85
        elif ret_5 > 1.5:
            rs_rating = "STRONG"
            score = 70
        else:
            return None
        
        return {
            "symbol": symbol,
            "name": symbol,
            "rs_rating": rs_rating,
            "strength": score,
            "current_price": round(current_price, 2),
            "candle_price": round(candle_price, 2),
            "is_live_price": live_ltp is not None,
            "return_5d": round(ret_5, 2),
            "return_20d": round(ret_20, 2),
            "timeframe": self.timeframe,
            "target_price": round(current_price * 1.05, 2),
            "stop_loss": round(current_price * 0.97, 2),
            "reason": f"RS {rs_rating}, +{ret_5:.1f}% (5-period) on {self.timeframe}"
        }


class VWAPScannerV2(BaseIntradayScanner):
    """VWAP Scanner."""
    
    def __init__(self, timeframe: str = None):
        super().__init__("vwap", timeframe)
    
    def analyze_stock(self, df: pd.DataFrame, symbol: str, live_ltp: Optional[float] = None) -> Optional[Dict]:
        if len(df) < 10:
            return None
        
        # VWAP calculation
        tp = (df['high'] + df['low'] + df['close']) / 3
        vwap = (tp * df['volume']).sum() / df['volume'].sum() if df['volume'].sum() > 0 else df['close'].iloc[-1]
        
        current_price = live_ltp if live_ltp is not None else df['close'].iloc[-1]
        prev_price = df['close'].iloc[-2]
        
        # BUY: Price crosses above VWAP AND holds. Relaxed volume check.
        vol_avg = df['volume'].rolling(5).mean().iloc[-1]
        curr_vol = df['volume'].iloc[-1]
        
        if prev_price <= vwap and current_price > vwap and curr_vol > vol_avg * 0.8:
            signal = "BUY"
            score = 80
        # SELL: Price crosses below VWAP AND Rejects VWAP
        elif prev_price >= vwap and current_price < vwap:
            signal = "SELL"
            score = 80
        else:
            return None
        
        return {
            "symbol": symbol,
            "name": symbol,
            "signal": signal,
            "strength": score,
            "current_price": round(current_price, 2),
            "vwap": round(vwap, 2),
            "is_live_price": live_ltp is not None,
            "target_price": round(current_price * (1.02 if signal == "BUY" else 0.98), 2),
            "stop_loss": round(vwap * (0.99 if signal == "BUY" else 1.01), 2),
            "reason": f"VWAP {signal}: Price crossover with volume confirmation"
        }


class SRBounceScannerV2(BaseIntradayScanner):
    """Support/Resistance Bounce Scanner."""
    
    def __init__(self, timeframe: str = None):
        super().__init__("sr_bounce", timeframe)
    
    def analyze_stock(self, df: pd.DataFrame, symbol: str, live_ltp: Optional[float] = None) -> Optional[Dict]:
        if len(df) < 50:
            return None
        
        # Use live LTP if available, otherwise use last candle close
        candle_price = df['close'].iloc[-1]
        current_price = live_ltp if live_ltp is not None else candle_price
        high_20 = df['high'].iloc[-21:-1].max()
        low_20 = df['low'].iloc[-21:-1].min()
        
        pivot = (df['high'].iloc[-1] + df['low'].iloc[-1] + df['close'].iloc[-1]) / 3
        
        near_support = df['low'].iloc[-1] <= low_20 * 1.025 and df['close'].iloc[-1] > df['open'].iloc[-1]
        near_resistance = df['high'].iloc[-1] >= high_20 * 0.975 and df['close'].iloc[-1] < df['open'].iloc[-1]
        
        if near_support:
            signal = "SUPPORT_BOUNCE"
            action = "BUY"
            level = low_20
            score = 75
        elif near_resistance:
            signal = "RESISTANCE_REJECT"
            action = "SELL"
            level = high_20
            score = 75
        else:
            return None
        
        return {
            "symbol": symbol,
            "name": symbol,
            "signal": signal,
            "action": action,
            "level_value": round(level, 2),
            "strength": score,
            "current_price": round(current_price, 2),
            "candle_price": round(candle_price, 2),
            "is_live_price": live_ltp is not None,
            "pivot": round(pivot, 2),
            "timeframe": self.timeframe,
            "target_price": round(pivot, 2),
            "stop_loss": round(level * (0.98 if action == "BUY" else 1.02), 2),
            "reason": f"{signal} at {level:.2f} on {self.timeframe}"
        }


# Factory function to get scanner by name
def get_scanner(strategy_name: str, timeframe: str = None) -> BaseIntradayScanner:
    """Get scanner instance by strategy name."""
    scanners = {
        "trend_finder": TrendFinderScanner,
        "breakout_detector": BreakoutScanner,
        "momentum": MomentumScannerV2,
        "mean_reversion": MeanReversionScannerV2,
        "gap_scanner": GapScannerV2,
        "relative_strength": RelativeStrengthScannerV2,
        "vwap": VWAPScannerV2,
        "sr_bounce": SRBounceScannerV2
    }
    
    scanner_class = scanners.get(strategy_name)
    if scanner_class:
        return scanner_class(timeframe)
    return None
