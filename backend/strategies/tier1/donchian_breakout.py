"""Donchian Channel Breakout Strategy - Tier 1"""

from typing import Optional
import pandas as pd
from strategies.base import BaseStrategy, ScanResult, SignalType, StrategyTier, StrategyRegistry
from core.scanner.indicator_utils import donchian_channels, volume_ratio


@StrategyRegistry.register
class DonchianBreakout(BaseStrategy):
    """
    Donchian Channel Breakout Strategy
    Buy on breakout above upper channel, Sell on breakdown below lower channel.
    """
    
    name = "Donchian Channel Breakout"
    description = "Turtle trading style breakout using Donchian Channels"
    tier = StrategyTier.TIER_1
    min_bars_required = 25
    
    def __init__(self, period: int = 20):
        self.period = period
    
    def scan(self, df: pd.DataFrame, symbol: str, index: str, timeframe: str) -> Optional[ScanResult]:
        if not self.validate_data(df):
            return None
        
        upper, middle, lower = donchian_channels(df['high'], df['low'], self.period)
        
        close = df['close'].iloc[-1]
        high = df['high'].iloc[-1]
        low = df['low'].iloc[-1]
        prev_high = df['high'].iloc[-2]
        prev_low = df['low'].iloc[-2]
        
        upper_band = upper.iloc[-2]  # Use previous bar's channel
        lower_band = lower.iloc[-2]
        
        vol_ratio = volume_ratio(df['volume']).iloc[-1]
        
        signal = SignalType.NEUTRAL
        confidence = 0.0
        
        # Bullish breakout
        if high > upper_band and prev_high <= upper.iloc[-3]:
            signal = SignalType.BULLISH
            confidence = 0.7
            if vol_ratio > 1.5:
                confidence += 0.15
        # Bearish breakdown
        elif low < lower_band and prev_low >= lower.iloc[-3]:
            signal = SignalType.BEARISH
            confidence = 0.7
            if vol_ratio > 1.5:
                confidence += 0.15
        else:
            return None
        
        support, resistance = self.get_support_resistance(df)
        
        return ScanResult(
            symbol=symbol,
            index=index,
            timeframe=timeframe,
            strategy=self.name,
            signal=signal,
            confidence_score=min(0.95, confidence),
            indicators={
                "upper_channel": upper_band,
                "middle_channel": middle.iloc[-1],
                "lower_channel": lower_band
            },
            trend=self.get_trend(df),
            support=support,
            resistance=resistance,
            volume_ratio=vol_ratio
        )
