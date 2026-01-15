"""
Category H - Multi-Timeframe Strategies (54-59)
Strategies that use higher timeframe for bias and lower timeframe for entry.
Note: These require data from multiple timeframes.
"""

import pandas as pd
from typing import List, Optional
from .base import (
    ExperimentStrategy, StrategyInfo, SignalResult, SignalType,
    StrategyCategory, register_strategy
)
from ..indicators.technical import TechnicalIndicators as TI


class MultiTimeframeStrategy(ExperimentStrategy):
    """Base class for multi-timeframe strategies."""
    
    def __init__(self):
        self._htf_data: Optional[pd.DataFrame] = None
    
    def set_htf_data(self, df: pd.DataFrame):
        """Set higher timeframe data for analysis."""
        self._htf_data = df
    
    def get_htf_bias(self, df: pd.DataFrame, current_idx: int) -> Optional[str]:
        """Get bias from higher timeframe. Override in subclass."""
        return None


@register_strategy
class DailyTrend_1HEntry(MultiTimeframeStrategy):
    """Strategy 54: Daily Trend + 1H Entry (EMA + RSI)"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=54, name="Daily Trend + 1H Entry", category=StrategyCategory.CATEGORY_H,
            description="Daily EMA trend direction with 1H RSI entry timing",
            indicators_used=["EMA (Daily)", "RSI (1H)"], min_bars_required=55)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        # For single timeframe simulation, use long EMAs as proxy for "daily" trend
        ema50 = TI.ema(df['close'], 50)
        ema100 = TI.ema(df['close'], 100) if len(df) > 100 else ema50
        rsi = TI.rsi(df['close'], 14)
        atr = TI.atr(df, 14)
        for i in range(55, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            # Daily bias bullish (price above EMA50 which is above EMA100)
            if price > ema50.iloc[i] and ema50.iloc[i] > ema100.iloc[i] if len(df) > 100 else True:
                if rsi.iloc[i-1] < 40 and rsi.iloc[i] > 40:  # RSI pullback recovery
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.75,
                        stop_loss=ema50.iloc[i], take_profit=price + 3*atr.iloc[i],
                        indicators={"rsi": rsi.iloc[i]}, reason="Daily uptrend + RSI pullback entry"))
            elif price < ema50.iloc[i] and (ema50.iloc[i] < ema100.iloc[i] if len(df) > 100 else True):
                if rsi.iloc[i-1] > 60 and rsi.iloc[i] < 60:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.75,
                        stop_loss=ema50.iloc[i], take_profit=price - 3*atr.iloc[i],
                        indicators={"rsi": rsi.iloc[i]}, reason="Daily downtrend + RSI rally entry"))
        return signals


@register_strategy
class DailyTrend_30mMomentum(MultiTimeframeStrategy):
    """Strategy 55: Daily Trend + 30m Momentum"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=55, name="Daily Trend + 30m Momentum", category=StrategyCategory.CATEGORY_H,
            description="Daily trend with 30m momentum breakout",
            indicators_used=["EMA (Daily)", "ROC (30m)"], min_bars_required=55)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        ema50 = TI.ema(df['close'], 50)
        roc = TI.roc(df['close'], 10)
        atr = TI.atr(df, 14)
        for i in range(55, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            if price > ema50.iloc[i] and roc.iloc[i-1] <= 0 and roc.iloc[i] > 2:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.72,
                    stop_loss=ema50.iloc[i], take_profit=price + 2.5*atr.iloc[i],
                    indicators={"roc": roc.iloc[i]}, reason="Daily uptrend + momentum breakout"))
            elif price < ema50.iloc[i] and roc.iloc[i-1] >= 0 and roc.iloc[i] < -2:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.72,
                    stop_loss=ema50.iloc[i], take_profit=price - 2.5*atr.iloc[i],
                    indicators={"roc": roc.iloc[i]}, reason="Daily downtrend + momentum breakdown"))
        return signals


@register_strategy
class H4Structure_15mBreakout(MultiTimeframeStrategy):
    """Strategy 56: 4H Structure + 15m Breakout"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=56, name="4H Structure + 15m Breakout", category=StrategyCategory.CATEGORY_H,
            description="4H support/resistance with 15m breakout entry",
            indicators_used=["S/R (4H)", "Breakout (15m)"], min_bars_required=30)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        # Use longer lookback for "structure"
        high_50 = df['high'].rolling(50).max()
        low_50 = df['low'].rolling(50).min()
        high_10 = df['high'].rolling(10).max()
        low_10 = df['low'].rolling(10).min()
        atr = TI.atr(df, 14)
        for i in range(50, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            # Near support and breaking short-term high
            if df['low'].iloc[i] <= low_50.iloc[i] * 1.02 and price > high_10.iloc[i-1]:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.7,
                    stop_loss=low_50.iloc[i] * 0.99, take_profit=price + 2.5*atr.iloc[i],
                    indicators={}, reason="4H support + 15m breakout"))
            elif df['high'].iloc[i] >= high_50.iloc[i] * 0.98 and price < low_10.iloc[i-1]:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.7,
                    stop_loss=high_50.iloc[i] * 1.01, take_profit=price - 2.5*atr.iloc[i],
                    indicators={}, reason="4H resistance + 15m breakdown"))
        return signals


@register_strategy
class WeeklyTrend_DailyPullback(MultiTimeframeStrategy):
    """Strategy 57: Weekly Trend + Daily Pullback"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=57, name="Weekly Trend + Daily Pullback", category=StrategyCategory.CATEGORY_H,
            description="Weekly trend with daily pullback to moving average",
            indicators_used=["EMA (Weekly)", "EMA (Daily)"], min_bars_required=100)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        # Simulate weekly with very long EMA
        ema100 = TI.ema(df['close'], 100)  # ~Weekly
        ema20 = TI.ema(df['close'], 20)   # ~Daily
        atr = TI.atr(df, 14)
        for i in range(100, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            # Weekly bullish, daily pullback to EMA20
            if price > ema100.iloc[i] and df['low'].iloc[i] <= ema20.iloc[i] <= df['high'].iloc[i]:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.72,
                    stop_loss=ema20.iloc[i] * 0.98, take_profit=price + 3*atr.iloc[i],
                    indicators={"ema20": ema20.iloc[i], "ema100": ema100.iloc[i]},
                    reason="Weekly uptrend + daily pullback"))
            elif price < ema100.iloc[i] and df['low'].iloc[i] <= ema20.iloc[i] <= df['high'].iloc[i]:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.72,
                    stop_loss=ema20.iloc[i] * 1.02, take_profit=price - 3*atr.iloc[i],
                    indicators={"ema20": ema20.iloc[i], "ema100": ema100.iloc[i]},
                    reason="Weekly downtrend + daily rally"))
        return signals


@register_strategy
class HTF_ADX_LTF_RSI(MultiTimeframeStrategy):
    """Strategy 58: HTF ADX + LTF RSI"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=58, name="HTF ADX + LTF RSI", category=StrategyCategory.CATEGORY_H,
            description="Higher TF ADX for trend, lower TF RSI for timing",
            indicators_used=["ADX (HTF)", "RSI (LTF)"], min_bars_required=35)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        # Use longer period ADX for "HTF" simulation
        adx, plus_di, minus_di = TI.adx(df, 28)  # Longer period = HTF proxy
        rsi = TI.rsi(df['close'], 7)  # Shorter period = LTF proxy
        atr = TI.atr(df, 14)
        for i in range(35, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            if adx.iloc[i] > 25 and plus_di.iloc[i] > minus_di.iloc[i]:
                if rsi.iloc[i-1] < 35 and rsi.iloc[i] > 35:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.75,
                        stop_loss=price - 2*atr.iloc[i], take_profit=price + 2.5*atr.iloc[i],
                        indicators={"adx": adx.iloc[i], "rsi": rsi.iloc[i]},
                        reason="HTF bullish ADX + LTF RSI pullback"))
            elif adx.iloc[i] > 25 and minus_di.iloc[i] > plus_di.iloc[i]:
                if rsi.iloc[i-1] > 65 and rsi.iloc[i] < 65:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.75,
                        stop_loss=price + 2*atr.iloc[i], take_profit=price - 2.5*atr.iloc[i],
                        indicators={"adx": adx.iloc[i], "rsi": rsi.iloc[i]},
                        reason="HTF bearish ADX + LTF RSI rally"))
        return signals


@register_strategy
class HTF_Ichimoku_LTF_MACD(MultiTimeframeStrategy):
    """Strategy 59: HTF Ichimoku + LTF MACD"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=59, name="HTF Ichimoku + LTF MACD", category=StrategyCategory.CATEGORY_H,
            description="Higher TF Ichimoku cloud for bias, lower TF MACD for entry",
            indicators_used=["Ichimoku (HTF)", "MACD (LTF)"], min_bars_required=60)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        ichimoku = TI.ichimoku(df)
        macd_line, signal_line, _ = TI.macd(df['close'], 6, 13, 5)  # Faster MACD
        atr = TI.atr(df, 14)
        for i in range(60, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            cloud_top = max(ichimoku['senkou_a'].iloc[i], ichimoku['senkou_b'].iloc[i]) if not pd.isna(ichimoku['senkou_a'].iloc[i]) else price
            cloud_bottom = min(ichimoku['senkou_a'].iloc[i], ichimoku['senkou_b'].iloc[i]) if not pd.isna(ichimoku['senkou_a'].iloc[i]) else price
            if price > cloud_top:
                if macd_line.iloc[i-1] <= signal_line.iloc[i-1] and macd_line.iloc[i] > signal_line.iloc[i]:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.78,
                        stop_loss=cloud_top, take_profit=price + 3*atr.iloc[i],
                        indicators={"macd": macd_line.iloc[i]},
                        reason="HTF above cloud + LTF MACD crossover"))
            elif price < cloud_bottom:
                if macd_line.iloc[i-1] >= signal_line.iloc[i-1] and macd_line.iloc[i] < signal_line.iloc[i]:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.78,
                        stop_loss=cloud_bottom, take_profit=price - 3*atr.iloc[i],
                        indicators={"macd": macd_line.iloc[i]},
                        reason="HTF below cloud + LTF MACD crossover"))
        return signals


__all__ = ['DailyTrend_1HEntry', 'DailyTrend_30mMomentum', 'H4Structure_15mBreakout',
           'WeeklyTrend_DailyPullback', 'HTF_ADX_LTF_RSI', 'HTF_Ichimoku_LTF_MACD']
