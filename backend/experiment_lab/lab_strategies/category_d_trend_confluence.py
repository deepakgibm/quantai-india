"""
Category D - Trend + Momentum Confluence Strategies (26-34)
Combine trend indicators with momentum for high-probability entries.
"""

import pandas as pd
from typing import List
from .base import (
    ExperimentStrategy, StrategyInfo, SignalResult, SignalType,
    StrategyCategory, register_strategy
)
from ..indicators.technical import TechnicalIndicators as TI


@register_strategy
class EMA9_21_MACD(ExperimentStrategy):
    """Strategy 26: EMA (9/21) + MACD"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=26, name="EMA 9/21 + MACD", category=StrategyCategory.CATEGORY_D,
            description="Fast EMA crossover confirmed by MACD", indicators_used=["EMA9", "EMA21", "MACD"], min_bars_required=35)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        ema9, ema21 = TI.ema(df['close'], 9), TI.ema(df['close'], 21)
        macd_line, signal_line, _ = TI.macd(df['close'])
        atr = TI.atr(df, 14)
        for i in range(35, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            if ema9.iloc[i-1] <= ema21.iloc[i-1] and ema9.iloc[i] > ema21.iloc[i] and macd_line.iloc[i] > signal_line.iloc[i]:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.75,
                    stop_loss=ema21.iloc[i], take_profit=price + 2.5*atr.iloc[i],
                    indicators={"ema9": ema9.iloc[i], "macd": macd_line.iloc[i]}, reason="EMA9/21 bullish + MACD confirmation"))
            elif ema9.iloc[i-1] >= ema21.iloc[i-1] and ema9.iloc[i] < ema21.iloc[i] and macd_line.iloc[i] < signal_line.iloc[i]:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.75,
                    stop_loss=ema21.iloc[i], take_profit=price - 2.5*atr.iloc[i],
                    indicators={"ema9": ema9.iloc[i], "macd": macd_line.iloc[i]}, reason="EMA9/21 bearish + MACD confirmation"))
        return signals


@register_strategy
class EMA20_50_RSI(ExperimentStrategy):
    """Strategy 27: EMA (20/50) + RSI"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=27, name="EMA 20/50 + RSI", category=StrategyCategory.CATEGORY_D,
            description="EMA trend with RSI momentum filter", indicators_used=["EMA20", "EMA50", "RSI"], min_bars_required=55)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        ema20, ema50 = TI.ema(df['close'], 20), TI.ema(df['close'], 50)
        rsi = TI.rsi(df['close'], 14)
        atr = TI.atr(df, 14)
        for i in range(55, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            if ema20.iloc[i] > ema50.iloc[i] and 40 < rsi.iloc[i] < 70 and price > ema20.iloc[i]:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.7,
                    stop_loss=ema50.iloc[i], take_profit=price + 3*atr.iloc[i],
                    indicators={"rsi": rsi.iloc[i]}, reason="Uptrend pullback + RSI confirmation"))
            elif ema20.iloc[i] < ema50.iloc[i] and 30 < rsi.iloc[i] < 60 and price < ema20.iloc[i]:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.7,
                    stop_loss=ema50.iloc[i], take_profit=price - 3*atr.iloc[i],
                    indicators={"rsi": rsi.iloc[i]}, reason="Downtrend rally + RSI confirmation"))
        return signals


@register_strategy
class SMATrend_Momentum(ExperimentStrategy):
    """Strategy 28: SMA Trend + Momentum"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=28, name="SMA Trend + Momentum", category=StrategyCategory.CATEGORY_D,
            description="SMA trend direction with ROC momentum", indicators_used=["SMA", "ROC"], min_bars_required=55)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        sma20, sma50 = TI.sma(df['close'], 20), TI.sma(df['close'], 50)
        roc = TI.roc(df['close'], 10)
        atr = TI.atr(df, 14)
        for i in range(55, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            if sma20.iloc[i] > sma50.iloc[i] and roc.iloc[i] > 2:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.68,
                    stop_loss=sma20.iloc[i], take_profit=price + 2.5*atr.iloc[i],
                    indicators={"roc": roc.iloc[i]}, reason="SMA uptrend + strong momentum"))
            elif sma20.iloc[i] < sma50.iloc[i] and roc.iloc[i] < -2:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.68,
                    stop_loss=sma20.iloc[i], take_profit=price - 2.5*atr.iloc[i],
                    indicators={"roc": roc.iloc[i]}, reason="SMA downtrend + strong momentum"))
        return signals


@register_strategy
class ADX_MACD(ExperimentStrategy):
    """Strategy 29: ADX + MACD"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=29, name="ADX + MACD", category=StrategyCategory.CATEGORY_D,
            description="Strong trend (ADX) with MACD timing", indicators_used=["ADX", "MACD"], min_bars_required=35)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        adx, plus_di, minus_di = TI.adx(df, 14)
        macd_line, signal_line, _ = TI.macd(df['close'])
        atr = TI.atr(df, 14)
        for i in range(35, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            if adx.iloc[i] > 25:
                if macd_line.iloc[i-1] <= signal_line.iloc[i-1] and macd_line.iloc[i] > signal_line.iloc[i] and plus_di.iloc[i] > minus_di.iloc[i]:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.78,
                        stop_loss=price - 2*atr.iloc[i], take_profit=price + 3*atr.iloc[i],
                        indicators={"adx": adx.iloc[i], "macd": macd_line.iloc[i]}, reason="Strong ADX + MACD bullish"))
                elif macd_line.iloc[i-1] >= signal_line.iloc[i-1] and macd_line.iloc[i] < signal_line.iloc[i] and minus_di.iloc[i] > plus_di.iloc[i]:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.78,
                        stop_loss=price + 2*atr.iloc[i], take_profit=price - 3*atr.iloc[i],
                        indicators={"adx": adx.iloc[i], "macd": macd_line.iloc[i]}, reason="Strong ADX + MACD bearish"))
        return signals


@register_strategy
class ADX_RSI_Momentum(ExperimentStrategy):
    """Strategy 30: ADX + RSI + Momentum"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=30, name="ADX + RSI + Momentum", category=StrategyCategory.CATEGORY_D,
            description="Triple confluence: trend strength, momentum oscillator, rate of change",
            indicators_used=["ADX", "RSI", "ROC"], min_bars_required=30)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        adx, plus_di, minus_di = TI.adx(df, 14)
        rsi = TI.rsi(df['close'], 14)
        roc = TI.roc(df['close'], 10)
        atr = TI.atr(df, 14)
        for i in range(30, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            if adx.iloc[i] > 25 and plus_di.iloc[i] > minus_di.iloc[i] and rsi.iloc[i] > 50 and roc.iloc[i] > 0:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.8,
                    stop_loss=price - 2*atr.iloc[i], take_profit=price + 3*atr.iloc[i],
                    indicators={"adx": adx.iloc[i], "rsi": rsi.iloc[i], "roc": roc.iloc[i]}, reason="Triple bullish confluence"))
            elif adx.iloc[i] > 25 and minus_di.iloc[i] > plus_di.iloc[i] and rsi.iloc[i] < 50 and roc.iloc[i] < 0:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.8,
                    stop_loss=price + 2*atr.iloc[i], take_profit=price - 3*atr.iloc[i],
                    indicators={"adx": adx.iloc[i], "rsi": rsi.iloc[i], "roc": roc.iloc[i]}, reason="Triple bearish confluence"))
        return signals


@register_strategy
class Ichimoku_MACD(ExperimentStrategy):
    """Strategy 31: Ichimoku + MACD"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=31, name="Ichimoku + MACD", category=StrategyCategory.CATEGORY_D,
            description="Ichimoku cloud position with MACD crossover", indicators_used=["Ichimoku", "MACD"], min_bars_required=60)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        ichimoku = TI.ichimoku(df)
        macd_line, signal_line, _ = TI.macd(df['close'])
        atr = TI.atr(df, 14)
        for i in range(60, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            cloud_top = max(ichimoku['senkou_a'].iloc[i], ichimoku['senkou_b'].iloc[i]) if not pd.isna(ichimoku['senkou_a'].iloc[i]) else price
            cloud_bottom = min(ichimoku['senkou_a'].iloc[i], ichimoku['senkou_b'].iloc[i]) if not pd.isna(ichimoku['senkou_a'].iloc[i]) else price
            if price > cloud_top and macd_line.iloc[i-1] <= signal_line.iloc[i-1] and macd_line.iloc[i] > signal_line.iloc[i]:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.78,
                    stop_loss=cloud_top, take_profit=price + 3*atr.iloc[i], indicators={"macd": macd_line.iloc[i]},
                    reason="Above Ichimoku cloud + MACD bullish"))
            elif price < cloud_bottom and macd_line.iloc[i-1] >= signal_line.iloc[i-1] and macd_line.iloc[i] < signal_line.iloc[i]:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.78,
                    stop_loss=cloud_bottom, take_profit=price - 3*atr.iloc[i], indicators={"macd": macd_line.iloc[i]},
                    reason="Below Ichimoku cloud + MACD bearish"))
        return signals


@register_strategy 
class Ichimoku_RSI(ExperimentStrategy):
    """Strategy 32: Ichimoku + RSI"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=32, name="Ichimoku + RSI", category=StrategyCategory.CATEGORY_D,
            description="Ichimoku cloud with RSI momentum filter", indicators_used=["Ichimoku", "RSI"], min_bars_required=60)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        ichimoku = TI.ichimoku(df)
        rsi = TI.rsi(df['close'], 14)
        atr = TI.atr(df, 14)
        for i in range(60, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            cloud_top = max(ichimoku['senkou_a'].iloc[i], ichimoku['senkou_b'].iloc[i]) if not pd.isna(ichimoku['senkou_a'].iloc[i]) else price
            cloud_bottom = min(ichimoku['senkou_a'].iloc[i], ichimoku['senkou_b'].iloc[i]) if not pd.isna(ichimoku['senkou_a'].iloc[i]) else price
            if price > cloud_top and 45 < rsi.iloc[i] < 70:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.72,
                    stop_loss=cloud_top, take_profit=price + 2.5*atr.iloc[i], indicators={"rsi": rsi.iloc[i]},
                    reason="Above cloud + RSI bullish zone"))
            elif price < cloud_bottom and 30 < rsi.iloc[i] < 55:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.72,
                    stop_loss=cloud_bottom, take_profit=price - 2.5*atr.iloc[i], indicators={"rsi": rsi.iloc[i]},
                    reason="Below cloud + RSI bearish zone"))
        return signals


@register_strategy
class Supertrend_RSI(ExperimentStrategy):
    """Strategy 33: Supertrend + RSI"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=33, name="Supertrend + RSI", category=StrategyCategory.CATEGORY_D,
            description="Supertrend direction with RSI timing", indicators_used=["Supertrend", "RSI"], min_bars_required=30)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        supertrend, direction = TI.supertrend(df, 10, 3.0)
        rsi = TI.rsi(df['close'], 14)
        atr = TI.atr(df, 14)
        for i in range(30, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            if direction.iloc[i-1] == -1 and direction.iloc[i] == 1 and rsi.iloc[i] > 40:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.75,
                    stop_loss=supertrend.iloc[i], take_profit=price + 2.5*atr.iloc[i],
                    indicators={"rsi": rsi.iloc[i]}, reason="Supertrend bullish flip + RSI confirmation"))
            elif direction.iloc[i-1] == 1 and direction.iloc[i] == -1 and rsi.iloc[i] < 60:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.75,
                    stop_loss=supertrend.iloc[i], take_profit=price - 2.5*atr.iloc[i],
                    indicators={"rsi": rsi.iloc[i]}, reason="Supertrend bearish flip + RSI confirmation"))
        return signals


@register_strategy
class Supertrend_MACD(ExperimentStrategy):
    """Strategy 34: Supertrend + MACD"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=34, name="Supertrend + MACD", category=StrategyCategory.CATEGORY_D,
            description="Supertrend with MACD momentum confirmation", indicators_used=["Supertrend", "MACD"], min_bars_required=35)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        supertrend, direction = TI.supertrend(df, 10, 3.0)
        macd_line, signal_line, _ = TI.macd(df['close'])
        atr = TI.atr(df, 14)
        for i in range(35, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            if direction.iloc[i] == 1 and macd_line.iloc[i-1] <= signal_line.iloc[i-1] and macd_line.iloc[i] > signal_line.iloc[i]:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.78,
                    stop_loss=supertrend.iloc[i], take_profit=price + 3*atr.iloc[i],
                    indicators={"macd": macd_line.iloc[i]}, reason="Supertrend bullish + MACD crossover"))
            elif direction.iloc[i] == -1 and macd_line.iloc[i-1] >= signal_line.iloc[i-1] and macd_line.iloc[i] < signal_line.iloc[i]:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.78,
                    stop_loss=supertrend.iloc[i], take_profit=price - 3*atr.iloc[i],
                    indicators={"macd": macd_line.iloc[i]}, reason="Supertrend bearish + MACD crossover"))
        return signals


__all__ = ['EMA9_21_MACD', 'EMA20_50_RSI', 'SMATrend_Momentum', 'ADX_MACD', 'ADX_RSI_Momentum',
           'Ichimoku_MACD', 'Ichimoku_RSI', 'Supertrend_RSI', 'Supertrend_MACD']
