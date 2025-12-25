"""ATR Volatility Breakout Strategy - Tier 3"""
from typing import Optional
import pandas as pd
from strategies.base import BaseStrategy, ScanResult, SignalType, StrategyTier, StrategyRegistry
from core.scanner.indicator_utils import atr, volume_ratio

@StrategyRegistry.register
class ATRVolatilityBreakout(BaseStrategy):
    name = "ATR-Based Volatility Breakout"
    description = "Breakout when price moves beyond ATR threshold"
    tier = StrategyTier.TIER_3
    min_bars_required = 25
    
    def scan(self, df: pd.DataFrame, symbol: str, index: str, timeframe: str) -> Optional[ScanResult]:
        if not self.validate_data(df):
            return None
        atr_val = atr(df['high'], df['low'], df['close']).iloc[-1]
        prev_close = df['close'].iloc[-2]
        curr_close = df['close'].iloc[-1]
        move = curr_close - prev_close
        vol_ratio = volume_ratio(df['volume']).iloc[-1]
        if abs(move) < atr_val * 1.5:
            return None
        signal = SignalType.BULLISH if move > 0 else SignalType.BEARISH
        confidence = 0.65 + min(0.2, (abs(move) / atr_val - 1.5) / 3)
        support, resistance = self.get_support_resistance(df)
        return ScanResult(symbol=symbol, index=index, timeframe=timeframe, strategy=self.name,
            signal=signal, confidence_score=confidence, indicators={"atr": atr_val, "move": move, "atr_multiple": abs(move)/atr_val},
            trend=self.get_trend(df), support=support, resistance=resistance, volume_ratio=vol_ratio)
