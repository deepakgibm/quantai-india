"""
Multi-Timeframe (MTF) Indicator Coordinator
Provides HTF (Higher Timeframe) context for LTF (Lower Timeframe) trading decisions.
"""

from typing import Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging

from engine.indicators import IndicatorSet, compute_indicators_for_symbol

logger = logging.getLogger(__name__)


class TrendAlignment(Enum):
    """Multi-timeframe trend alignment status."""
    BULLISH_ALIGNED = "BULLISH_ALIGNED"     # HTF and LTF both bullish
    BEARISH_ALIGNED = "BEARISH_ALIGNED"     # HTF and LTF both bearish
    HTF_BULLISH = "HTF_BULLISH"             # HTF bullish, LTF not aligned
    HTF_BEARISH = "HTF_BEARISH"             # HTF bearish, LTF not aligned
    NEUTRAL = "NEUTRAL"                      # No clear alignment


@dataclass
class MTFContext:
    """Multi-timeframe context for a symbol."""
    symbol: str
    primary_interval: str  # e.g., "15m"
    htf_interval: str      # e.g., "1d" or "4h"
    
    # Primary (LTF) indicators
    ltf_indicators: Optional[IndicatorSet] = None
    
    # Higher timeframe indicators
    htf_indicators: Optional[IndicatorSet] = None
    
    # Derived signals
    trend_alignment: TrendAlignment = TrendAlignment.NEUTRAL
    htf_trend: str = "NEUTRAL"
    ltf_trend: str = "NEUTRAL"
    
    # Key levels from HTF
    htf_resistance: float = 0.0
    htf_support: float = 0.0
    
    # Confluence score (0-100)
    confluence_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "primary_interval": self.primary_interval,
            "htf_interval": self.htf_interval,
            "trend_alignment": self.trend_alignment.value,
            "htf_trend": self.htf_trend,
            "ltf_trend": self.ltf_trend,
            "htf_resistance": self.htf_resistance,
            "htf_support": self.htf_support,
            "confluence_score": self.confluence_score,
            "ltf_indicators": self.ltf_indicators.to_dict() if self.ltf_indicators else {},
            "htf_indicators": self.htf_indicators.to_dict() if self.htf_indicators else {}
        }


# Interval hierarchy for MTF analysis
INTERVAL_HIERARCHY = {
    "1m": ["5m", "15m", "1h"],
    "3m": ["15m", "1h", "4h"],
    "5m": ["15m", "1h", "4h"],
    "15m": ["1h", "4h", "1d"],
    "30m": ["4h", "1d"],
    "1h": ["4h", "1d"],
    "4h": ["1d", "1w"],
    "1d": ["1w", "1M"]
}


def get_htf_interval(ltf_interval: str) -> str:
    """Get the higher timeframe for a given lower timeframe."""
    hierarchy = INTERVAL_HIERARCHY.get(ltf_interval, ["1d"])
    return hierarchy[0] if hierarchy else "1d"


def determine_trend(indicators: IndicatorSet) -> str:
    """Determine trend direction from indicator set."""
    if not indicators:
        return "NEUTRAL"
    
    # EMA stack analysis
    ema_bullish = indicators.ema_9 > indicators.ema_21 > indicators.ema_50
    ema_bearish = indicators.ema_9 < indicators.ema_21 < indicators.ema_50
    
    # Price vs EMAs
    price = indicators.current_close
    price_above_emas = price > indicators.ema_21
    price_below_emas = price < indicators.ema_21
    
    # RSI confirmation
    rsi_bullish = indicators.rsi_14 > 50
    rsi_bearish = indicators.rsi_14 < 50
    
    # MACD confirmation
    macd_bullish = indicators.macd_histogram > 0
    macd_bearish = indicators.macd_histogram < 0
    
    # Composite trend
    bullish_signals = sum([ema_bullish, price_above_emas, rsi_bullish, macd_bullish])
    bearish_signals = sum([ema_bearish, price_below_emas, rsi_bearish, macd_bearish])
    
    if bullish_signals >= 3:
        return "BULLISH"
    elif bearish_signals >= 3:
        return "BEARISH"
    else:
        return "NEUTRAL"


def compute_mtf_context(
    symbol: str,
    primary_interval: str = "15m",
    htf_interval: str = None
) -> Optional[MTFContext]:
    """
    Compute multi-timeframe context for a symbol.
    Combines LTF indicators with HTF trend context.
    """
    # Determine HTF if not specified
    if not htf_interval:
        htf_interval = get_htf_interval(primary_interval)
    
    # Get indicators for both timeframes
    ltf_indicators = compute_indicators_for_symbol(symbol, primary_interval)
    htf_indicators = compute_indicators_for_symbol(symbol, htf_interval)
    
    if not ltf_indicators:
        return None
    
    # Create context
    context = MTFContext(
        symbol=symbol,
        primary_interval=primary_interval,
        htf_interval=htf_interval,
        ltf_indicators=ltf_indicators,
        htf_indicators=htf_indicators
    )
    
    # Determine trends
    context.ltf_trend = determine_trend(ltf_indicators)
    context.htf_trend = determine_trend(htf_indicators) if htf_indicators else "NEUTRAL"
    
    # Determine alignment
    if context.htf_trend == "BULLISH" and context.ltf_trend == "BULLISH":
        context.trend_alignment = TrendAlignment.BULLISH_ALIGNED
    elif context.htf_trend == "BEARISH" and context.ltf_trend == "BEARISH":
        context.trend_alignment = TrendAlignment.BEARISH_ALIGNED
    elif context.htf_trend == "BULLISH":
        context.trend_alignment = TrendAlignment.HTF_BULLISH
    elif context.htf_trend == "BEARISH":
        context.trend_alignment = TrendAlignment.HTF_BEARISH
    else:
        context.trend_alignment = TrendAlignment.NEUTRAL
    
    # Extract HTF support/resistance levels
    if htf_indicators:
        context.htf_resistance = htf_indicators.high_20
        context.htf_support = htf_indicators.low_20
    
    # Calculate confluence score
    context.confluence_score = _calculate_confluence(context)
    
    return context


def _calculate_confluence(context: MTFContext) -> float:
    """
    Calculate confluence score (0-100) based on MTF alignment.
    Higher scores indicate stronger alignment and higher probability trades.
    """
    score = 50.0  # Neutral baseline
    
    # Trend alignment bonus
    if context.trend_alignment == TrendAlignment.BULLISH_ALIGNED:
        score += 25
    elif context.trend_alignment == TrendAlignment.BEARISH_ALIGNED:
        score += 25
    elif context.trend_alignment in [TrendAlignment.HTF_BULLISH, TrendAlignment.HTF_BEARISH]:
        score += 10
    
    # RSI confluence
    if context.ltf_indicators and context.htf_indicators:
        ltf_rsi = context.ltf_indicators.rsi_14
        htf_rsi = context.htf_indicators.rsi_14
        
        # Both oversold or overbought
        if (ltf_rsi < 30 and htf_rsi < 40) or (ltf_rsi > 70 and htf_rsi > 60):
            score += 10
    
    # MACD alignment
    if context.ltf_indicators and context.htf_indicators:
        ltf_macd = context.ltf_indicators.macd_histogram
        htf_macd = context.htf_indicators.macd_histogram
        
        if (ltf_macd > 0 and htf_macd > 0) or (ltf_macd < 0 and htf_macd < 0):
            score += 10
    
    # Price position relative to HTF levels
    if context.ltf_indicators and context.htf_support > 0:
        price = context.ltf_indicators.current_close
        
        # Near HTF support (bullish setup)
        if context.htf_trend == "BULLISH" and price < context.htf_support * 1.02:
            score += 5
        
        # Near HTF resistance (bearish setup)
        if context.htf_trend == "BEARISH" and price > context.htf_resistance * 0.98:
            score += 5
    
    return min(100.0, max(0.0, score))


def get_mtf_trade_direction(context: MTFContext) -> Optional[str]:
    """
    Get recommended trade direction based on MTF context.
    Returns "LONG", "SHORT", or None.
    """
    if not context:
        return None
    
    # Only trade with HTF trend
    if context.trend_alignment == TrendAlignment.BULLISH_ALIGNED:
        return "LONG"
    elif context.trend_alignment == TrendAlignment.BEARISH_ALIGNED:
        return "SHORT"
    elif context.confluence_score >= 70:
        # High confluence can override neutral alignment
        if context.htf_trend == "BULLISH":
            return "LONG"
        elif context.htf_trend == "BEARISH":
            return "SHORT"
    
    return None


def get_mtf_entry_quality(context: MTFContext) -> str:
    """
    Rate entry quality based on MTF context.
    Returns "A" (best), "B" (good), "C" (fair), or "D" (poor).
    """
    if not context:
        return "D"
    
    score = context.confluence_score
    is_aligned = context.trend_alignment in [
        TrendAlignment.BULLISH_ALIGNED,
        TrendAlignment.BEARISH_ALIGNED
    ]
    
    if score >= 80 and is_aligned:
        return "A"
    elif score >= 65 and is_aligned:
        return "B"
    elif score >= 50:
        return "C"
    else:
        return "D"
