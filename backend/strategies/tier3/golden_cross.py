"""Golden Cross Strategy - Tier 3"""
from typing import Optional
import pandas as pd
from strategies.base import BaseStrategy, ScanResult, SignalType, StrategyTier, StrategyRegistry
from core.scanner.indicator_utils import sma, volume_ratio

@StrategyRegistry.register
class GoldenCross(BaseStrategy):
    name = "Moving Average Golden Cross"
    description = "50 SMA crossing above 200 SMA"
    tier = StrategyTier.TIER_3
    min_bars_required = 210
    
    def scan(self, df: pd.DataFrame, symbol: str, index: str, timeframe: str) -> Optional[ScanResult]:
        if not self.validate_data(df):
            return None
        sma50 = sma(df['close'], 50)
        sma200 = sma(df['close'], 200)
        curr_50, curr_200 = sma50.iloc[-1], sma200.iloc[-1]
        prev_50, prev_200 = sma50.iloc[-2], sma200.iloc[-2]
        vol_ratio = volume_ratio(df['volume']).iloc[-1]
        signal, confidence = SignalType.NEUTRAL, 0.0
        if curr_50 > curr_200 and prev_50 <= prev_200:
            signal, confidence = SignalType.BULLISH, 0.75
        elif curr_50 < curr_200 and prev_50 >= prev_200:
            signal, confidence = SignalType.BEARISH, 0.75
        else:
            return None
        support, resistance = self.get_support_resistance(df)
        return ScanResult(symbol=symbol, index=index, timeframe=timeframe, strategy=self.name,
            signal=signal, confidence_score=min(0.9, confidence), indicators={"sma_50": curr_50, "sma_200": curr_200},
            trend=self.get_trend(df), support=support, resistance=resistance, volume_ratio=vol_ratio)
