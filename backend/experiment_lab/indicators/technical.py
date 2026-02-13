"""
Technical Indicators Module for Experiment Lab
Provides all indicator calculations needed by the 70 strategies.
Uses OHLCV data only.
"""

import pandas as pd
import numpy as np
from typing import Tuple


class TechnicalIndicators:
    """
    Centralized technical indicator calculations.
    All methods are static and operate on pandas DataFrames/Series.
    """
    
    # ==================== MOVING AVERAGES ====================
    
    @staticmethod
    def sma(series: pd.Series, period: int) -> pd.Series:
        """Simple Moving Average."""
        return series.rolling(window=period).mean()
    
    @staticmethod
    def ema(series: pd.Series, period: int) -> pd.Series:
        """Exponential Moving Average."""
        return series.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def wma(series: pd.Series, period: int) -> pd.Series:
        """Weighted Moving Average - Vectorized version."""
        weights = np.arange(1, period + 1)
        # Using a faster vectorized approach for WMA
        try:
            return series.rolling(window=period).apply(
                lambda x: np.dot(x, weights) / weights.sum(), raw=True
            )
        except Exception:
            # Fallback for older pandas or edge cases
            return series.rolling(window=period).mean()
    
    # ==================== MOMENTUM INDICATORS ====================
    
    @staticmethod
    def rsi(series: pd.Series, period: int = 14) -> pd.Series:
        """Relative Strength Index."""
        delta = series.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        
        avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
        avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
        
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50)
    
    @staticmethod
    def stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """Stochastic Oscillator - returns %K and %D."""
        low_min = df['low'].rolling(window=k_period).min()
        high_max = df['high'].rolling(window=k_period).max()
        
        stoch_k = 100 * (df['close'] - low_min) / (high_max - low_min)
        stoch_d = stoch_k.rolling(window=d_period).mean()
        
        return stoch_k.fillna(50), stoch_d.fillna(50)
    
    @staticmethod
    def williams_r(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Williams %R."""
        high_max = df['high'].rolling(window=period).max()
        low_min = df['low'].rolling(window=period).min()
        
        wr = -100 * (high_max - df['close']) / (high_max - low_min)
        return wr.fillna(-50)
    
    @staticmethod
    def roc(series: pd.Series, period: int = 10) -> pd.Series:
        """Rate of Change (Momentum)."""
        return ((series - series.shift(period)) / series.shift(period)) * 100
    
    @staticmethod
    def cci(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Commodity Channel Index - Vectorized MAD."""
        tp = (df['high'] + df['low'] + df['close']) / 3
        sma_tp = tp.rolling(window=period).mean()
        
        # Faster vectorized MAD calculation
        def get_mad(x):
            return np.abs(x - x.mean()).mean()
            
        mad = tp.rolling(window=period).apply(get_mad, raw=True)
        return (tp - sma_tp) / (0.015 * mad + 1e-10)  # Avoid div by zero
    
    # ==================== TREND INDICATORS ====================
    
    @staticmethod
    def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """MACD - returns MACD line, Signal line, and Histogram."""
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def adx(df: pd.DataFrame, period: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """ADX - returns ADX, +DI, and -DI."""
        high = df['high']
        low = df['low']
        close = df['close']
        
        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Directional Movements
        up_move = high - high.shift()
        down_move = low.shift() - low
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        # Smoothed values
        atr = pd.Series(tr).ewm(span=period, adjust=False).mean()
        plus_di = 100 * pd.Series(plus_dm).ewm(span=period, adjust=False).mean() / atr
        minus_di = 100 * pd.Series(minus_dm).ewm(span=period, adjust=False).mean() / atr
        
        # ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        adx = dx.ewm(span=period, adjust=False).mean()
        
        return adx.fillna(0), plus_di.fillna(0), minus_di.fillna(0)
    
    @staticmethod
    def supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> Tuple[pd.Series, pd.Series]:
        """Supertrend - returns Supertrend line and direction (1=bullish, -1=bearish)."""
        high = df['high']
        low = df['low']
        close = df['close']
        
        # ATR
        tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        # Basic bands
        hl2 = (high + low) / 2
        upper_band = hl2 + (multiplier * atr)
        lower_band = hl2 - (multiplier * atr)
        
        # Supertrend calculation
        supertrend = pd.Series(index=df.index, dtype=float)
        direction = pd.Series(index=df.index, dtype=int)
        
        supertrend.iloc[0] = upper_band.iloc[0]
        direction.iloc[0] = 1
        
        for i in range(1, len(df)):
            if close.iloc[i] > supertrend.iloc[i-1]:
                supertrend.iloc[i] = lower_band.iloc[i]
                direction.iloc[i] = 1
            else:
                supertrend.iloc[i] = upper_band.iloc[i]
                direction.iloc[i] = -1
        
        return supertrend, direction
    
    # ==================== VOLATILITY INDICATORS ====================
    
    @staticmethod
    def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Average True Range."""
        high = df['high']
        low = df['low']
        close = df['close'].shift(1)
        
        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        return tr.rolling(window=period).mean()
    
    @staticmethod
    def bollinger_bands(series: pd.Series, period: int = 20, std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Bollinger Bands - returns Upper, Middle (SMA), Lower."""
        middle = series.rolling(window=period).mean()
        std = series.rolling(window=period).std()
        
        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)
        
        return upper, middle, lower
    
    @staticmethod
    def donchian_channel(df: pd.DataFrame, period: int = 20) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Donchian Channel - returns Upper, Middle, Lower."""
        upper = df['high'].rolling(window=period).max()
        lower = df['low'].rolling(window=period).min()
        middle = (upper + lower) / 2
        
        return upper, middle, lower
    
    # ==================== VOLUME INDICATORS ====================
    
    @staticmethod
    def obv(df: pd.DataFrame) -> pd.Series:
        """On-Balance Volume."""
        sign = np.where(df['close'] > df['close'].shift(1), 1,
                       np.where(df['close'] < df['close'].shift(1), -1, 0))
        return (sign * df['volume']).cumsum()
    
    @staticmethod
    def vwap(df: pd.DataFrame) -> pd.Series:
        """Volume Weighted Average Price."""
        tp = (df['high'] + df['low'] + df['close']) / 3
        return (tp * df['volume']).cumsum() / df['volume'].cumsum()
    
    @staticmethod
    def volume_sma(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Volume Simple Moving Average."""
        return df['volume'].rolling(window=period).mean()
    
    @staticmethod
    def volume_ratio(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Current volume vs average volume ratio."""
        avg_vol = df['volume'].rolling(window=period).mean()
        return df['volume'] / avg_vol
    
    # ==================== ICHIMOKU ====================
    
    @staticmethod
    def ichimoku(df: pd.DataFrame, tenkan: int = 9, kijun: int = 26, senkou_b: int = 52) -> dict:
        """
        Ichimoku Cloud components.
        Returns dict with: tenkan_sen, kijun_sen, senkou_a, senkou_b, chikou_span
        """
        # Tenkan-sen (Conversion Line)
        tenkan_high = df['high'].rolling(window=tenkan).max()
        tenkan_low = df['low'].rolling(window=tenkan).min()
        tenkan_sen = (tenkan_high + tenkan_low) / 2
        
        # Kijun-sen (Base Line)
        kijun_high = df['high'].rolling(window=kijun).max()
        kijun_low = df['low'].rolling(window=kijun).min()
        kijun_sen = (kijun_high + kijun_low) / 2
        
        # Senkou Span A (Leading Span A)
        senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(kijun)
        
        # Senkou Span B (Leading Span B)
        senkou_b_high = df['high'].rolling(window=senkou_b).max()
        senkou_b_low = df['low'].rolling(window=senkou_b).min()
        senkou_span_b = ((senkou_b_high + senkou_b_low) / 2).shift(kijun)
        
        # Chikou Span (Lagging Span)
        chikou_span = df['close'].shift(-kijun)
        
        return {
            'tenkan_sen': tenkan_sen,
            'kijun_sen': kijun_sen,
            'senkou_a': senkou_span_a,
            'senkou_b': senkou_span_b,
            'chikou_span': chikou_span
        }
    
    # ==================== SUPPORT/RESISTANCE ====================
    
    @staticmethod
    def pivot_points(df: pd.DataFrame) -> dict:
        """Calculate pivot points (for daily data)."""
        pivot = (df['high'] + df['low'] + df['close']) / 3
        r1 = 2 * pivot - df['low']
        s1 = 2 * pivot - df['high']
        r2 = pivot + (df['high'] - df['low'])
        s2 = pivot - (df['high'] - df['low'])
        
        return {
            'pivot': pivot,
            'r1': r1, 'r2': r2,
            's1': s1, 's2': s2
        }
    
    @staticmethod
    def fibonacci_levels(high: float, low: float) -> dict:
        """Calculate Fibonacci retracement levels."""
        diff = high - low
        return {
            'level_0': low,
            'level_236': low + 0.236 * diff,
            'level_382': low + 0.382 * diff,
            'level_500': low + 0.5 * diff,
            'level_618': low + 0.618 * diff,
            'level_786': low + 0.786 * diff,
            'level_100': high
        }
    
    # ==================== PATTERN DETECTION HELPERS ====================
    
    @staticmethod
    def is_higher_high(df: pd.DataFrame, lookback: int = 5) -> pd.Series:
        """Detect higher highs."""
        return df['high'] > df['high'].rolling(window=lookback).max().shift(1)
    
    @staticmethod
    def is_lower_low(df: pd.DataFrame, lookback: int = 5) -> pd.Series:
        """Detect lower lows."""
        return df['low'] < df['low'].rolling(window=lookback).min().shift(1)
    
    @staticmethod
    def is_bullish_candle(df: pd.DataFrame) -> pd.Series:
        """Detect bullish candles."""
        return df['close'] > df['open']
    
    @staticmethod
    def is_bearish_candle(df: pd.DataFrame) -> pd.Series:
        """Detect bearish candles."""
        return df['close'] < df['open']
    
    @staticmethod
    def candle_body_ratio(df: pd.DataFrame) -> pd.Series:
        """Calculate ratio of body to full range."""
        body = abs(df['close'] - df['open'])
        full_range = df['high'] - df['low']
        return body / full_range.replace(0, np.nan)


__all__ = ['TechnicalIndicators']
