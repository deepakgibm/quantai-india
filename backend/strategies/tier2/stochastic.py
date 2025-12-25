"""Stochastic Oscillator Strategy - Tier 2"""

from typing import Optional
import pandas as pd
from strategies.base import BaseStrategy, ScanResult, SignalType, StrategyTier, StrategyRegistry
from core.scanner.indicator_utils import stochastic, volume_ratio


@StrategyRegistry.register
class StochasticOscillator(BaseStrategy):
    name = "Stochastic Oscillator"
    description = "Identifies overbought/oversold using Stochastic %K/%D crossovers"
    tier = StrategyTier.TIER_2
    min_bars_required = 20
    
    def scan(self, df: pd.DataFrame, symbol: str, index: str, timeframe: str) -> Optional[ScanResult]:
        if not self.validate_data(df):
            return None
        
        k, d = stochastic(df['high'], df['low'], df['close'])
        curr_k, curr_d = k.iloc[-1], d.iloc[-1]
        prev_k, prev_d = k.iloc[-2], d.iloc[-2]
        vol_ratio = volume_ratio(df['volume']).iloc[-1]
        
        signal = SignalType.NEUTRAL
        confidence = 0.0
        
        # Bullish: %K crosses above %D in oversold zone
        if curr_k < 20 and curr_k > curr_d and prev_k <= prev_d:
            signal = SignalType.BULLISH
            confidence = 0.65
        elif curr_k > 80 and curr_k < curr_d and prev_k >= prev_d:
            signal = SignalType.BEARISH
            confidence = 0.65
        else:
            return None
        
        if vol_ratio > 1.3:
            confidence = min(0.9, confidence + 0.1)
        
        support, resistance = self.get_support_resistance(df)
        return ScanResult(
            symbol=symbol, index=index, timeframe=timeframe, strategy=self.name,
            signal=signal, confidence_score=confidence,
            indicators={"stoch_k": curr_k, "stoch_d": curr_d},
            trend=self.get_trend(df), support=support, resistance=resistance, volume_ratio=vol_ratio
        )
