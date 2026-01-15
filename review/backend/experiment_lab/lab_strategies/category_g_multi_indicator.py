"""
Category G - Multi-Indicator Confluence Strategies (47-53)
High-confidence strategies requiring 3+ indicators to align.
"""

import pandas as pd
from typing import List
from .base import (
    ExperimentStrategy, StrategyInfo, SignalResult, SignalType,
    StrategyCategory, register_strategy
)
from ..indicators.technical import TechnicalIndicators as TI


@register_strategy
class RSI_MACD_ADX(ExperimentStrategy):
    """Strategy 47: RSI + MACD + ADX"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=47, name="RSI + MACD + ADX", category=StrategyCategory.CATEGORY_G,
            description="Triple confluence: momentum, trend signal, trend strength",
            indicators_used=["RSI", "MACD", "ADX"], min_bars_required=35)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        rsi = TI.rsi(df['close'], 14)
        macd_line, signal_line, _ = TI.macd(df['close'])
        adx, plus_di, minus_di = TI.adx(df, 14)
        atr = TI.atr(df, 14)
        for i in range(35, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            if rsi.iloc[i] > 50 and macd_line.iloc[i] > signal_line.iloc[i] and adx.iloc[i] > 25 and plus_di.iloc[i] > minus_di.iloc[i]:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.85,
                    stop_loss=price - 2*atr.iloc[i], take_profit=price + 3*atr.iloc[i],
                    indicators={"rsi": rsi.iloc[i], "macd": macd_line.iloc[i], "adx": adx.iloc[i]},
                    reason="Triple bullish confluence: RSI+MACD+ADX"))
            elif rsi.iloc[i] < 50 and macd_line.iloc[i] < signal_line.iloc[i] and adx.iloc[i] > 25 and minus_di.iloc[i] > plus_di.iloc[i]:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.85,
                    stop_loss=price + 2*atr.iloc[i], take_profit=price - 3*atr.iloc[i],
                    indicators={"rsi": rsi.iloc[i], "macd": macd_line.iloc[i], "adx": adx.iloc[i]},
                    reason="Triple bearish confluence: RSI+MACD+ADX"))
        return signals


@register_strategy
class RSI_MACD_Volume(ExperimentStrategy):
    """Strategy 48: RSI + MACD + Volume"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=48, name="RSI + MACD + Volume", category=StrategyCategory.CATEGORY_G,
            description="Momentum confluence with volume confirmation",
            indicators_used=["RSI", "MACD", "Volume"], min_bars_required=35)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        rsi = TI.rsi(df['close'], 14)
        macd_line, signal_line, _ = TI.macd(df['close'])
        vol_ratio = TI.volume_ratio(df, 20)
        atr = TI.atr(df, 14)
        for i in range(35, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            if rsi.iloc[i] > 50 and macd_line.iloc[i-1] <= signal_line.iloc[i-1] and macd_line.iloc[i] > signal_line.iloc[i] and vol_ratio.iloc[i] > 1.3:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.8,
                    stop_loss=price - 2*atr.iloc[i], take_profit=price + 2.5*atr.iloc[i],
                    indicators={"rsi": rsi.iloc[i], "vol_ratio": vol_ratio.iloc[i]},
                    reason="RSI+MACD crossover + volume confirmation"))
            elif rsi.iloc[i] < 50 and macd_line.iloc[i-1] >= signal_line.iloc[i-1] and macd_line.iloc[i] < signal_line.iloc[i] and vol_ratio.iloc[i] > 1.3:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.8,
                    stop_loss=price + 2*atr.iloc[i], take_profit=price - 2.5*atr.iloc[i],
                    indicators={"rsi": rsi.iloc[i], "vol_ratio": vol_ratio.iloc[i]},
                    reason="RSI+MACD crossover + volume confirmation"))
        return signals


@register_strategy
class Bollinger_RSI_ADX(ExperimentStrategy):
    """Strategy 49: Bollinger + RSI + ADX"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=49, name="Bollinger + RSI + ADX", category=StrategyCategory.CATEGORY_G,
            description="Bollinger breakout with RSI and ADX filters",
            indicators_used=["Bollinger Bands", "RSI", "ADX"], min_bars_required=30)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        upper, middle, lower = TI.bollinger_bands(df['close'], 20, 2.0)
        rsi = TI.rsi(df['close'], 14)
        adx, _, _ = TI.adx(df, 14)
        atr = TI.atr(df, 14)
        for i in range(30, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            if price > upper.iloc[i] and rsi.iloc[i] > 55 and rsi.iloc[i] < 75 and adx.iloc[i] > 25:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.78,
                    stop_loss=middle.iloc[i], take_profit=price + 2.5*atr.iloc[i],
                    indicators={"rsi": rsi.iloc[i], "adx": adx.iloc[i]},
                    reason="BB breakout + RSI+ADX confirmation"))
            elif price < lower.iloc[i] and rsi.iloc[i] < 45 and rsi.iloc[i] > 25 and adx.iloc[i] > 25:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.78,
                    stop_loss=middle.iloc[i], take_profit=price - 2.5*atr.iloc[i],
                    indicators={"rsi": rsi.iloc[i], "adx": adx.iloc[i]},
                    reason="BB breakdown + RSI+ADX confirmation"))
        return signals


@register_strategy
class EMATrend_Momentum_Volume(ExperimentStrategy):
    """Strategy 50: EMA Trend + Momentum + Volume"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=50, name="EMA Trend + Momentum + Volume", category=StrategyCategory.CATEGORY_G,
            description="EMA trend with ROC momentum and volume confirmation",
            indicators_used=["EMA", "ROC", "Volume"], min_bars_required=55)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        ema20, ema50 = TI.ema(df['close'], 20), TI.ema(df['close'], 50)
        roc = TI.roc(df['close'], 10)
        vol_ratio = TI.volume_ratio(df, 20)
        atr = TI.atr(df, 14)
        for i in range(55, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            if ema20.iloc[i] > ema50.iloc[i] and roc.iloc[i] > 1 and vol_ratio.iloc[i] > 1.2:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.75,
                    stop_loss=ema20.iloc[i], take_profit=price + 2.5*atr.iloc[i],
                    indicators={"roc": roc.iloc[i], "vol_ratio": vol_ratio.iloc[i]},
                    reason="EMA uptrend + momentum + volume"))
            elif ema20.iloc[i] < ema50.iloc[i] and roc.iloc[i] < -1 and vol_ratio.iloc[i] > 1.2:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.75,
                    stop_loss=ema20.iloc[i], take_profit=price - 2.5*atr.iloc[i],
                    indicators={"roc": roc.iloc[i], "vol_ratio": vol_ratio.iloc[i]},
                    reason="EMA downtrend + momentum + volume"))
        return signals


@register_strategy
class Supertrend_RSI_Volume(ExperimentStrategy):
    """Strategy 51: Supertrend + RSI + Volume"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=51, name="Supertrend + RSI + Volume", category=StrategyCategory.CATEGORY_G,
            description="Supertrend direction with RSI and volume confirmation",
            indicators_used=["Supertrend", "RSI", "Volume"], min_bars_required=30)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        supertrend, direction = TI.supertrend(df, 10, 3.0)
        rsi = TI.rsi(df['close'], 14)
        vol_ratio = TI.volume_ratio(df, 20)
        atr = TI.atr(df, 14)
        for i in range(30, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            if direction.iloc[i-1] == -1 and direction.iloc[i] == 1 and rsi.iloc[i] > 45 and vol_ratio.iloc[i] > 1.2:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.8,
                    stop_loss=supertrend.iloc[i], take_profit=price + 2.5*atr.iloc[i],
                    indicators={"rsi": rsi.iloc[i], "vol_ratio": vol_ratio.iloc[i]},
                    reason="Supertrend flip + RSI + volume"))
            elif direction.iloc[i-1] == 1 and direction.iloc[i] == -1 and rsi.iloc[i] < 55 and vol_ratio.iloc[i] > 1.2:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.8,
                    stop_loss=supertrend.iloc[i], take_profit=price - 2.5*atr.iloc[i],
                    indicators={"rsi": rsi.iloc[i], "vol_ratio": vol_ratio.iloc[i]},
                    reason="Supertrend flip + RSI + volume"))
        return signals


@register_strategy
class Ichimoku_MACD_Volume(ExperimentStrategy):
    """Strategy 52: Ichimoku + MACD + Volume"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=52, name="Ichimoku + MACD + Volume", category=StrategyCategory.CATEGORY_G,
            description="Ichimoku cloud with MACD crossover and volume",
            indicators_used=["Ichimoku", "MACD", "Volume"], min_bars_required=60)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        ichimoku = TI.ichimoku(df)
        macd_line, signal_line, _ = TI.macd(df['close'])
        vol_ratio = TI.volume_ratio(df, 20)
        atr = TI.atr(df, 14)
        for i in range(60, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            cloud_top = max(ichimoku['senkou_a'].iloc[i], ichimoku['senkou_b'].iloc[i]) if not pd.isna(ichimoku['senkou_a'].iloc[i]) else price
            cloud_bottom = min(ichimoku['senkou_a'].iloc[i], ichimoku['senkou_b'].iloc[i]) if not pd.isna(ichimoku['senkou_a'].iloc[i]) else price
            if price > cloud_top and macd_line.iloc[i] > signal_line.iloc[i] and vol_ratio.iloc[i] > 1.2:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.82,
                    stop_loss=cloud_top, take_profit=price + 3*atr.iloc[i],
                    indicators={"macd": macd_line.iloc[i], "vol_ratio": vol_ratio.iloc[i]},
                    reason="Above cloud + MACD + volume"))
            elif price < cloud_bottom and macd_line.iloc[i] < signal_line.iloc[i] and vol_ratio.iloc[i] > 1.2:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.82,
                    stop_loss=cloud_bottom, take_profit=price - 3*atr.iloc[i],
                    indicators={"macd": macd_line.iloc[i], "vol_ratio": vol_ratio.iloc[i]},
                    reason="Below cloud + MACD + volume"))
        return signals


@register_strategy
class ATRBreakout_ADX_Momentum(ExperimentStrategy):
    """Strategy 53: ATR Breakout + ADX + Momentum"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=53, name="ATR Breakout + ADX + Momentum", category=StrategyCategory.CATEGORY_G,
            description="Volatility breakout with trend strength and momentum",
            indicators_used=["ATR", "ADX", "ROC"], min_bars_required=30)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        atr = TI.atr(df, 14)
        adx, plus_di, minus_di = TI.adx(df, 14)
        roc = TI.roc(df['close'], 10)
        for i in range(30, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            price_change = price - df['close'].iloc[i-1]
            if abs(price_change) > 1.5 * atr.iloc[i-1] and adx.iloc[i] > 25:
                if price_change > 0 and roc.iloc[i] > 0 and plus_di.iloc[i] > minus_di.iloc[i]:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.8,
                        stop_loss=price - atr.iloc[i], take_profit=price + 2*atr.iloc[i],
                        indicators={"adx": adx.iloc[i], "roc": roc.iloc[i]},
                        reason="ATR breakout + ADX + momentum bullish"))
                elif price_change < 0 and roc.iloc[i] < 0 and minus_di.iloc[i] > plus_di.iloc[i]:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.8,
                        stop_loss=price + atr.iloc[i], take_profit=price - 2*atr.iloc[i],
                        indicators={"adx": adx.iloc[i], "roc": roc.iloc[i]},
                        reason="ATR breakout + ADX + momentum bearish"))
        return signals


__all__ = ['RSI_MACD_ADX', 'RSI_MACD_Volume', 'Bollinger_RSI_ADX', 'EMATrend_Momentum_Volume',
           'Supertrend_RSI_Volume', 'Ichimoku_MACD_Volume', 'ATRBreakout_ADX_Momentum']
