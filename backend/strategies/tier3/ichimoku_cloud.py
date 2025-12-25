"""Ichimoku Cloud Strategy - Tier 3"""
from typing import Optional
import pandas as pd
from strategies.base import BaseStrategy, ScanResult, SignalType, StrategyTier, StrategyRegistry
from core.scanner.indicator_utils import ichimoku, volume_ratio

@StrategyRegistry.register
class IchimokuCloud(BaseStrategy):
    name = "Ichimoku Cloud Trend"
    description = "Trend following using Ichimoku Cloud"
    tier = StrategyTier.TIER_3
    min_bars_required = 60
    
    def scan(self, df: pd.DataFrame, symbol: str, index: str, timeframe: str) -> Optional[ScanResult]:
        if not self.validate_data(df):
            return None
        tenkan, kijun, senkou_a, senkou_b, _ = ichimoku(df['high'], df['low'], df['close'])
        close = df['close'].iloc[-1]
        curr_tenkan, curr_kijun = tenkan.iloc[-1], kijun.iloc[-1]
        cloud_top = max(senkou_a.iloc[-1], senkou_b.iloc[-1]) if pd.notna(senkou_a.iloc[-1]) else 0
        cloud_bottom = min(senkou_a.iloc[-1], senkou_b.iloc[-1]) if pd.notna(senkou_a.iloc[-1]) else 0
        vol_ratio = volume_ratio(df['volume']).iloc[-1]
        signal, confidence = SignalType.NEUTRAL, 0.0
        # Price above cloud + TK cross
        if close > cloud_top and curr_tenkan > curr_kijun:
            signal, confidence = SignalType.BULLISH, 0.7
        elif close < cloud_bottom and curr_tenkan < curr_kijun:
            signal, confidence = SignalType.BEARISH, 0.7
        else:
            return None
        support, resistance = self.get_support_resistance(df)
        return ScanResult(symbol=symbol, index=index, timeframe=timeframe, strategy=self.name,
            signal=signal, confidence_score=confidence, indicators={"tenkan": curr_tenkan, "kijun": curr_kijun, "cloud_top": cloud_top},
            trend=self.get_trend(df), support=support, resistance=resistance, volume_ratio=vol_ratio)
