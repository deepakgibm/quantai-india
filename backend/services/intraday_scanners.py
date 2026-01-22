"""
Base Scanner Class for Upstox Intraday API
All 9 strategy scanners inherit from this base class.
"""

import os
import json
import pandas as pd
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import asyncio

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from config import settings
from core.indicators import ema, rsi, bollinger_bands
from core.indicators import ema, rsi, bollinger_bands


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
        """Get Nifty 500 symbols from database."""
        try:
            from services.nifty500_fetcher import Nifty500Symbol
            session = self._Session()
            try:
                symbols = session.query(Nifty500Symbol).all()
                return [(s.symbol, s.instrument_key) for s in symbols]
            finally:
                session.close()
        except Exception as e:
            print(f"Error fetching Nifty 500 symbols: {e}")
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
            
            return df
            
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            return pd.DataFrame()
    
    def get_cached_data(self, symbol: str, candles: int = 100) -> pd.DataFrame:
        """
        Get data from database cache (fallback if API fails).
        """
        try:
            from services.intraday_loader import IntradayCandle
            session = self._Session()
            try:
                results = session.query(IntradayCandle).filter(
                    IntradayCandle.symbol == symbol,
                    IntradayCandle.interval == self.timeframe
                ).order_by(desc(IntradayCandle.timestamp)).limit(candles).all()
                
                if not results:
                    return pd.DataFrame()
                
                data = [{
                    'timestamp': r.timestamp, 'open': r.open, 'high': r.high,
                    'low': r.low, 'close': r.close, 'volume': r.volume
                } for r in reversed(results)]
                
                df = pd.DataFrame(data)
                df.set_index('timestamp', inplace=True)
                return df
            finally:
                session.close()
        except Exception as e:
            print(f"Cache fallback error for {symbol}: {e}")
            return pd.DataFrame()
    
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
    
    async def scan_stock(self, symbol: str, instrument_key: str) -> Optional[Dict]:
        """Scan a single stock with live LTP."""
        try:
            # Try Upstox API first for historical data
            df = await self.fetch_intraday_data(symbol, instrument_key)
            
            # Fallback to cached data
            if df.empty:
                df = self.get_cached_data(symbol)
            
            if df.empty or len(df) < 20:
                return None
            
            # Fetch live LTP for real-time price
            live_ltp = await self.fetch_live_ltp(symbol, instrument_key)
            
            return self.analyze_stock(df, symbol, live_ltp)
            
        except Exception as e:
            print(f"Error scanning {symbol}: {e}")
            return None
    
    async def scan_all(self, limit: int = 10) -> List[Dict]:
        """
        Scan all Nifty 500 stocks and return top signals.
        """
        symbols = self.get_nifty500_symbols()
        if not symbols:
            print("No Nifty 500 symbols found")
            return []
        
        results = []
        
        # Process in batches to respect rate limits
        batch_size = 10
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            
            tasks = [self.scan_stock(sym, key) for sym, key in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, dict) and result.get("strength", 0) >= self.min_score:
                    results.append(result)
            
            # Rate limiting
            await asyncio.sleep(0.5)
        
        # Sort by strength and return top results
        results.sort(key=lambda x: x.get("strength", 0), reverse=True)
        return results[:limit]
    
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
        ema20 = ema(close, 20)
        ema50 = ema(close, 50)
        
        # Use live LTP if available, otherwise use last candle close
        candle_price = close.iloc[-1]
        current_price = live_ltp if live_ltp is not None else candle_price
        ema20_val = ema20.iloc[-1]
        ema50_val = ema50.iloc[-1]
        
        # Trend score
        if current_price > ema20_val > ema50_val:
            trend = "BULLISH"
            ema_score = 80 + min(20, (current_price - ema20_val) / ema20_val * 100 * 10)
        elif current_price < ema20_val < ema50_val:
            trend = "BEARISH"
            ema_score = 80 + min(20, (ema20_val - current_price) / ema20_val * 100 * 10)
        else:
            return None
        
        return {
            "symbol": symbol,
            "name": symbol,
            "trend": trend,
            "strength": round(ema_score),
            "current_price": round(current_price, 2),
            "candle_price": round(candle_price, 2),
            "is_live_price": live_ltp is not None,
            "ema20": round(ema20_val, 2),
            "ema50": round(ema50_val, 2),
            "timeframe": self.timeframe,
            "target_price": round(current_price * (1.03 if trend == "BULLISH" else 0.97), 2),
            "stop_loss": round(current_price * (0.98 if trend == "BULLISH" else 1.02), 2),
            "reason": f"EMA20 > EMA50, {trend} trend on {self.timeframe}"
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
        # Use live LTP if available, otherwise use last candle close
        candle_price = close.iloc[-1]
        current_price = live_ltp if live_ltp is not None else candle_price
        
        roc_10 = ((close.iloc[-1] - close.iloc[-11]) / close.iloc[-11]) * 100 if len(close) >= 11 else 0
        
        # MFI calculation
        tp = (df['high'] + df['low'] + df['close']) / 3
        mf = tp * df['volume']
        pos_mf = mf.where(tp > tp.shift(1), 0).rolling(14).sum()
        neg_mf = mf.where(tp < tp.shift(1), 0).rolling(14).sum()
        mfi = 100 - (100 / (1 + pos_mf / neg_mf))
        mfi_val = mfi.iloc[-1] if not pd.isna(mfi.iloc[-1]) else 50
        
        if roc_10 > 2 and 40 < mfi_val < 80:
            strength = 70 + min(30, roc_10 * 5)
            momentum_type = "STRONG" if roc_10 > 4 else "MODERATE"
        else:
            return None
        
        return {
            "symbol": symbol,
            "name": symbol,
            "momentum_type": momentum_type,
            "strength": round(strength),
            "current_price": round(current_price, 2),
            "candle_price": round(candle_price, 2),
            "is_live_price": live_ltp is not None,
            "roc_10d": round(roc_10, 2),
            "mfi": round(mfi_val, 2),
            "timeframe": self.timeframe,
            "target_price": round(current_price * 1.03, 2),
            "stop_loss": round(current_price * 0.97, 2),
            "reason": f"ROC +{roc_10:.1f}%, MFI {mfi_val:.0f} on {self.timeframe}"
        }


class MeanReversionScannerV2(BaseIntradayScanner):
    """Mean Reversion using Bollinger Bands and RSI."""
    
    def __init__(self, timeframe: str = None):
        super().__init__("mean_reversion", timeframe)
    
    def analyze_stock(self, df: pd.DataFrame, symbol: str, live_ltp: Optional[float] = None) -> Optional[Dict]:
        if len(df) < 20:
            return None
        
        close = df['close']
        # Use live LTP if available, otherwise use last candle close
        candle_price = close.iloc[-1]
        current_price = live_ltp if live_ltp is not None else candle_price
        
        # Bollinger Bands
        middle, upper, lower = bollinger_bands(close, 20, 2.0)
        
        # RSI
        rsi_series = rsi(close, 14)
        rsi_val = rsi_series.iloc[-1]
        if pd.isna(rsi_val):
            rsi_val = 50
        
        upper_val = upper.iloc[-1]
        lower_val = lower.iloc[-1]
        
        bb_pos = (current_price - lower_val) / (upper_val - lower_val) if upper_val != lower_val else 0.5
        
        if bb_pos < 0.2 and rsi_val < 35:
            signal = "OVERSOLD_BUY"
            action = "BUY"
            score = 85
        elif bb_pos > 0.8 and rsi > 65:
            signal = "OVERBOUGHT_SELL"
            action = "SELL"
            score = 85
        else:
            return None
        
        return {
            "symbol": symbol,
            "name": symbol,
            "signal": signal,
            "action": action,
            "strength": score,
            "current_price": round(current_price, 2),
            "candle_price": round(candle_price, 2),
            "is_live_price": live_ltp is not None,
            "rsi": round(rsi_val, 2),
            "bb_position": round(bb_pos * 100, 1),
            "timeframe": self.timeframe,
            "target_price": round(middle.iloc[-1], 2),
            "stop_loss": round(lower_val * 0.98 if action == "BUY" else upper_val * 1.02, 2),
            "reason": f"{signal}, RSI {rsi_val:.0f}, BB {bb_pos*100:.0f}% on {self.timeframe}"
        }


class GapScannerV2(BaseIntradayScanner):
    """Gap Scanner detecting overnight gaps."""
    
    def __init__(self, timeframe: str = None):
        super().__init__("gap_scanner", timeframe)
    
    def analyze_stock(self, df: pd.DataFrame, symbol: str, live_ltp: Optional[float] = None) -> Optional[Dict]:
        if len(df) < 2:
            return None
        
        prev_close = df['close'].iloc[-2]
        curr_open = df['open'].iloc[-1]
        # Use live LTP if available, otherwise use last candle close
        candle_price = df['close'].iloc[-1]
        current_price = live_ltp if live_ltp is not None else candle_price
        
        gap_pct = (curr_open - prev_close) / prev_close * 100
        
        if abs(gap_pct) < 1.5:
            return None
        
        gap_type = "GAP_UP" if gap_pct > 0 else "GAP_DOWN"
        filled = (current_price < curr_open) if gap_pct > 0 else (current_price > curr_open)
        trade_type = "FADE" if filled else "CONTINUATION"
        
        score = 60 + min(40, abs(gap_pct) * 10)
        
        return {
            "symbol": symbol,
            "name": symbol,
            "gap_type": gap_type,
            "gap_pct": round(gap_pct, 2),
            "trade_type": trade_type,
            "filled": filled,
            "strength": round(score),
            "current_price": round(current_price, 2),
            "candle_price": round(candle_price, 2),
            "is_live_price": live_ltp is not None,
            "timeframe": self.timeframe,
            "target_price": round(prev_close if filled else current_price * (1.02 if gap_pct > 0 else 0.98), 2),
            "stop_loss": round(curr_open * (0.99 if gap_pct > 0 else 1.01), 2),
            "reason": f"{gap_type} {abs(gap_pct):.1f}%, {trade_type} on {self.timeframe}"
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
        
        if ret_5 > 3 and ret_20 > 5:
            rs_rating = "VERY_STRONG"
            score = 85
        elif ret_5 > 2:
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
        if len(df) < 5:
            return None
        
        tp = (df['high'] + df['low'] + df['close']) / 3
        vwap = (tp * df['volume']).sum() / df['volume'].sum()
        # Use live LTP if available, otherwise use last candle close
        candle_price = df['close'].iloc[-1]
        current_price = live_ltp if live_ltp is not None else candle_price
        vol_ratio = df['volume'].iloc[-1] / df['volume'].mean() if df['volume'].mean() > 0 else 1
        
        vwap_dist = (current_price - vwap) / vwap * 100
        
        if current_price > vwap and vol_ratio >= 1.2:
            signal = "ABOVE_VWAP_LONG"
            action = "BUY"
            score = 70 + min(20, vwap_dist * 5)
        elif current_price < vwap and vol_ratio >= 1.2:
            signal = "BELOW_VWAP_SHORT"
            action = "SELL"
            score = 70 + min(20, abs(vwap_dist) * 5)
        else:
            return None
        
        return {
            "symbol": symbol,
            "name": symbol,
            "signal": signal,
            "action": action,
            "strength": round(score),
            "current_price": round(current_price, 2),
            "candle_price": round(candle_price, 2),
            "is_live_price": live_ltp is not None,
            "vwap": round(vwap, 2),
            "vwap_distance": round(vwap_dist, 2),
            "volume_ratio": round(vol_ratio, 2),
            "timeframe": self.timeframe,
            "target_price": round(current_price * (1.02 if action == "BUY" else 0.98), 2),
            "stop_loss": round(vwap * (0.99 if action == "BUY" else 1.01), 2),
            "reason": f"{signal}, {vol_ratio:.1f}x vol on {self.timeframe}"
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
        
        near_support = df['low'].iloc[-1] <= low_20 * 1.02 and df['close'].iloc[-1] > df['open'].iloc[-1]
        near_resistance = df['high'].iloc[-1] >= high_20 * 0.98 and df['close'].iloc[-1] < df['open'].iloc[-1]
        
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
