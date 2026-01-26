"""Flag and Pennant Continuation Pattern - Tier 3"""
from typing import Optional
import pandas as pd
from strategies.base import BaseStrategy, ScanResult, SignalType, StrategyTier, StrategyRegistry
from core.scanner.indicator_utils import volume_ratio

@StrategyRegistry.register
class FlagPennant(BaseStrategy):
    name = "Flag & Pennant Continuation"
    description = "Detects flag/pennant consolidation patterns"
    tier = StrategyTier.TIER_3
    min_bars_required = 30
    
    def scan(self, df: pd.DataFrame, symbol: str, index: str, timeframe: str) -> Optional[ScanResult]:
        if not self.validate_data(df):
            return None
        # Look for prior strong move followed by consolidation
        lookback = 20
        prior_move = df['close'].iloc[-lookback] - df['close'].iloc[-lookback-10]
        recent_range = df['high'].iloc[-10:].max() - df['low'].iloc[-10:].min()
        prior_range = df['high'].iloc[-lookback:-10].max() - df['low'].iloc[-lookback:-10].min()
        vol_ratio = volume_ratio(df['volume']).iloc[-1]
        signal, confidence = SignalType.NEUTRAL, 0.0
        # Consolidation: recent range << prior range after a strong move
        if recent_range < prior_range * 0.5 and abs(prior_move) > prior_range * 0.5:
            signal = SignalType.BULLISH if prior_move > 0 else SignalType.BEARISH
            confidence = 0.6
        else:
            return None
        support, resistance = self.get_support_resistance(df)
        return ScanResult(symbol=symbol, index=index, timeframe=timeframe, strategy=self.name,
            signal=signal, confidence_score=confidence, indicators={"prior_move": prior_move, "consolidation_ratio": recent_range/prior_range},
            trend=self.get_trend(df), support=support, resistance=resistance, volume_ratio=vol_ratio)
