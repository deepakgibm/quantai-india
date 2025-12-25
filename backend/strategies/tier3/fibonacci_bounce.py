"""Fibonacci Bounce Strategy - Tier 3"""
from typing import Optional
import pandas as pd
from strategies.base import BaseStrategy, ScanResult, SignalType, StrategyTier, StrategyRegistry
from core.scanner.indicator_utils import fibonacci_levels, volume_ratio

@StrategyRegistry.register
class FibonacciBounce(BaseStrategy):
    name = "Fibonacci Retracement Bounce"
    description = "Price bouncing at Fibonacci retracement levels"
    tier = StrategyTier.TIER_3
    min_bars_required = 50
    
    def scan(self, df: pd.DataFrame, symbol: str, index: str, timeframe: str) -> Optional[ScanResult]:
        if not self.validate_data(df):
            return None
        high = df['high'].max()
        low = df['low'].min()
        close = df['close'].iloc[-1]
        fib = fibonacci_levels(high, low)
        vol_ratio = volume_ratio(df['volume']).iloc[-1]
        signal, confidence, fib_level = SignalType.NEUTRAL, 0.0, 0.0
        tolerance = (high - low) * 0.02
        for level, price in fib.items():
            if level in [0.382, 0.5, 0.618] and abs(close - price) < tolerance:
                signal = SignalType.BULLISH if close < (high + low) / 2 else SignalType.BEARISH
                confidence = 0.65
                fib_level = level
                break
        if signal == SignalType.NEUTRAL:
            return None
        support, resistance = self.get_support_resistance(df)
        return ScanResult(symbol=symbol, index=index, timeframe=timeframe, strategy=self.name,
            signal=signal, confidence_score=confidence, indicators={"fib_level": fib_level, "fib_price": fib[fib_level]},
            trend=self.get_trend(df), support=support, resistance=resistance, volume_ratio=vol_ratio)
