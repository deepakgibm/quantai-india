"""CCI Deviation Strategy - Tier 3"""
from typing import Optional
import pandas as pd
from strategies.base import BaseStrategy, ScanResult, SignalType, StrategyTier, StrategyRegistry
from core.scanner.indicator_utils import cci, volume_ratio

@StrategyRegistry.register
class CCIDeviation(BaseStrategy):
    name = "CCI Deviation"
    description = "CCI extreme deviation mean reversion"
    tier = StrategyTier.TIER_3
    min_bars_required = 25
    
    def scan(self, df: pd.DataFrame, symbol: str, index: str, timeframe: str) -> Optional[ScanResult]:
        if not self.validate_data(df):
            return None
        cci_val = cci(df['high'], df['low'], df['close']).iloc[-1]
        vol_ratio = volume_ratio(df['volume']).iloc[-1]
        signal, confidence = SignalType.NEUTRAL, 0.0
        if cci_val < -100:
            signal, confidence = SignalType.BULLISH, 0.6 + min(0.2, abs(cci_val + 100) / 200)
        elif cci_val > 100:
            signal, confidence = SignalType.BEARISH, 0.6 + min(0.2, (cci_val - 100) / 200)
        else:
            return None
        support, resistance = self.get_support_resistance(df)
        return ScanResult(symbol=symbol, index=index, timeframe=timeframe, strategy=self.name,
            signal=signal, confidence_score=confidence, indicators={"cci": cci_val},
            trend=self.get_trend(df), support=support, resistance=resistance, volume_ratio=vol_ratio)
