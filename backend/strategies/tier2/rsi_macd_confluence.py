"""RSI + MACD Confluence Strategy - Tier 2"""

from typing import Optional
import pandas as pd
from strategies.base import BaseStrategy, ScanResult, SignalType, StrategyTier, StrategyRegistry
from core.scanner.indicator_utils import rsi, macd, volume_ratio


@StrategyRegistry.register
class RSIMACDConfluence(BaseStrategy):
    name = "RSI + MACD Confluence"
    description = "Combined RSI and MACD for high-probability signals"
    tier = StrategyTier.TIER_2
    min_bars_required = 35
    
    def scan(self, df: pd.DataFrame, symbol: str, index: str, timeframe: str) -> Optional[ScanResult]:
        if not self.validate_data(df):
            return None
        
        rsi_val = rsi(df['close']).iloc[-1]
        macd_line, signal_line, hist = macd(df['close'])
        curr_hist = hist.iloc[-1]
        prev_hist = hist.iloc[-2]
        vol_ratio = volume_ratio(df['volume']).iloc[-1]
        
        signal = SignalType.NEUTRAL
        confidence = 0.0
        
        # Bullish: RSI < 40 + MACD histogram turning positive
        if rsi_val < 40 and curr_hist > 0 and prev_hist <= 0:
            signal = SignalType.BULLISH
            confidence = 0.75
        elif rsi_val > 60 and curr_hist < 0 and prev_hist >= 0:
            signal = SignalType.BEARISH
            confidence = 0.75
        else:
            return None
        
        if vol_ratio > 1.3:
            confidence = min(0.9, confidence + 0.1)
        
        support, resistance = self.get_support_resistance(df)
        return ScanResult(
            symbol=symbol, index=index, timeframe=timeframe, strategy=self.name,
            signal=signal, confidence_score=confidence,
            indicators={"rsi": rsi_val, "macd_hist": curr_hist},
            trend=self.get_trend(df), support=support, resistance=resistance, volume_ratio=vol_ratio
        )
