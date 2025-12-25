"""RSI Mean Reversion Strategy - Tier 1"""

from typing import Optional
import pandas as pd
from strategies.base import BaseStrategy, ScanResult, SignalType, StrategyTier, StrategyRegistry
from core.scanner.indicator_utils import rsi, volume_ratio


@StrategyRegistry.register
class RSIMeanReversion(BaseStrategy):
    """
    RSI Mean Reversion Strategy
    Buy when RSI < 30 (oversold), Sell when RSI > 70 (overbought)
    """
    
    name = "RSI Mean Reversion"
    description = "Identifies oversold/overbought conditions using RSI for mean reversion trades"
    tier = StrategyTier.TIER_1
    min_bars_required = 30
    
    def __init__(self, rsi_period: int = 14, oversold: float = 30, overbought: float = 70):
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought
    
    def scan(self, df: pd.DataFrame, symbol: str, index: str, timeframe: str) -> Optional[ScanResult]:
        if not self.validate_data(df):
            return None
        
        # Calculate RSI
        rsi_values = rsi(df['close'], self.rsi_period)
        current_rsi = rsi_values.iloc[-1]
        prev_rsi = rsi_values.iloc[-2]
        
        # Calculate volume ratio
        vol_ratio = volume_ratio(df['volume']).iloc[-1]
        
        # Determine signal
        signal = SignalType.NEUTRAL
        confidence = 0.0
        
        if current_rsi < self.oversold:
            signal = SignalType.BULLISH
            # Higher confidence for lower RSI and rising
            confidence = min(0.9, 0.5 + (self.oversold - current_rsi) / 50)
            if current_rsi > prev_rsi:  # RSI turning up
                confidence += 0.1
        elif current_rsi > self.overbought:
            signal = SignalType.BEARISH
            confidence = min(0.9, 0.5 + (current_rsi - self.overbought) / 50)
            if current_rsi < prev_rsi:  # RSI turning down
                confidence += 0.1
        else:
            return None  # No signal
        
        # Volume confirmation
        if vol_ratio > 1.5:
            confidence = min(1.0, confidence + 0.1)
        
        support, resistance = self.get_support_resistance(df)
        
        return ScanResult(
            symbol=symbol,
            index=index,
            timeframe=timeframe,
            strategy=self.name,
            signal=signal,
            confidence_score=confidence,
            indicators={"rsi": current_rsi, "rsi_prev": prev_rsi},
            trend=self.get_trend(df),
            support=support,
            resistance=resistance,
            volume_ratio=vol_ratio
        )
