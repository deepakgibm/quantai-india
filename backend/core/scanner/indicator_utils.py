"""
Technical Indicator Utilities
Common indicator calculations used across strategies.
"""

import numpy as np
import pandas as pd
from typing import Tuple


def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """MACD - Moving Average Convergence Divergence."""
    fast_ema = ema(close, fast)
    slow_ema = ema(close, slow)
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def bollinger_bands(close: pd.Series, period: int = 20, std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Bollinger Bands - Middle, Upper, Lower."""
    middle = sma(close, period)
    std = close.rolling(window=period).std()
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    return middle, upper, lower


def williams_r(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Williams %R Indicator."""
    highest_high = high.rolling(window=period).max()
    lowest_low = low.rolling(window=period).min()
    return -100 * (highest_high - close) / (highest_high - lowest_low)


def donchian_channels(high: pd.Series, low: pd.Series, period: int = 20) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Donchian Channels - Upper, Middle, Lower."""
    upper = high.rolling(window=period).max()
    lower = low.rolling(window=period).min()
    middle = (upper + lower) / 2
    return upper, middle, lower


def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Average Directional Index with +DI and -DI."""
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(span=period, adjust=False).mean()
    
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    
    plus_di = 100 * (plus_dm.ewm(span=period, adjust=False).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(span=period, adjust=False).mean() / atr)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx_val = dx.ewm(span=period, adjust=False).mean()
    
    return adx_val, plus_di, minus_di


def stochastic(high: pd.Series, low: pd.Series, close: pd.Series, k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
    """Stochastic Oscillator - %K and %D."""
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()
    k = 100 * (close - lowest_low) / (highest_high - lowest_low)
    d = k.rolling(window=d_period).mean()
    return k, d


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range."""
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()  # Use standard rolling mean for consistency with existing computer


def mfi(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, period: int = 14) -> pd.Series:
    """Money Flow Index."""
    typical_price = (high + low + close) / 3
    money_flow = typical_price * volume
    
    positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0.0)
    negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0.0)
    
    positive_mf = positive_flow.rolling(window=period).sum()
    negative_mf = negative_flow.rolling(window=period).sum()
    
    mfr = positive_mf / negative_mf
    mfi_val = 100 - (100 / (1 + mfr))
    return mfi_val


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """On-Balance Volume."""
    sign = np.sign(close.diff())
    sign.iloc[0] = 0
    return (volume * sign).cumsum()


def cci(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> pd.Series:
    """Commodity Channel Index."""
    typical_price = (high + low + close) / 3
    tp_sma = typical_price.rolling(window=period).mean()
    mean_dev = typical_price.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())
    return (typical_price - tp_sma) / (0.015 * mean_dev)


def parabolic_sar(high: pd.Series, low: pd.Series, af_start: float = 0.02, af_step: float = 0.02, af_max: float = 0.2) -> pd.Series:
    """Parabolic SAR."""
    length = len(high)
    sar = pd.Series(index=high.index, dtype=float)
    trend = pd.Series(index=high.index, dtype=int)
    ep = pd.Series(index=high.index, dtype=float)
    af = pd.Series(index=high.index, dtype=float)
    
    # Initialize
    sar.iloc[0] = low.iloc[0]
    trend.iloc[0] = 1
    ep.iloc[0] = high.iloc[0]
    af.iloc[0] = af_start
    
    for i in range(1, length):
        if trend.iloc[i-1] == 1:  # Uptrend
            sar.iloc[i] = sar.iloc[i-1] + af.iloc[i-1] * (ep.iloc[i-1] - sar.iloc[i-1])
            sar.iloc[i] = min(sar.iloc[i], low.iloc[i-1], low.iloc[i-2] if i > 1 else low.iloc[i-1])
            
            if low.iloc[i] < sar.iloc[i]:  # Reversal
                trend.iloc[i] = -1
                sar.iloc[i] = ep.iloc[i-1]
                ep.iloc[i] = low.iloc[i]
                af.iloc[i] = af_start
            else:
                trend.iloc[i] = 1
                if high.iloc[i] > ep.iloc[i-1]:
                    ep.iloc[i] = high.iloc[i]
                    af.iloc[i] = min(af.iloc[i-1] + af_step, af_max)
                else:
                    ep.iloc[i] = ep.iloc[i-1]
                    af.iloc[i] = af.iloc[i-1]
        else:  # Downtrend
            sar.iloc[i] = sar.iloc[i-1] + af.iloc[i-1] * (ep.iloc[i-1] - sar.iloc[i-1])
            sar.iloc[i] = max(sar.iloc[i], high.iloc[i-1], high.iloc[i-2] if i > 1 else high.iloc[i-1])
            
            if high.iloc[i] > sar.iloc[i]:  # Reversal
                trend.iloc[i] = 1
                sar.iloc[i] = ep.iloc[i-1]
                ep.iloc[i] = high.iloc[i]
                af.iloc[i] = af_start
            else:
                trend.iloc[i] = -1
                if low.iloc[i] < ep.iloc[i-1]:
                    ep.iloc[i] = low.iloc[i]
                    af.iloc[i] = min(af.iloc[i-1] + af_step, af_max)
                else:
                    ep.iloc[i] = ep.iloc[i-1]
                    af.iloc[i] = af.iloc[i-1]
    
    return sar


def ichimoku(high: pd.Series, low: pd.Series, close: pd.Series, 
             tenkan: int = 9, kijun: int = 26, senkou_b: int = 52) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
    """Ichimoku Cloud - Tenkan, Kijun, Senkou A, Senkou B, Chikou."""
    tenkan_sen = (high.rolling(tenkan).max() + low.rolling(tenkan).min()) / 2
    kijun_sen = (high.rolling(kijun).max() + low.rolling(kijun).min()) / 2
    senkou_a = ((tenkan_sen + kijun_sen) / 2).shift(kijun)
    senkou_b_line = ((high.rolling(senkou_b).max() + low.rolling(senkou_b).min()) / 2).shift(kijun)
    chikou = close.shift(-kijun)
    return tenkan_sen, kijun_sen, senkou_a, senkou_b_line, chikou


def fibonacci_levels(high: float, low: float) -> dict:
    """Calculate Fibonacci retracement levels."""
    diff = high - low
    return {
        0.0: high,
        0.236: high - diff * 0.236,
        0.382: high - diff * 0.382,
        0.5: high - diff * 0.5,
        0.618: high - diff * 0.618,
        0.786: high - diff * 0.786,
        1.0: low
    }


def volume_ratio(volume: pd.Series, period: int = 20) -> pd.Series:
    """Current volume vs average volume ratio."""
    avg_vol = volume.rolling(window=period).mean()
    return volume / avg_vol


def price_momentum(close: pd.Series, period: int = 126) -> pd.Series:
    """Price momentum (rate of change)."""
    return (close / close.shift(period) - 1) * 100
