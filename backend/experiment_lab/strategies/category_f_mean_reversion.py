"""
Category F - Mean Reversion Strategies (41-46)
Counter-trend strategies that trade reversals to the mean.
"""

import pandas as pd
import numpy as np
from typing import List
from .base import (
    ExperimentStrategy, StrategyInfo, SignalResult, SignalType,
    StrategyCategory, register_strategy
)
from ..indicators.technical import TechnicalIndicators as TI


@register_strategy
class BollingerMeanReversion_RSI(ExperimentStrategy):
    """Strategy 41: Bollinger Mean Reversion + RSI"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=41, name="Bollinger Mean Reversion + RSI", category=StrategyCategory.CATEGORY_F,
            description="Bollinger band touch with RSI extreme for mean reversion",
            indicators_used=["Bollinger Bands", "RSI"], min_bars_required=25)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        upper, middle, lower = TI.bollinger_bands(df['close'], 20, 2.0)
        rsi = TI.rsi(df['close'], 14)
        atr = TI.atr(df, 14)
        for i in range(25, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            if price <= lower.iloc[i] and rsi.iloc[i] < 30:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.72,
                    stop_loss=lower.iloc[i] - atr.iloc[i], take_profit=middle.iloc[i],
                    indicators={"rsi": rsi.iloc[i]}, reason="BB lower + RSI oversold mean reversion"))
            elif price >= upper.iloc[i] and rsi.iloc[i] > 70:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.72,
                    stop_loss=upper.iloc[i] + atr.iloc[i], take_profit=middle.iloc[i],
                    indicators={"rsi": rsi.iloc[i]}, reason="BB upper + RSI overbought mean reversion"))
        return signals


@register_strategy
class DonchianMeanReversion_RSI(ExperimentStrategy):
    """Strategy 42: Donchian Mean Reversion + RSI"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=42, name="Donchian Mean Reversion + RSI", category=StrategyCategory.CATEGORY_F,
            description="Trade reversals at Donchian channel extremes with RSI",
            indicators_used=["Donchian Channel", "RSI"], min_bars_required=25)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        upper, middle, lower = TI.donchian_channel(df, 20)
        rsi = TI.rsi(df['close'], 14)
        atr = TI.atr(df, 14)
        for i in range(25, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            if price <= lower.iloc[i] * 1.01 and rsi.iloc[i] < 35:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.7,
                    stop_loss=lower.iloc[i] * 0.98, take_profit=middle.iloc[i],
                    indicators={"rsi": rsi.iloc[i]}, reason="Donchian lower + RSI mean reversion"))
            elif price >= upper.iloc[i] * 0.99 and rsi.iloc[i] > 65:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.7,
                    stop_loss=upper.iloc[i] * 1.02, take_profit=middle.iloc[i],
                    indicators={"rsi": rsi.iloc[i]}, reason="Donchian upper + RSI mean reversion"))
        return signals


@register_strategy
class WilliamsR_RSI(ExperimentStrategy):
    """Strategy 43: Williams %R + RSI"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=43, name="Williams %R + RSI", category=StrategyCategory.CATEGORY_F,
            description="Dual oscillator extreme for mean reversion",
            indicators_used=["Williams %R", "RSI"], min_bars_required=25)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        williams = TI.williams_r(df, 14)
        rsi = TI.rsi(df['close'], 14)
        atr = TI.atr(df, 14)
        for i in range(25, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            if williams.iloc[i] < -80 and rsi.iloc[i] < 30:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.75,
                    stop_loss=price - 2*atr.iloc[i], take_profit=price + 2*atr.iloc[i],
                    indicators={"williams_r": williams.iloc[i], "rsi": rsi.iloc[i]},
                    reason="Williams + RSI both oversold"))
            elif williams.iloc[i] > -20 and rsi.iloc[i] > 70:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.75,
                    stop_loss=price + 2*atr.iloc[i], take_profit=price - 2*atr.iloc[i],
                    indicators={"williams_r": williams.iloc[i], "rsi": rsi.iloc[i]},
                    reason="Williams + RSI both overbought"))
        return signals


@register_strategy
class CCIDeviation_RSI(ExperimentStrategy):
    """Strategy 44: CCI Deviation + RSI"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=44, name="CCI Deviation + RSI", category=StrategyCategory.CATEGORY_F,
            description="CCI extreme deviation with RSI confirmation",
            indicators_used=["CCI", "RSI"], min_bars_required=25)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        cci = TI.cci(df, 20)
        rsi = TI.rsi(df['close'], 14)
        atr = TI.atr(df, 14)
        for i in range(25, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            if cci.iloc[i] < -150 and rsi.iloc[i] < 35:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.72,
                    stop_loss=price - 2*atr.iloc[i], take_profit=price + 2*atr.iloc[i],
                    indicators={"cci": cci.iloc[i], "rsi": rsi.iloc[i]},
                    reason="CCI extreme oversold + RSI confirmation"))
            elif cci.iloc[i] > 150 and rsi.iloc[i] > 65:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.72,
                    stop_loss=price + 2*atr.iloc[i], take_profit=price - 2*atr.iloc[i],
                    indicators={"cci": cci.iloc[i], "rsi": rsi.iloc[i]},
                    reason="CCI extreme overbought + RSI confirmation"))
        return signals


@register_strategy
class RSI_VWAPDeviation(ExperimentStrategy):
    """Strategy 45: RSI + VWAP Deviation"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=45, name="RSI + VWAP Deviation", category=StrategyCategory.CATEGORY_F,
            description="Trade deviation from VWAP with RSI confirmation",
            indicators_used=["RSI", "VWAP"], min_bars_required=25)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        rsi = TI.rsi(df['close'], 14)
        vwap = TI.vwap(df)
        atr = TI.atr(df, 14)
        for i in range(25, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            vwap_dev = (price - vwap.iloc[i]) / vwap.iloc[i] * 100
            if vwap_dev < -2 and rsi.iloc[i] < 35:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.7,
                    stop_loss=price - 1.5*atr.iloc[i], take_profit=vwap.iloc[i],
                    indicators={"vwap_dev": vwap_dev, "rsi": rsi.iloc[i]},
                    reason="Below VWAP + RSI oversold"))
            elif vwap_dev > 2 and rsi.iloc[i] > 65:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.7,
                    stop_loss=price + 1.5*atr.iloc[i], take_profit=vwap.iloc[i],
                    indicators={"vwap_dev": vwap_dev, "rsi": rsi.iloc[i]},
                    reason="Above VWAP + RSI overbought"))
        return signals


@register_strategy
class ATRCompression_MeanReversion(ExperimentStrategy):
    """Strategy 46: ATR Compression + Mean Reversion"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=46, name="ATR Compression Mean Reversion", category=StrategyCategory.CATEGORY_F,
            description="Low volatility compression followed by mean reversion setup",
            indicators_used=["ATR", "Bollinger Bands"], min_bars_required=30)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        atr = TI.atr(df, 14)
        atr_sma = TI.sma(atr, 20)
        upper, middle, lower = TI.bollinger_bands(df['close'], 20, 2.0)
        for i in range(30, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            # Volatility compression (ATR < 0.7x average)
            if atr.iloc[i] < atr_sma.iloc[i] * 0.7:
                if price <= lower.iloc[i]:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.68,
                        stop_loss=lower.iloc[i] - atr.iloc[i], take_profit=middle.iloc[i],
                        indicators={"atr_ratio": atr.iloc[i]/atr_sma.iloc[i]},
                        reason="ATR compression + lower BB mean reversion"))
                elif price >= upper.iloc[i]:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.68,
                        stop_loss=upper.iloc[i] + atr.iloc[i], take_profit=middle.iloc[i],
                        indicators={"atr_ratio": atr.iloc[i]/atr_sma.iloc[i]},
                        reason="ATR compression + upper BB mean reversion"))
        return signals


__all__ = ['BollingerMeanReversion_RSI', 'DonchianMeanReversion_RSI', 'WilliamsR_RSI',
           'CCIDeviation_RSI', 'RSI_VWAPDeviation', 'ATRCompression_MeanReversion']
