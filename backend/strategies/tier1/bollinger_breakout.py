"""Bollinger Bands Breakout Strategy - Tier 1"""

from typing import Optional
import pandas as pd
from strategies.base import BaseStrategy, ScanResult, SignalType, StrategyTier, StrategyRegistry
from core.scanner.indicator_utils import bollinger_bands, volume_ratio


@StrategyRegistry.register
class BollingerBreakout(BaseStrategy):
    """
    Bollinger Bands Breakout Strategy
    Signal when price breaks above/below bands with volume confirmation.
    """
    
    name = "Bollinger Bands Breakout"
    description = "Detects breakouts above upper or below lower Bollinger Bands"
    tier = StrategyTier.TIER_1
    min_bars_required = 30
    
    def __init__(self, period: int = 20, std_dev: float = 2.0):
        self.period = period
        self.std_dev = std_dev
    
    def scan(self, df: pd.DataFrame, symbol: str, index: str, timeframe: str) -> Optional[ScanResult]:
        if not self.validate_data(df):
            return None
        
        # Calculate Bollinger Bands
        middle, upper, lower = bollinger_bands(df['close'], self.period, self.std_dev)
        
        close = df['close'].iloc[-1]
        prev_close = df['close'].iloc[-2]
        upper_band = upper.iloc[-1]
        lower_band = lower.iloc[-1]
        middle_band = middle.iloc[-1]
        
        # Calculate band width (volatility)
        band_width = (upper_band - lower_band) / middle_band
        
        vol_ratio = volume_ratio(df['volume']).iloc[-1]
        
        signal = SignalType.NEUTRAL
        confidence = 0.0
        
        # Bullish breakout above upper band
        if close > upper_band and prev_close <= upper.iloc[-2]:
            signal = SignalType.BULLISH
            confidence = 0.65
            if vol_ratio > 1.5:
                confidence += 0.15
        # Bearish breakout below lower band
        elif close < lower_band and prev_close >= lower.iloc[-2]:
            signal = SignalType.BEARISH
            confidence = 0.65
            if vol_ratio > 1.5:
                confidence += 0.15
        # Mean reversion from bands
        elif close < lower_band:
            signal = SignalType.BULLISH
            confidence = 0.55 + min(0.2, (lower_band - close) / close * 10)
        elif close > upper_band:
            signal = SignalType.BEARISH
            confidence = 0.55 + min(0.2, (close - upper_band) / close * 10)
        else:
            return None
        
        support, resistance = self.get_support_resistance(df)
        
        return ScanResult(
            symbol=symbol,
            index=index,
            timeframe=timeframe,
            strategy=self.name,
            signal=signal,
            confidence_score=min(0.95, confidence),
            indicators={
                "upper_band": upper_band,
                "middle_band": middle_band,
                "lower_band": lower_band,
                "band_width": band_width * 100
            },
            trend=self.get_trend(df),
            support=support,
            resistance=resistance,
            volume_ratio=vol_ratio
        )
