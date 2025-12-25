"""OBV Divergence Strategy - Tier 3"""
from typing import Optional
import pandas as pd
from strategies.base import BaseStrategy, ScanResult, SignalType, StrategyTier, StrategyRegistry
from core.scanner.indicator_utils import obv, volume_ratio

@StrategyRegistry.register
class OBVDivergence(BaseStrategy):
    name = "OBV Divergence"
    description = "Detects divergence between price and On-Balance Volume"
    tier = StrategyTier.TIER_3
    min_bars_required = 30
    
    def scan(self, df: pd.DataFrame, symbol: str, index: str, timeframe: str) -> Optional[ScanResult]:
        if not self.validate_data(df):
            return None
        obv_vals = obv(df['close'], df['volume'])
        price_10d = df['close'].iloc[-1] - df['close'].iloc[-10]
        obv_10d = obv_vals.iloc[-1] - obv_vals.iloc[-10]
        vol_ratio = volume_ratio(df['volume']).iloc[-1]
        signal, confidence = SignalType.NEUTRAL, 0.0
        # Bullish divergence: price down, OBV up
        if price_10d < 0 and obv_10d > 0:
            signal, confidence = SignalType.BULLISH, 0.65
        elif price_10d > 0 and obv_10d < 0:
            signal, confidence = SignalType.BEARISH, 0.65
        else:
            return None
        support, resistance = self.get_support_resistance(df)
        return ScanResult(symbol=symbol, index=index, timeframe=timeframe, strategy=self.name,
            signal=signal, confidence_score=confidence, indicators={"obv_change": obv_10d, "price_change": price_10d},
            trend=self.get_trend(df), support=support, resistance=resistance, volume_ratio=vol_ratio)
