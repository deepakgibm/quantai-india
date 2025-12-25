"""Williams %R Mean Reversion Strategy - Tier 1"""

from typing import Optional
import pandas as pd
from strategies.base import BaseStrategy, ScanResult, SignalType, StrategyTier, StrategyRegistry
from core.scanner.indicator_utils import williams_r, volume_ratio


@StrategyRegistry.register
class WilliamsR(BaseStrategy):
    """
    Williams %R Mean Reversion Strategy
    Buy when W%R < -80 (oversold), Sell when W%R > -20 (overbought)
    """
    
    name = "Williams %R Mean Reversion"
    description = "Identifies overbought/oversold using Williams %R oscillator"
    tier = StrategyTier.TIER_1
    min_bars_required = 20
    
    def __init__(self, period: int = 14, oversold: float = -80, overbought: float = -20):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
    
    def scan(self, df: pd.DataFrame, symbol: str, index: str, timeframe: str) -> Optional[ScanResult]:
        if not self.validate_data(df):
            return None
        
        wr = williams_r(df['high'], df['low'], df['close'], self.period)
        current_wr = wr.iloc[-1]
        prev_wr = wr.iloc[-2]
        
        vol_ratio = volume_ratio(df['volume']).iloc[-1]
        
        signal = SignalType.NEUTRAL
        confidence = 0.0
        
        if current_wr < self.oversold:
            signal = SignalType.BULLISH
            confidence = 0.6 + min(0.25, (self.oversold - current_wr) / 40)
            if current_wr > prev_wr:  # Turning up
                confidence += 0.1
        elif current_wr > self.overbought:
            signal = SignalType.BEARISH
            confidence = 0.6 + min(0.25, (current_wr - self.overbought) / 40)
            if current_wr < prev_wr:  # Turning down
                confidence += 0.1
        else:
            return None
        
        if vol_ratio > 1.3:
            confidence = min(0.95, confidence + 0.05)
        
        support, resistance = self.get_support_resistance(df)
        
        return ScanResult(
            symbol=symbol,
            index=index,
            timeframe=timeframe,
            strategy=self.name,
            signal=signal,
            confidence_score=confidence,
            indicators={"williams_r": current_wr, "williams_r_prev": prev_wr},
            trend=self.get_trend(df),
            support=support,
            resistance=resistance,
            volume_ratio=vol_ratio
        )
