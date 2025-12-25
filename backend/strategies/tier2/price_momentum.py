"""Price Momentum Strategy - Tier 2"""

from typing import Optional
import pandas as pd
from strategies.base import BaseStrategy, ScanResult, SignalType, StrategyTier, StrategyRegistry
from core.scanner.indicator_utils import price_momentum, volume_ratio


@StrategyRegistry.register
class PriceMomentum(BaseStrategy):
    name = "Price Momentum"
    description = "6-month/52-week momentum based on rate of change"
    tier = StrategyTier.TIER_2
    min_bars_required = 130
    
    def scan(self, df: pd.DataFrame, symbol: str, index: str, timeframe: str) -> Optional[ScanResult]:
        if not self.validate_data(df):
            return None
        
        mom_6m = price_momentum(df['close'], 126).iloc[-1]  # ~6 months
        mom_3m = price_momentum(df['close'], 63).iloc[-1]   # ~3 months
        vol_ratio = volume_ratio(df['volume']).iloc[-1]
        
        signal = SignalType.NEUTRAL
        confidence = 0.0
        
        # Strong positive momentum
        if mom_6m > 20 and mom_3m > 10:
            signal = SignalType.BULLISH
            confidence = 0.6 + min(0.25, mom_6m / 100)
        elif mom_6m < -20 and mom_3m < -10:
            signal = SignalType.BEARISH
            confidence = 0.6 + min(0.25, abs(mom_6m) / 100)
        else:
            return None
        
        if vol_ratio > 1.2:
            confidence = min(0.85, confidence + 0.05)
        
        support, resistance = self.get_support_resistance(df)
        return ScanResult(
            symbol=symbol, index=index, timeframe=timeframe, strategy=self.name,
            signal=signal, confidence_score=confidence,
            indicators={"momentum_6m": mom_6m, "momentum_3m": mom_3m},
            trend=self.get_trend(df), support=support, resistance=resistance, volume_ratio=vol_ratio
        )
