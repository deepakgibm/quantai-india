"""Donchian Mean Reversion Strategy - Tier 3"""
from typing import Optional
import pandas as pd
from strategies.base import BaseStrategy, ScanResult, SignalType, StrategyTier, StrategyRegistry
from core.scanner.indicator_utils import donchian_channels, volume_ratio

@StrategyRegistry.register
class DonchianMeanReversion(BaseStrategy):
    name = "Donchian Channel Mean Reversion"
    description = "Mean reversion from Donchian channel extremes"
    tier = StrategyTier.TIER_3
    min_bars_required = 25
    
    def scan(self, df: pd.DataFrame, symbol: str, index: str, timeframe: str) -> Optional[ScanResult]:
        if not self.validate_data(df):
            return None
        upper, middle, lower = donchian_channels(df['high'], df['low'])
        close = df['close'].iloc[-1]
        channel_width = upper.iloc[-1] - lower.iloc[-1]
        dist_from_lower = close - lower.iloc[-1]
        dist_from_upper = upper.iloc[-1] - close
        vol_ratio = volume_ratio(df['volume']).iloc[-1]
        signal, confidence = SignalType.NEUTRAL, 0.0
        if dist_from_lower < channel_width * 0.1:
            signal, confidence = SignalType.BULLISH, 0.6
        elif dist_from_upper < channel_width * 0.1:
            signal, confidence = SignalType.BEARISH, 0.6
        else:
            return None
        support, resistance = self.get_support_resistance(df)
        return ScanResult(symbol=symbol, index=index, timeframe=timeframe, strategy=self.name,
            signal=signal, confidence_score=confidence, indicators={"upper": upper.iloc[-1], "lower": lower.iloc[-1], "middle": middle.iloc[-1]},
            trend=self.get_trend(df), support=support, resistance=resistance, volume_ratio=vol_ratio)
