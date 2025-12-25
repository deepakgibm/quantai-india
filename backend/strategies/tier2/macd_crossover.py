"""MACD Bullish Crossover Strategy - Tier 2"""

from typing import Optional
import pandas as pd
from strategies.base import BaseStrategy, ScanResult, SignalType, StrategyTier, StrategyRegistry
from core.scanner.indicator_utils import macd, volume_ratio


@StrategyRegistry.register
class MACDCrossover(BaseStrategy):
    name = "MACD Bullish Crossover"
    description = "MACD line crossing signal line"
    tier = StrategyTier.TIER_2
    min_bars_required = 35
    
    def scan(self, df: pd.DataFrame, symbol: str, index: str, timeframe: str) -> Optional[ScanResult]:
        if not self.validate_data(df):
            return None
        
        macd_line, signal_line, _ = macd(df['close'])
        curr_macd, curr_signal = macd_line.iloc[-1], signal_line.iloc[-1]
        prev_macd, prev_signal = macd_line.iloc[-2], signal_line.iloc[-2]
        vol_ratio = volume_ratio(df['volume']).iloc[-1]
        
        signal = SignalType.NEUTRAL
        confidence = 0.0
        
        if curr_macd > curr_signal and prev_macd <= prev_signal:
            signal = SignalType.BULLISH
            confidence = 0.7
        elif curr_macd < curr_signal and prev_macd >= prev_signal:
            signal = SignalType.BEARISH
            confidence = 0.7
        else:
            return None
        
        if vol_ratio > 1.3:
            confidence = min(0.85, confidence + 0.1)
        
        support, resistance = self.get_support_resistance(df)
        return ScanResult(
            symbol=symbol, index=index, timeframe=timeframe, strategy=self.name,
            signal=signal, confidence_score=confidence,
            indicators={"macd": curr_macd, "signal": curr_signal},
            trend=self.get_trend(df), support=support, resistance=resistance, volume_ratio=vol_ratio
        )
