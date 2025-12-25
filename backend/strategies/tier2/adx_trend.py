"""ADX Trend Strength Strategy - Tier 2"""

from typing import Optional
import pandas as pd
from strategies.base import BaseStrategy, ScanResult, SignalType, StrategyTier, StrategyRegistry
from core.scanner.indicator_utils import adx, volume_ratio


@StrategyRegistry.register
class ADXTrend(BaseStrategy):
    """ADX Trend Strength Strategy - identifies strong trending stocks."""
    
    name = "ADX Trend Strength"
    description = "Identifies strong trends using ADX with +DI/-DI crossovers"
    tier = StrategyTier.TIER_2
    min_bars_required = 30
    
    def __init__(self, period: int = 14, adx_threshold: float = 25):
        self.period = period
        self.adx_threshold = adx_threshold
    
    def scan(self, df: pd.DataFrame, symbol: str, index: str, timeframe: str) -> Optional[ScanResult]:
        if not self.validate_data(df):
            return None
        
        adx_val, plus_di, minus_di = adx(df['high'], df['low'], df['close'], self.period)
        
        current_adx = adx_val.iloc[-1]
        current_plus_di = plus_di.iloc[-1]
        current_minus_di = minus_di.iloc[-1]
        prev_plus_di = plus_di.iloc[-2]
        prev_minus_di = minus_di.iloc[-2]
        
        vol_ratio = volume_ratio(df['volume']).iloc[-1]
        
        signal = SignalType.NEUTRAL
        confidence = 0.0
        
        # Strong trend with +DI > -DI
        if current_adx > self.adx_threshold:
            if current_plus_di > current_minus_di and prev_plus_di <= prev_minus_di:
                signal = SignalType.BULLISH
                confidence = 0.6 + min(0.25, (current_adx - self.adx_threshold) / 50)
            elif current_minus_di > current_plus_di and prev_minus_di <= prev_plus_di:
                signal = SignalType.BEARISH
                confidence = 0.6 + min(0.25, (current_adx - self.adx_threshold) / 50)
        
        if signal == SignalType.NEUTRAL:
            return None
        
        if vol_ratio > 1.3:
            confidence = min(0.9, confidence + 0.1)
        
        support, resistance = self.get_support_resistance(df)
        
        return ScanResult(
            symbol=symbol, index=index, timeframe=timeframe, strategy=self.name,
            signal=signal, confidence_score=confidence,
            indicators={"adx": current_adx, "plus_di": current_plus_di, "minus_di": current_minus_di},
            trend=self.get_trend(df), support=support, resistance=resistance, volume_ratio=vol_ratio
        )
