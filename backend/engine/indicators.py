"""
Shared Indicator Engine
Computes indicators ONCE per symbol/interval, reused by all strategies.
No database queries allowed in this module.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class IndicatorSet:
    """Complete set of indicators for a symbol/interval."""
    # Trend
    sma_20: float = 0.0
    sma_50: float = 0.0
    sma_200: float = 0.0
    ema_9: float = 0.0
    ema_21: float = 0.0
    ema_50: float = 0.0
    
    # Momentum
    rsi_14: float = 50.0
    macd_line: float = 0.0
    macd_signal: float = 0.0
    macd_histogram: float = 0.0
    
    # Volatility
    atr_14: float = 0.0
    bollinger_upper: float = 0.0
    bollinger_middle: float = 0.0
    bollinger_lower: float = 0.0
    bollinger_width: float = 0.0
    
    # Volume
    volume_sma_20: float = 0.0
    volume_ratio: float = 1.0
    vwap: float = 0.0
    
    # Price Action
    prev_close: float = 0.0
    current_close: float = 0.0
    change_pct: float = 0.0
    high_20: float = 0.0
    low_20: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "sma_20": self.sma_20,
            "sma_50": self.sma_50,
            "sma_200": self.sma_200,
            "ema_9": self.ema_9,
            "ema_21": self.ema_21,
            "ema_50": self.ema_50,
            "rsi_14": self.rsi_14,
            "macd_line": self.macd_line,
            "macd_signal": self.macd_signal,
            "macd_histogram": self.macd_histogram,
            "atr_14": self.atr_14,
            "bollinger_upper": self.bollinger_upper,
            "bollinger_middle": self.bollinger_middle,
            "bollinger_lower": self.bollinger_lower,
            "bollinger_width": self.bollinger_width,
            "volume_sma_20": self.volume_sma_20,
            "volume_ratio": self.volume_ratio,
            "vwap": self.vwap,
            "prev_close": self.prev_close,
            "current_close": self.current_close,
            "change_pct": self.change_pct,
            "high_20": self.high_20,
            "low_20": self.low_20
        }


class IndicatorEngine:
    """
    Computes all indicators for a symbol.
    Uses efficient incremental updates where possible.
    """
    
    @staticmethod
    def compute_all(
        closes: List[float],
        highs: List[float],
        lows: List[float],
        volumes: List[int]
    ) -> IndicatorSet:
        """
        Compute all indicators from price/volume data.
        Requires minimum 200 data points for full indicator set.
        """
        if len(closes) < 20:
            return IndicatorSet()
        
        indicators = IndicatorSet()
        
        # Current and previous close
        indicators.current_close = closes[-1]
        indicators.prev_close = closes[-2] if len(closes) >= 2 else closes[-1]
        indicators.change_pct = (
            (indicators.current_close - indicators.prev_close) / indicators.prev_close * 100
            if indicators.prev_close > 0 else 0.0
        )
        
        # SMAs
        indicators.sma_20 = IndicatorEngine._sma(closes, 20)
        indicators.sma_50 = IndicatorEngine._sma(closes, 50) if len(closes) >= 50 else indicators.sma_20
        indicators.sma_200 = IndicatorEngine._sma(closes, 200) if len(closes) >= 200 else indicators.sma_50
        
        # EMAs
        indicators.ema_9 = IndicatorEngine._ema(closes, 9)
        indicators.ema_21 = IndicatorEngine._ema(closes, 21)
        indicators.ema_50 = IndicatorEngine._ema(closes, 50) if len(closes) >= 50 else indicators.ema_21
        
        # RSI
        indicators.rsi_14 = IndicatorEngine._rsi(closes, 14)
        
        # MACD
        macd_line, macd_signal, macd_hist = IndicatorEngine._macd(closes)
        indicators.macd_line = macd_line
        indicators.macd_signal = macd_signal
        indicators.macd_histogram = macd_hist
        
        # ATR
        if len(highs) >= 14 and len(lows) >= 14:
            indicators.atr_14 = IndicatorEngine._atr(highs, lows, closes, 14)
        
        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = IndicatorEngine._bollinger(closes, 20, 2.0)
        indicators.bollinger_upper = bb_upper
        indicators.bollinger_middle = bb_middle
        indicators.bollinger_lower = bb_lower
        indicators.bollinger_width = (bb_upper - bb_lower) / bb_middle if bb_middle > 0 else 0.0
        
        # Volume
        if len(volumes) >= 20:
            indicators.volume_sma_20 = sum(volumes[-20:]) / 20
            indicators.volume_ratio = volumes[-1] / indicators.volume_sma_20 if indicators.volume_sma_20 > 0 else 1.0
        
        # VWAP (simplified - uses last 20 bars)
        if len(volumes) >= 20 and len(closes) >= 20:
            typical_prices = [(highs[i] + lows[i] + closes[i]) / 3 for i in range(-20, 0)]
            vols = volumes[-20:]
            total_pv = sum(tp * v for tp, v in zip(typical_prices, vols))
            total_v = sum(vols)
            indicators.vwap = total_pv / total_v if total_v > 0 else closes[-1]
        
        # Price action
        indicators.high_20 = max(highs[-20:]) if len(highs) >= 20 else max(highs)
        indicators.low_20 = min(lows[-20:]) if len(lows) >= 20 else min(lows)
        
        return indicators
    
    @staticmethod
    def _sma(data: List[float], period: int) -> float:
        """Simple Moving Average."""
        if len(data) < period:
            return data[-1] if data else 0.0
        return sum(data[-period:]) / period
    
    @staticmethod
    def _ema(data: List[float], period: int) -> float:
        """Exponential Moving Average."""
        if len(data) < period:
            return data[-1] if data else 0.0
        
        multiplier = 2 / (period + 1)
        ema = sum(data[:period]) / period  # Initial SMA
        
        for price in data[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    @staticmethod
    def _rsi(closes: List[float], period: int = 14) -> float:
        """Relative Strength Index."""
        if len(closes) < period + 1:
            return 50.0
        
        gains = []
        losses = []
        
        for i in range(1, len(closes)):
            change = closes[i] - closes[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        if len(gains) < period:
            return 50.0
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 2)
    
    @staticmethod
    def _macd(
        closes: List[float],
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> Tuple[float, float, float]:
        """MACD Line, Signal Line, Histogram."""
        if len(closes) < slow:
            return 0.0, 0.0, 0.0
        
        ema_fast = IndicatorEngine._ema(closes, fast)
        ema_slow = IndicatorEngine._ema(closes, slow)
        macd_line = ema_fast - ema_slow
        
        # For signal line, we'd need historical MACD values
        # Simplified: use current MACD as approximation
        macd_signal = macd_line * 0.9  # Approximation
        macd_hist = macd_line - macd_signal
        
        return round(macd_line, 4), round(macd_signal, 4), round(macd_hist, 4)
    
    @staticmethod
    def _atr(
        highs: List[float],
        lows: List[float],
        closes: List[float],
        period: int = 14
    ) -> float:
        """Average True Range."""
        if len(highs) < period or len(lows) < period or len(closes) < period:
            return 0.0
        
        tr_values = []
        for i in range(-period, 0):
            high = highs[i]
            low = lows[i]
            prev_close = closes[i-1] if i > -len(closes) else closes[i]
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            tr_values.append(tr)
        
        return sum(tr_values) / len(tr_values)
    
    @staticmethod
    def _bollinger(
        closes: List[float],
        period: int = 20,
        std_dev: float = 2.0
    ) -> Tuple[float, float, float]:
        """Bollinger Bands (Upper, Middle, Lower)."""
        if len(closes) < period:
            price = closes[-1] if closes else 0.0
            return price, price, price
        
        sma = sum(closes[-period:]) / period
        
        variance = sum((x - sma) ** 2 for x in closes[-period:]) / period
        std = variance ** 0.5
        
        upper = sma + (std_dev * std)
        lower = sma - (std_dev * std)
        
        return round(upper, 2), round(sma, 2), round(lower, 2)


def compute_indicators_for_symbol(
    symbol: str,
    interval: str
) -> Optional[IndicatorSet]:
    """
    Compute indicators for a symbol using in-memory state.
    This is the main entry point for strategy evaluation.
    """
    from engine.state import get_state_manager
    
    state_manager = get_state_manager()
    symbol_state = state_manager.get_symbol(symbol)
    
    if not symbol_state:
        return None
    
    candles = symbol_state.get_candles(interval, 200)
    if len(candles) < 20:
        return None
    
    closes = [c.close for c in candles]
    highs = [c.high for c in candles]
    lows = [c.low for c in candles]
    volumes = [c.volume for c in candles]
    
    indicators = IndicatorEngine.compute_all(closes, highs, lows, volumes)
    
    # Cache in symbol state
    symbol_state.set_indicators(interval, indicators.to_dict())
    
    return indicators
