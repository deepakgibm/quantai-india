"""
Category E - Volume-Confirmed Strategies (35-40)
Strategies that require volume confirmation for entries.
"""

import pandas as pd
from typing import List
from .base import (
    ExperimentStrategy, StrategyInfo, SignalResult, SignalType,
    StrategyCategory, register_strategy
)
from ..indicators.technical import TechnicalIndicators as TI


@register_strategy
class RSI_VolumeSurge(ExperimentStrategy):
    """Strategy 35: RSI + Volume Surge"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=35, name="RSI + Volume Surge", category=StrategyCategory.CATEGORY_E,
            description="RSI extremes confirmed by volume > 1.5x average",
            indicators_used=["RSI", "Volume"], min_bars_required=25)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        rsi = TI.rsi(df['close'], 14)
        vol_ratio = TI.volume_ratio(df, 20)
        atr = TI.atr(df, 14)
        for i in range(25, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            if rsi.iloc[i] < 35 and vol_ratio.iloc[i] > 1.5:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.75,
                    stop_loss=price - 2*atr.iloc[i], take_profit=price + 2.5*atr.iloc[i],
                    indicators={"rsi": rsi.iloc[i], "vol_ratio": vol_ratio.iloc[i]},
                    reason="RSI oversold + volume surge"))
            elif rsi.iloc[i] > 65 and vol_ratio.iloc[i] > 1.5:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.75,
                    stop_loss=price + 2*atr.iloc[i], take_profit=price - 2.5*atr.iloc[i],
                    indicators={"rsi": rsi.iloc[i], "vol_ratio": vol_ratio.iloc[i]},
                    reason="RSI overbought + volume surge"))
        return signals


@register_strategy
class MACD_OBV(ExperimentStrategy):
    """Strategy 36: MACD + OBV"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=36, name="MACD + OBV", category=StrategyCategory.CATEGORY_E,
            description="MACD crossover confirmed by OBV trend",
            indicators_used=["MACD", "OBV"], min_bars_required=35)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        macd_line, signal_line, _ = TI.macd(df['close'])
        obv = TI.obv(df)
        obv_sma = TI.sma(obv, 20)
        atr = TI.atr(df, 14)
        for i in range(35, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            if macd_line.iloc[i-1] <= signal_line.iloc[i-1] and macd_line.iloc[i] > signal_line.iloc[i] and obv.iloc[i] > obv_sma.iloc[i]:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.72,
                    stop_loss=price - 2*atr.iloc[i], take_profit=price + 2.5*atr.iloc[i],
                    indicators={"macd": macd_line.iloc[i]}, reason="MACD bullish + OBV accumulation"))
            elif macd_line.iloc[i-1] >= signal_line.iloc[i-1] and macd_line.iloc[i] < signal_line.iloc[i] and obv.iloc[i] < obv_sma.iloc[i]:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.72,
                    stop_loss=price + 2*atr.iloc[i], take_profit=price - 2.5*atr.iloc[i],
                    indicators={"macd": macd_line.iloc[i]}, reason="MACD bearish + OBV distribution"))
        return signals


@register_strategy
class Breakout_VolumeExpansion(ExperimentStrategy):
    """Strategy 37: Breakout + Volume Expansion"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=37, name="Breakout + Volume Expansion", category=StrategyCategory.CATEGORY_E,
            description="Price breakout with volume > 2x average",
            indicators_used=["Price", "Volume"], min_bars_required=25)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        high_20 = df['high'].rolling(20).max()
        low_20 = df['low'].rolling(20).min()
        vol_ratio = TI.volume_ratio(df, 20)
        atr = TI.atr(df, 14)
        for i in range(25, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            if price > high_20.iloc[i-1] and vol_ratio.iloc[i] > 2.0:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.78,
                    stop_loss=high_20.iloc[i-1] * 0.98, take_profit=price + 2.5*atr.iloc[i],
                    indicators={"vol_ratio": vol_ratio.iloc[i]}, reason="Breakout + 2x volume"))
            elif price < low_20.iloc[i-1] and vol_ratio.iloc[i] > 2.0:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.78,
                    stop_loss=low_20.iloc[i-1] * 1.02, take_profit=price - 2.5*atr.iloc[i],
                    indicators={"vol_ratio": vol_ratio.iloc[i]}, reason="Breakdown + 2x volume"))
        return signals


@register_strategy  
class DonchianBreakout_OBV(ExperimentStrategy):
    """Strategy 38: Donchian Breakout + OBV"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=38, name="Donchian Breakout + OBV", category=StrategyCategory.CATEGORY_E,
            description="Donchian channel breakout with OBV trend confirmation",
            indicators_used=["Donchian", "OBV"], min_bars_required=30)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        upper, middle, lower = TI.donchian_channel(df, 20)
        obv = TI.obv(df)
        obv_sma = TI.sma(obv, 20)
        atr = TI.atr(df, 14)
        for i in range(30, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            if price > upper.iloc[i-1] and obv.iloc[i] > obv_sma.iloc[i]:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.75,
                    stop_loss=middle.iloc[i], take_profit=price + 2.5*atr.iloc[i],
                    indicators={}, reason="Donchian breakout + OBV bullish"))
            elif price < lower.iloc[i-1] and obv.iloc[i] < obv_sma.iloc[i]:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.75,
                    stop_loss=middle.iloc[i], take_profit=price - 2.5*atr.iloc[i],
                    indicators={}, reason="Donchian breakdown + OBV bearish"))
        return signals


@register_strategy
class PriceTrend_AccumulationVolume(ExperimentStrategy):
    """Strategy 39: Price Trend + Accumulation Volume"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=39, name="Price Trend + Accumulation", category=StrategyCategory.CATEGORY_E,
            description="EMA trend with sustained volume accumulation",
            indicators_used=["EMA", "Volume"], min_bars_required=30)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        ema20 = TI.ema(df['close'], 20)
        vol_sma = TI.volume_sma(df, 20)
        atr = TI.atr(df, 14)
        for i in range(30, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            # 3-day average volume above SMA
            recent_vol = df['volume'].iloc[i-2:i+1].mean()
            if price > ema20.iloc[i] and recent_vol > vol_sma.iloc[i] * 1.3:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.7,
                    stop_loss=ema20.iloc[i], take_profit=price + 2.5*atr.iloc[i],
                    indicators={"vol_ratio": recent_vol/vol_sma.iloc[i]}, reason="Uptrend + accumulation"))
            elif price < ema20.iloc[i] and recent_vol > vol_sma.iloc[i] * 1.3:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.7,
                    stop_loss=ema20.iloc[i], take_profit=price - 2.5*atr.iloc[i],
                    indicators={"vol_ratio": recent_vol/vol_sma.iloc[i]}, reason="Downtrend + distribution"))
        return signals


@register_strategy
class VolumeSpike_ATRBreakout(ExperimentStrategy):
    """Strategy 40: Volume Spike + ATR Breakout"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=40, name="Volume Spike + ATR Breakout", category=StrategyCategory.CATEGORY_E,
            description="Extreme volume spike with ATR-based price move",
            indicators_used=["Volume", "ATR"], min_bars_required=25)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        vol_ratio = TI.volume_ratio(df, 20)
        atr = TI.atr(df, 14)
        for i in range(25, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            price_change = price - df['close'].iloc[i-1]
            if vol_ratio.iloc[i] > 2.5 and abs(price_change) > atr.iloc[i-1]:
                if price_change > 0:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.8,
                        stop_loss=price - atr.iloc[i], take_profit=price + 2*atr.iloc[i],
                        indicators={"vol_ratio": vol_ratio.iloc[i], "atr": atr.iloc[i]},
                        reason="Volume spike + ATR breakout bullish"))
                else:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.8,
                        stop_loss=price + atr.iloc[i], take_profit=price - 2*atr.iloc[i],
                        indicators={"vol_ratio": vol_ratio.iloc[i], "atr": atr.iloc[i]},
                        reason="Volume spike + ATR breakout bearish"))
        return signals


__all__ = ['RSI_VolumeSurge', 'MACD_OBV', 'Breakout_VolumeExpansion', 
           'DonchianBreakout_OBV', 'PriceTrend_AccumulationVolume', 'VolumeSpike_ATRBreakout']
