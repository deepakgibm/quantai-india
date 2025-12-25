"""Volume Surge Strategy - Tier 3"""
from typing import Optional
import pandas as pd
from strategies.base import BaseStrategy, ScanResult, SignalType, StrategyTier, StrategyRegistry
from core.scanner.indicator_utils import volume_ratio

@StrategyRegistry.register
class VolumeSurge(BaseStrategy):
    name = "Volume Surge Accumulation"
    description = "Detects unusual volume spikes indicating accumulation/distribution"
    tier = StrategyTier.TIER_3
    min_bars_required = 25
    
    def scan(self, df: pd.DataFrame, symbol: str, index: str, timeframe: str) -> Optional[ScanResult]:
        if not self.validate_data(df):
            return None
        vol_ratio = volume_ratio(df['volume']).iloc[-1]
        price_change = (df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2] * 100
        if vol_ratio < 2.0:
            return None
        signal = SignalType.BULLISH if price_change > 0 else SignalType.BEARISH
        confidence = 0.6 + min(0.3, (vol_ratio - 2) / 5)
        support, resistance = self.get_support_resistance(df)
        return ScanResult(symbol=symbol, index=index, timeframe=timeframe, strategy=self.name,
            signal=signal, confidence_score=confidence, indicators={"volume_ratio": vol_ratio, "price_change": price_change},
            trend=self.get_trend(df), support=support, resistance=resistance, volume_ratio=vol_ratio)
