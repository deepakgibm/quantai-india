"""Head and Shoulders Pattern Strategy - Tier 1"""

from typing import Optional
import pandas as pd
from strategies.base import BaseStrategy, ScanResult, SignalType, StrategyTier, StrategyRegistry
from core.scanner.indicator_utils import volume_ratio


@StrategyRegistry.register
class HeadShoulders(BaseStrategy):
    """
    Head and Shoulders Pattern Detection
    Identifies H&S tops and inverse H&S bottoms.
    """
    
    name = "Head & Shoulders Pattern"
    description = "Detects Head & Shoulders reversal patterns"
    tier = StrategyTier.TIER_1
    min_bars_required = 50
    
    def scan(self, df: pd.DataFrame, symbol: str, index: str, timeframe: str) -> Optional[ScanResult]:
        if not self.validate_data(df):
            return None
        
        # Find local peaks and troughs
        highs = df['high'].values
        lows = df['low'].values
        close = df['close'].values
        
        # Simple peak detection - look for 5-bar pattern
        lookback = 30
        recent_highs = highs[-lookback:]
        recent_lows = lows[-lookback:]
        
        # Find peaks (local maxima)
        peaks = []
        troughs = []
        for i in range(2, len(recent_highs) - 2):
            if recent_highs[i] > max(recent_highs[i-2:i]) and recent_highs[i] > max(recent_highs[i+1:i+3]):
                peaks.append((i, recent_highs[i]))
            if recent_lows[i] < min(recent_lows[i-2:i]) and recent_lows[i] < min(recent_lows[i+1:i+3]):
                troughs.append((i, recent_lows[i]))
        
        vol_ratio = volume_ratio(df['volume']).iloc[-1]
        
        signal = SignalType.NEUTRAL
        confidence = 0.0
        pattern_type = ""
        
        # Check for H&S Top (3 peaks with middle being highest)
        if len(peaks) >= 3:
            last_3_peaks = peaks[-3:]
            heights = [p[1] for p in last_3_peaks]
            if heights[1] > heights[0] and heights[1] > heights[2]:
                # Check if shoulders are roughly equal
                shoulder_diff = abs(heights[0] - heights[2]) / heights[1]
                if shoulder_diff < 0.1:  # Shoulders within 10%
                    signal = SignalType.BEARISH
                    confidence = 0.6 + (0.1 - shoulder_diff)
                    pattern_type = "H&S Top"
        
        # Check for Inverse H&S (3 troughs with middle being lowest)
        if len(troughs) >= 3 and signal == SignalType.NEUTRAL:
            last_3_troughs = troughs[-3:]
            depths = [t[1] for t in last_3_troughs]
            if depths[1] < depths[0] and depths[1] < depths[2]:
                shoulder_diff = abs(depths[0] - depths[2]) / depths[1]
                if shoulder_diff < 0.1:
                    signal = SignalType.BULLISH
                    confidence = 0.6 + (0.1 - shoulder_diff)
                    pattern_type = "Inverse H&S"
        
        if signal == SignalType.NEUTRAL:
            return None
        
        if vol_ratio > 1.3:
            confidence = min(0.9, confidence + 0.1)
        
        support, resistance = self.get_support_resistance(df)
        
        return ScanResult(
            symbol=symbol,
            index=index,
            timeframe=timeframe,
            strategy=self.name,
            signal=signal,
            confidence_score=confidence,
            indicators={"pattern": pattern_type, "peaks_found": len(peaks), "troughs_found": len(troughs)},
            trend=self.get_trend(df),
            support=support,
            resistance=resistance,
            volume_ratio=vol_ratio
        )
