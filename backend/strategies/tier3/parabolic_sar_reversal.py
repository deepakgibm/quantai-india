"""Parabolic SAR Reversal Strategy - Tier 3"""
from typing import Optional
import pandas as pd
from strategies.base import BaseStrategy, ScanResult, SignalType, StrategyTier, StrategyRegistry
from core.scanner.indicator_utils import parabolic_sar, volume_ratio

@StrategyRegistry.register
class ParabolicSARReversal(BaseStrategy):
    name = "Parabolic SAR Reversal"
    description = "Trend reversal signals from Parabolic SAR"
    tier = StrategyTier.TIER_3
    min_bars_required = 25
    
    def scan(self, df: pd.DataFrame, symbol: str, index: str, timeframe: str) -> Optional[ScanResult]:
        if not self.validate_data(df):
            return None
        sar = parabolic_sar(df['high'], df['low'])
        close = df['close'].iloc[-1]
        prev_close = df['close'].iloc[-2]
        curr_sar = sar.iloc[-1]
        prev_sar = sar.iloc[-2]
        vol_ratio = volume_ratio(df['volume']).iloc[-1]
        signal, confidence = SignalType.NEUTRAL, 0.0
        # SAR flipped below price (bullish)
        if prev_close < prev_sar and close > curr_sar:
            signal, confidence = SignalType.BULLISH, 0.65
        elif prev_close > prev_sar and close < curr_sar:
            signal, confidence = SignalType.BEARISH, 0.65
        else:
            return None
        support, resistance = self.get_support_resistance(df)
        return ScanResult(symbol=symbol, index=index, timeframe=timeframe, strategy=self.name,
            signal=signal, confidence_score=confidence, indicators={"sar": curr_sar, "close": close},
            trend=self.get_trend(df), support=support, resistance=resistance, volume_ratio=vol_ratio)
