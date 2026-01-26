"""
Category B - Price + Momentum Strategies (11-18)
Combine price action with momentum indicators.
"""

import pandas as pd
from typing import List
from .base import (
    ExperimentStrategy, StrategyInfo, SignalResult, SignalType,
    StrategyCategory, register_strategy
)
from ..indicators.technical import TechnicalIndicators as TI


@register_strategy
class RSI_MACD(ExperimentStrategy):
    """Strategy 11: RSI + MACD"""
    
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(
            id=11,
            name="RSI + MACD",
            category=StrategyCategory.CATEGORY_B,
            description="RSI oversold/overbought confirmed by MACD crossover",
            indicators_used=["RSI", "MACD"],
            min_bars_required=35
        )
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df):
            return []
        
        signals = []
        rsi = TI.rsi(df['close'], 14)
        macd_line, signal_line, histogram = TI.macd(df['close'])
        atr = TI.atr(df, 14)
        
        for i in range(35, len(df)):
            idx = df.index[i]
            price = df['close'].iloc[i]
            current_atr = atr.iloc[i]
            
            # Buy: RSI < 40 AND MACD bullish crossover
            if rsi.iloc[i] < 40 and macd_line.iloc[i-1] <= signal_line.iloc[i-1] and macd_line.iloc[i] > signal_line.iloc[i]:
                signals.append(SignalResult(
                    timestamp=idx, signal=SignalType.BUY, price=price,
                    confidence=0.75,
                    stop_loss=price - 2 * current_atr,
                    take_profit=price + 3 * current_atr,
                    indicators={"rsi": rsi.iloc[i], "macd": macd_line.iloc[i]},
                    reason="RSI oversold + MACD bullish crossover"
                ))
            # Sell: RSI > 60 AND MACD bearish crossover
            elif rsi.iloc[i] > 60 and macd_line.iloc[i-1] >= signal_line.iloc[i-1] and macd_line.iloc[i] < signal_line.iloc[i]:
                signals.append(SignalResult(
                    timestamp=idx, signal=SignalType.SELL, price=price,
                    confidence=0.75,
                    stop_loss=price + 2 * current_atr,
                    take_profit=price - 3 * current_atr,
                    indicators={"rsi": rsi.iloc[i], "macd": macd_line.iloc[i]},
                    reason="RSI overbought + MACD bearish crossover"
                ))
        
        return signals


@register_strategy
class RSI_Stochastic(ExperimentStrategy):
    """Strategy 12: RSI + Stochastic"""
    
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(
            id=12,
            name="RSI + Stochastic",
            category=StrategyCategory.CATEGORY_B,
            description="Dual oscillator confirmation for entries",
            indicators_used=["RSI", "Stochastic"],
            min_bars_required=25
        )
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df):
            return []
        
        signals = []
        rsi = TI.rsi(df['close'], 14)
        stoch_k, stoch_d = TI.stochastic(df, 14, 3)
        atr = TI.atr(df, 14)
        
        for i in range(25, len(df)):
            idx = df.index[i]
            price = df['close'].iloc[i]
            current_atr = atr.iloc[i]
            
            # Buy: Both RSI and Stochastic oversold
            if rsi.iloc[i] < 35 and stoch_k.iloc[i] < 25 and stoch_k.iloc[i] > stoch_k.iloc[i-1]:
                signals.append(SignalResult(
                    timestamp=idx, signal=SignalType.BUY, price=price,
                    confidence=0.7,
                    stop_loss=price - 2 * current_atr,
                    take_profit=price + 2.5 * current_atr,
                    indicators={"rsi": rsi.iloc[i], "stoch_k": stoch_k.iloc[i]},
                    reason="RSI + Stochastic both oversold"
                ))
            # Sell: Both RSI and Stochastic overbought
            elif rsi.iloc[i] > 65 and stoch_k.iloc[i] > 75 and stoch_k.iloc[i] < stoch_k.iloc[i-1]:
                signals.append(SignalResult(
                    timestamp=idx, signal=SignalType.SELL, price=price,
                    confidence=0.7,
                    stop_loss=price + 2 * current_atr,
                    take_profit=price - 2.5 * current_atr,
                    indicators={"rsi": rsi.iloc[i], "stoch_k": stoch_k.iloc[i]},
                    reason="RSI + Stochastic both overbought"
                ))
        
        return signals


@register_strategy
class RSI_WilliamsR(ExperimentStrategy):
    """Strategy 13: RSI + Williams %R"""
    
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(
            id=13,
            name="RSI + Williams %R",
            category=StrategyCategory.CATEGORY_B,
            description="RSI confirmed by Williams %R extremes",
            indicators_used=["RSI", "Williams %R"],
            min_bars_required=25
        )
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df):
            return []
        
        signals = []
        rsi = TI.rsi(df['close'], 14)
        williams = TI.williams_r(df, 14)
        atr = TI.atr(df, 14)
        
        for i in range(25, len(df)):
            idx = df.index[i]
            price = df['close'].iloc[i]
            current_atr = atr.iloc[i]
            
            # Buy: RSI < 35 AND Williams < -80
            if rsi.iloc[i] < 35 and williams.iloc[i] < -80:
                signals.append(SignalResult(
                    timestamp=idx, signal=SignalType.BUY, price=price,
                    confidence=0.72,
                    stop_loss=price - 2 * current_atr,
                    take_profit=price + 2.5 * current_atr,
                    indicators={"rsi": rsi.iloc[i], "williams_r": williams.iloc[i]},
                    reason="RSI + Williams %R both oversold"
                ))
            # Sell: RSI > 65 AND Williams > -20
            elif rsi.iloc[i] > 65 and williams.iloc[i] > -20:
                signals.append(SignalResult(
                    timestamp=idx, signal=SignalType.SELL, price=price,
                    confidence=0.72,
                    stop_loss=price + 2 * current_atr,
                    take_profit=price - 2.5 * current_atr,
                    indicators={"rsi": rsi.iloc[i], "williams_r": williams.iloc[i]},
                    reason="RSI + Williams %R both overbought"
                ))
        
        return signals


@register_strategy
class MACD_Momentum(ExperimentStrategy):
    """Strategy 14: MACD + Momentum (ROC)"""
    
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(
            id=14,
            name="MACD + Momentum",
            category=StrategyCategory.CATEGORY_B,
            description="MACD crossover confirmed by Rate of Change",
            indicators_used=["MACD", "ROC"],
            min_bars_required=35
        )
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df):
            return []
        
        signals = []
        macd_line, signal_line, _ = TI.macd(df['close'])
        roc = TI.roc(df['close'], 10)
        atr = TI.atr(df, 14)
        
        for i in range(35, len(df)):
            idx = df.index[i]
            price = df['close'].iloc[i]
            current_atr = atr.iloc[i]
            
            # Buy: MACD bullish crossover AND positive momentum
            if macd_line.iloc[i-1] <= signal_line.iloc[i-1] and macd_line.iloc[i] > signal_line.iloc[i] and roc.iloc[i] > 0:
                signals.append(SignalResult(
                    timestamp=idx, signal=SignalType.BUY, price=price,
                    confidence=0.7,
                    stop_loss=price - 2 * current_atr,
                    take_profit=price + 3 * current_atr,
                    indicators={"macd": macd_line.iloc[i], "roc": roc.iloc[i]},
                    reason="MACD bullish + positive momentum"
                ))
            # Sell: MACD bearish crossover AND negative momentum
            elif macd_line.iloc[i-1] >= signal_line.iloc[i-1] and macd_line.iloc[i] < signal_line.iloc[i] and roc.iloc[i] < 0:
                signals.append(SignalResult(
                    timestamp=idx, signal=SignalType.SELL, price=price,
                    confidence=0.7,
                    stop_loss=price + 2 * current_atr,
                    take_profit=price - 3 * current_atr,
                    indicators={"macd": macd_line.iloc[i], "roc": roc.iloc[i]},
                    reason="MACD bearish + negative momentum"
                ))
        
        return signals


@register_strategy
class MACD_Stochastic(ExperimentStrategy):
    """Strategy 15: MACD + Stochastic"""
    
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(
            id=15,
            name="MACD + Stochastic",
            category=StrategyCategory.CATEGORY_B,
            description="MACD trend with Stochastic timing",
            indicators_used=["MACD", "Stochastic"],
            min_bars_required=35
        )
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df):
            return []
        
        signals = []
        macd_line, signal_line, _ = TI.macd(df['close'])
        stoch_k, stoch_d = TI.stochastic(df, 14, 3)
        atr = TI.atr(df, 14)
        
        for i in range(35, len(df)):
            idx = df.index[i]
            price = df['close'].iloc[i]
            current_atr = atr.iloc[i]
            
            # Buy: MACD > Signal AND Stochastic crossing up from oversold
            if macd_line.iloc[i] > signal_line.iloc[i] and stoch_k.iloc[i-1] < 30 and stoch_k.iloc[i] > stoch_d.iloc[i]:
                signals.append(SignalResult(
                    timestamp=idx, signal=SignalType.BUY, price=price,
                    confidence=0.72,
                    stop_loss=price - 2 * current_atr,
                    take_profit=price + 2.5 * current_atr,
                    indicators={"macd": macd_line.iloc[i], "stoch_k": stoch_k.iloc[i]},
                    reason="MACD bullish + Stochastic oversold crossover"
                ))
            # Sell: MACD < Signal AND Stochastic crossing down from overbought
            elif macd_line.iloc[i] < signal_line.iloc[i] and stoch_k.iloc[i-1] > 70 and stoch_k.iloc[i] < stoch_d.iloc[i]:
                signals.append(SignalResult(
                    timestamp=idx, signal=SignalType.SELL, price=price,
                    confidence=0.72,
                    stop_loss=price + 2 * current_atr,
                    take_profit=price - 2.5 * current_atr,
                    indicators={"macd": macd_line.iloc[i], "stoch_k": stoch_k.iloc[i]},
                    reason="MACD bearish + Stochastic overbought crossover"
                ))
        
        return signals


@register_strategy
class Momentum_MATrend(ExperimentStrategy):
    """Strategy 16: Momentum + Moving Average Trend"""
    
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(
            id=16,
            name="Momentum + MA Trend",
            category=StrategyCategory.CATEGORY_B,
            description="Trade momentum in direction of EMA trend",
            indicators_used=["ROC", "EMA"],
            min_bars_required=55
        )
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df):
            return []
        
        signals = []
        roc = TI.roc(df['close'], 10)
        ema20 = TI.ema(df['close'], 20)
        ema50 = TI.ema(df['close'], 50)
        atr = TI.atr(df, 14)
        
        for i in range(55, len(df)):
            idx = df.index[i]
            price = df['close'].iloc[i]
            current_atr = atr.iloc[i]
            
            # Buy: Uptrend (EMA20 > EMA50) AND momentum turning positive
            if ema20.iloc[i] > ema50.iloc[i] and roc.iloc[i-1] <= 0 and roc.iloc[i] > 0:
                signals.append(SignalResult(
                    timestamp=idx, signal=SignalType.BUY, price=price,
                    confidence=0.68,
                    stop_loss=ema50.iloc[i],
                    take_profit=price + 3 * current_atr,
                    indicators={"roc": roc.iloc[i], "ema20": ema20.iloc[i], "ema50": ema50.iloc[i]},
                    reason="Uptrend + momentum turning positive"
                ))
            # Sell: Downtrend (EMA20 < EMA50) AND momentum turning negative
            elif ema20.iloc[i] < ema50.iloc[i] and roc.iloc[i-1] >= 0 and roc.iloc[i] < 0:
                signals.append(SignalResult(
                    timestamp=idx, signal=SignalType.SELL, price=price,
                    confidence=0.68,
                    stop_loss=ema50.iloc[i],
                    take_profit=price - 3 * current_atr,
                    indicators={"roc": roc.iloc[i], "ema20": ema20.iloc[i], "ema50": ema50.iloc[i]},
                    reason="Downtrend + momentum turning negative"
                ))
        
        return signals


@register_strategy
class RSI_PriceMomentum(ExperimentStrategy):
    """Strategy 17: RSI + Price Momentum"""
    
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(
            id=17,
            name="RSI + Price Momentum",
            category=StrategyCategory.CATEGORY_B,
            description="RSI with price momentum confirmation",
            indicators_used=["RSI", "ROC"],
            min_bars_required=25
        )
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df):
            return []
        
        signals = []
        rsi = TI.rsi(df['close'], 14)
        roc = TI.roc(df['close'], 5)
        atr = TI.atr(df, 14)
        
        for i in range(25, len(df)):
            idx = df.index[i]
            price = df['close'].iloc[i]
            current_atr = atr.iloc[i]
            
            # Buy: RSI between 40-50 (not extreme) AND strong positive momentum
            if 40 <= rsi.iloc[i] <= 50 and roc.iloc[i] > 2:
                signals.append(SignalResult(
                    timestamp=idx, signal=SignalType.BUY, price=price,
                    confidence=0.65,
                    stop_loss=price - 1.5 * current_atr,
                    take_profit=price + 2.5 * current_atr,
                    indicators={"rsi": rsi.iloc[i], "roc": roc.iloc[i]},
                    reason="RSI neutral + strong positive momentum"
                ))
            # Sell: RSI between 50-60 (not extreme) AND strong negative momentum
            elif 50 <= rsi.iloc[i] <= 60 and roc.iloc[i] < -2:
                signals.append(SignalResult(
                    timestamp=idx, signal=SignalType.SELL, price=price,
                    confidence=0.65,
                    stop_loss=price + 1.5 * current_atr,
                    take_profit=price - 2.5 * current_atr,
                    indicators={"rsi": rsi.iloc[i], "roc": roc.iloc[i]},
                    reason="RSI neutral + strong negative momentum"
                ))
        
        return signals


@register_strategy
class RSI_ADX_MeanReversion(ExperimentStrategy):
    """Strategy 18: RSI + ADX (mean reversion only when ADX < threshold)"""
    
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(
            id=18,
            name="RSI + ADX Filter",
            category=StrategyCategory.CATEGORY_B,
            description="RSI mean reversion only in ranging markets (ADX < 25)",
            indicators_used=["RSI", "ADX"],
            min_bars_required=30
        )
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df):
            return []
        
        signals = []
        rsi = TI.rsi(df['close'], 14)
        adx, _, _ = TI.adx(df, 14)
        atr = TI.atr(df, 14)
        
        for i in range(30, len(df)):
            idx = df.index[i]
            price = df['close'].iloc[i]
            current_atr = atr.iloc[i]
            
            # Only trade mean reversion when market is ranging (ADX < 25)
            if adx.iloc[i] < 25:
                # Buy: RSI oversold in ranging market
                if rsi.iloc[i] < 30:
                    signals.append(SignalResult(
                        timestamp=idx, signal=SignalType.BUY, price=price,
                        confidence=0.7,
                        stop_loss=price - 1.5 * current_atr,
                        take_profit=price + 2 * current_atr,
                        indicators={"rsi": rsi.iloc[i], "adx": adx.iloc[i]},
                        reason="RSI oversold in ranging market (ADX < 25)"
                    ))
                # Sell: RSI overbought in ranging market
                elif rsi.iloc[i] > 70:
                    signals.append(SignalResult(
                        timestamp=idx, signal=SignalType.SELL, price=price,
                        confidence=0.7,
                        stop_loss=price + 1.5 * current_atr,
                        take_profit=price - 2 * current_atr,
                        indicators={"rsi": rsi.iloc[i], "adx": adx.iloc[i]},
                        reason="RSI overbought in ranging market (ADX < 25)"
                    ))
        
        return signals


__all__ = [
    'RSI_MACD',
    'RSI_Stochastic',
    'RSI_WilliamsR',
    'MACD_Momentum',
    'MACD_Stochastic',
    'Momentum_MATrend',
    'RSI_PriceMomentum',
    'RSI_ADX_MeanReversion'
]
