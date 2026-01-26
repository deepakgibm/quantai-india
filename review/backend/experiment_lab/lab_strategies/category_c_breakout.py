"""
Category C - Breakout + Filter Strategies (19-25)
Breakout strategies with additional confirmation filters.
"""

import pandas as pd
from typing import List
from .base import (
    ExperimentStrategy, StrategyInfo, SignalResult, SignalType,
    StrategyCategory, register_strategy
)
from ..indicators.technical import TechnicalIndicators as TI


@register_strategy
class BollingerBreakout_ADX(ExperimentStrategy):
    """Strategy 19: Bollinger Breakout + ADX"""
    
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(
            id=19, name="Bollinger Breakout + ADX",
            category=StrategyCategory.CATEGORY_C,
            description="Bollinger breakout confirmed by strong trend (ADX > 25)",
            indicators_used=["Bollinger Bands", "ADX"], min_bars_required=30
        )
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        upper, middle, lower = TI.bollinger_bands(df['close'], 20, 2.0)
        adx, _, _ = TI.adx(df, 14)
        atr = TI.atr(df, 14)
        
        for i in range(30, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            if adx.iloc[i] > 25:
                if df['close'].iloc[i-1] <= upper.iloc[i-1] and price > upper.iloc[i]:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price,
                        confidence=0.75, stop_loss=middle.iloc[i], take_profit=price + 2*atr.iloc[i],
                        indicators={"bb_upper": upper.iloc[i], "adx": adx.iloc[i]},
                        reason="Bollinger breakout + strong ADX"))
                elif df['close'].iloc[i-1] >= lower.iloc[i-1] and price < lower.iloc[i]:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price,
                        confidence=0.75, stop_loss=middle.iloc[i], take_profit=price - 2*atr.iloc[i],
                        indicators={"bb_lower": lower.iloc[i], "adx": adx.iloc[i]},
                        reason="Bollinger breakdown + strong ADX"))
        return signals


@register_strategy
class BollingerBreakout_RSI(ExperimentStrategy):
    """Strategy 20: Bollinger Breakout + RSI Filter"""
    
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(
            id=20, name="Bollinger Breakout + RSI",
            category=StrategyCategory.CATEGORY_C,
            description="Bollinger breakout with RSI momentum confirmation",
            indicators_used=["Bollinger Bands", "RSI"], min_bars_required=30
        )
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        upper, middle, lower = TI.bollinger_bands(df['close'], 20, 2.0)
        rsi = TI.rsi(df['close'], 14)
        atr = TI.atr(df, 14)
        
        for i in range(30, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            if price > upper.iloc[i] and 50 < rsi.iloc[i] < 75:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price,
                    confidence=0.7, stop_loss=middle.iloc[i], take_profit=price + 2*atr.iloc[i],
                    indicators={"rsi": rsi.iloc[i]}, reason="Bollinger breakout + RSI confirmation"))
            elif price < lower.iloc[i] and 25 < rsi.iloc[i] < 50:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price,
                    confidence=0.7, stop_loss=middle.iloc[i], take_profit=price - 2*atr.iloc[i],
                    indicators={"rsi": rsi.iloc[i]}, reason="Bollinger breakdown + RSI confirmation"))
        return signals


@register_strategy
class DonchianBreakout_ADX(ExperimentStrategy):
    """Strategy 21: Donchian Breakout + ADX"""
    
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(
            id=21, name="Donchian Breakout + ADX",
            category=StrategyCategory.CATEGORY_C,
            description="Donchian channel breakout with ADX trend filter",
            indicators_used=["Donchian Channel", "ADX"], min_bars_required=30
        )
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        upper, middle, lower = TI.donchian_channel(df, 20)
        adx, plus_di, minus_di = TI.adx(df, 14)
        atr = TI.atr(df, 14)
        
        for i in range(30, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            if adx.iloc[i] > 20:
                if price > upper.iloc[i-1] and plus_di.iloc[i] > minus_di.iloc[i]:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price,
                        confidence=0.75, stop_loss=middle.iloc[i], take_profit=price + 2.5*atr.iloc[i],
                        indicators={"adx": adx.iloc[i]}, reason="Donchian breakout + ADX confirmation"))
                elif price < lower.iloc[i-1] and minus_di.iloc[i] > plus_di.iloc[i]:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price,
                        confidence=0.75, stop_loss=middle.iloc[i], take_profit=price - 2.5*atr.iloc[i],
                        indicators={"adx": adx.iloc[i]}, reason="Donchian breakdown + ADX confirmation"))
        return signals


@register_strategy
class DonchianBreakout_ATR(ExperimentStrategy):
    """Strategy 22: Donchian Breakout + ATR Filter"""
    
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(
            id=22, name="Donchian Breakout + ATR",
            category=StrategyCategory.CATEGORY_C,
            description="Donchian breakout with volatility expansion filter",
            indicators_used=["Donchian Channel", "ATR"], min_bars_required=30
        )
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        upper, middle, lower = TI.donchian_channel(df, 20)
        atr = TI.atr(df, 14)
        atr_sma = TI.sma(atr, 20)
        
        for i in range(30, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            if atr.iloc[i] > atr_sma.iloc[i] * 1.2:  # Volatility expansion
                if price > upper.iloc[i-1]:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price,
                        confidence=0.72, stop_loss=price - 1.5*atr.iloc[i], take_profit=price + 2.5*atr.iloc[i],
                        indicators={"atr": atr.iloc[i]}, reason="Donchian breakout + ATR expansion"))
                elif price < lower.iloc[i-1]:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price,
                        confidence=0.72, stop_loss=price + 1.5*atr.iloc[i], take_profit=price - 2.5*atr.iloc[i],
                        indicators={"atr": atr.iloc[i]}, reason="Donchian breakdown + ATR expansion"))
        return signals


@register_strategy
class ATRBreakout_Volume(ExperimentStrategy):
    """Strategy 23: ATR Breakout + Volume Confirmation"""
    
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(
            id=23, name="ATR Breakout + Volume",
            category=StrategyCategory.CATEGORY_C,
            description="ATR volatility breakout confirmed by volume surge",
            indicators_used=["ATR", "Volume"], min_bars_required=25
        )
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        atr = TI.atr(df, 14)
        vol_ratio = TI.volume_ratio(df, 20)
        
        for i in range(25, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            price_change = price - df['close'].iloc[i-1]
            if abs(price_change) > 1.5 * atr.iloc[i-1] and vol_ratio.iloc[i] > 1.5:
                if price_change > 0:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price,
                        confidence=0.75, stop_loss=price - atr.iloc[i], take_profit=price + 2*atr.iloc[i],
                        indicators={"atr": atr.iloc[i], "vol_ratio": vol_ratio.iloc[i]},
                        reason="ATR breakout + volume confirmation"))
                else:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price,
                        confidence=0.75, stop_loss=price + atr.iloc[i], take_profit=price - 2*atr.iloc[i],
                        indicators={"atr": atr.iloc[i], "vol_ratio": vol_ratio.iloc[i]},
                        reason="ATR breakdown + volume confirmation"))
        return signals


@register_strategy
class HighLowBreakout_Trend(ExperimentStrategy):
    """Strategy 24: High-Low Breakout + Trend Filter"""
    
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(
            id=24, name="High-Low Breakout + Trend",
            category=StrategyCategory.CATEGORY_C,
            description="N-period high/low breakout with EMA trend filter",
            indicators_used=["High/Low", "EMA"], min_bars_required=55
        )
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        high_20 = df['high'].rolling(20).max()
        low_20 = df['low'].rolling(20).min()
        ema20 = TI.ema(df['close'], 20)
        ema50 = TI.ema(df['close'], 50)
        atr = TI.atr(df, 14)
        
        for i in range(55, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            # Bullish trend + breakout
            if ema20.iloc[i] > ema50.iloc[i] and price > high_20.iloc[i-1]:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price,
                    confidence=0.72, stop_loss=ema20.iloc[i], take_profit=price + 2.5*atr.iloc[i],
                    indicators={"high_20": high_20.iloc[i-1]}, reason="High breakout in uptrend"))
            elif ema20.iloc[i] < ema50.iloc[i] and price < low_20.iloc[i-1]:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price,
                    confidence=0.72, stop_loss=ema20.iloc[i], take_profit=price - 2.5*atr.iloc[i],
                    indicators={"low_20": low_20.iloc[i-1]}, reason="Low breakdown in downtrend"))
        return signals


@register_strategy
class RangeExpansion_Momentum(ExperimentStrategy):
    """Strategy 25: Price Range Expansion + Momentum"""
    
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(
            id=25, name="Range Expansion + Momentum",
            category=StrategyCategory.CATEGORY_C,
            description="Trade when daily range expands significantly with momentum",
            indicators_used=["Range", "ROC"], min_bars_required=25
        )
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        daily_range = df['high'] - df['low']
        avg_range = daily_range.rolling(20).mean()
        roc = TI.roc(df['close'], 5)
        atr = TI.atr(df, 14)
        
        for i in range(25, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            if daily_range.iloc[i] > avg_range.iloc[i] * 1.5:  # Range expansion
                if roc.iloc[i] > 1:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price,
                        confidence=0.68, stop_loss=price - 1.5*atr.iloc[i], take_profit=price + 2*atr.iloc[i],
                        indicators={"range_ratio": daily_range.iloc[i]/avg_range.iloc[i], "roc": roc.iloc[i]},
                        reason="Range expansion + positive momentum"))
                elif roc.iloc[i] < -1:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price,
                        confidence=0.68, stop_loss=price + 1.5*atr.iloc[i], take_profit=price - 2*atr.iloc[i],
                        indicators={"range_ratio": daily_range.iloc[i]/avg_range.iloc[i], "roc": roc.iloc[i]},
                        reason="Range expansion + negative momentum"))
        return signals


__all__ = ['BollingerBreakout_ADX', 'BollingerBreakout_RSI', 'DonchianBreakout_ADX',
           'DonchianBreakout_ATR', 'ATRBreakout_Volume', 'HighLowBreakout_Trend', 'RangeExpansion_Momentum']
