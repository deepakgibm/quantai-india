"""
Category I - Pattern + Indicator Strategies (60-65)
Price pattern recognition combined with indicator confirmation.
"""

import pandas as pd
from typing import List
from .base import (
    ExperimentStrategy, StrategyInfo, SignalResult, SignalType,
    StrategyCategory, register_strategy
)
from ..indicators.technical import TechnicalIndicators as TI


@register_strategy
class FlagPennant_Volume(ExperimentStrategy):
    """Strategy 60: Flag/Pennant + Volume"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=60, name="Flag/Pennant + Volume", category=StrategyCategory.CATEGORY_I,
            description="Consolidation breakout (flag pattern) with volume",
            indicators_used=["Price Pattern", "Volume"], min_bars_required=30)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        atr = TI.atr(df, 14)
        vol_ratio = TI.volume_ratio(df, 20)
        
        for i in range(30, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            # Detect consolidation (narrowing range over last 10 bars)
            recent_range = df['high'].iloc[i-10:i].max() - df['low'].iloc[i-10:i].min()
            prior_range = df['high'].iloc[i-20:i-10].max() - df['low'].iloc[i-20:i-10].min()
            
            if recent_range < prior_range * 0.6:  # Consolidation detected
                consolidation_high = df['high'].iloc[i-10:i].max()
                consolidation_low = df['low'].iloc[i-10:i].min()
                
                if price > consolidation_high and vol_ratio.iloc[i] > 1.5:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.72,
                        stop_loss=consolidation_low, take_profit=price + 2*atr.iloc[i],
                        indicators={"vol_ratio": vol_ratio.iloc[i]},
                        reason="Flag breakout + volume"))
                elif price < consolidation_low and vol_ratio.iloc[i] > 1.5:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.72,
                        stop_loss=consolidation_high, take_profit=price - 2*atr.iloc[i],
                        indicators={"vol_ratio": vol_ratio.iloc[i]},
                        reason="Flag breakdown + volume"))
        return signals


@register_strategy
class HeadShoulders_RSIDivergence(ExperimentStrategy):
    """Strategy 61: Head & Shoulders + RSI Divergence"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=61, name="Head & Shoulders + RSI Divergence", category=StrategyCategory.CATEGORY_I,
            description="H&S pattern reversal confirmed by RSI divergence",
            indicators_used=["H&S Pattern", "RSI"], min_bars_required=40)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        rsi = TI.rsi(df['close'], 14)
        atr = TI.atr(df, 14)
        
        for i in range(40, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            # Simplified H&S detection: Look for lower high with RSI divergence
            high_20 = df['high'].iloc[i-20:i].max()
            high_10 = df['high'].iloc[i-10:i].max()
            rsi_20_max = rsi.iloc[i-20:i-10].max()
            rsi_10_max = rsi.iloc[i-10:i].max()
            
            # Potential right shoulder (lower high) with RSI divergence
            if high_10 < high_20 * 0.98 and rsi_10_max < rsi_20_max and rsi.iloc[i] < 50:
                # Neckline break
                support = df['low'].iloc[i-20:i].min()
                if price < support * 1.01:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.7,
                        stop_loss=high_10, take_profit=price - 2.5*atr.iloc[i],
                        indicators={"rsi": rsi.iloc[i]},
                        reason="H&S pattern + RSI divergence"))
            
            # Inverse H&S
            low_20 = df['low'].iloc[i-20:i].min()
            low_10 = df['low'].iloc[i-10:i].min()
            rsi_20_min = rsi.iloc[i-20:i-10].min()
            rsi_10_min = rsi.iloc[i-10:i].min()
            
            if low_10 > low_20 * 1.02 and rsi_10_min > rsi_20_min and rsi.iloc[i] > 50:
                resistance = df['high'].iloc[i-20:i].max()
                if price > resistance * 0.99:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.7,
                        stop_loss=low_10, take_profit=price + 2.5*atr.iloc[i],
                        indicators={"rsi": rsi.iloc[i]},
                        reason="Inverse H&S + RSI divergence"))
        return signals


@register_strategy
class BreakoutRetest_Momentum(ExperimentStrategy):
    """Strategy 62: Breakout Retest + Momentum"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=62, name="Breakout Retest + Momentum", category=StrategyCategory.CATEGORY_I,
            description="Enter on retest of breakout level with momentum confirmation",
            indicators_used=["Breakout Levels", "ROC"], min_bars_required=30)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        roc = TI.roc(df['close'], 5)
        atr = TI.atr(df, 14)
        high_20 = df['high'].rolling(20).max()
        low_20 = df['low'].rolling(20).min()
        
        for i in range(30, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            prev_high = high_20.iloc[i-5]
            prev_low = low_20.iloc[i-5]
            
            # Bullish: Previously broke above, now retesting from above
            if df['close'].iloc[i-2] > prev_high and abs(price - prev_high) < atr.iloc[i] * 0.5 and roc.iloc[i] > 0:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.72,
                    stop_loss=prev_high * 0.98, take_profit=price + 2*atr.iloc[i],
                    indicators={"roc": roc.iloc[i]},
                    reason="Breakout retest + positive momentum"))
            # Bearish: Previously broke below, now retesting from below
            elif df['close'].iloc[i-2] < prev_low and abs(price - prev_low) < atr.iloc[i] * 0.5 and roc.iloc[i] < 0:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.72,
                    stop_loss=prev_low * 1.02, take_profit=price - 2*atr.iloc[i],
                    indicators={"roc": roc.iloc[i]},
                    reason="Breakdown retest + negative momentum"))
        return signals


@register_strategy
class FibonacciBounce_RSI(ExperimentStrategy):
    """Strategy 63: Fibonacci Bounce + RSI"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=63, name="Fibonacci Bounce + RSI", category=StrategyCategory.CATEGORY_I,
            description="Trade bounce from Fibonacci levels with RSI confirmation",
            indicators_used=["Fibonacci Levels", "RSI"], min_bars_required=50)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        rsi = TI.rsi(df['close'], 14)
        atr = TI.atr(df, 14)
        
        for i in range(50, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            # Calculate Fibonacci levels from recent swing
            swing_high = df['high'].iloc[i-50:i-10].max()
            swing_low = df['low'].iloc[i-50:i-10].min()
            fib_levels = TI.fibonacci_levels(swing_high, swing_low)
            
            # Check if price is near 38.2%, 50%, or 61.8% level
            for level_name, level_price in [('382', fib_levels['level_382']), 
                                             ('500', fib_levels['level_500']),
                                             ('618', fib_levels['level_618'])]:
                if abs(price - level_price) < atr.iloc[i] * 0.5:
                    # Bullish bounce (uptrend retracement)
                    if swing_high > swing_low and price > df['close'].iloc[i-1] and rsi.iloc[i] < 60:
                        signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.7,
                            stop_loss=fib_levels['level_786'] if price > fib_levels['level_500'] else swing_low,
                            take_profit=swing_high,
                            indicators={"fib_level": level_name, "rsi": rsi.iloc[i]},
                            reason=f"Fib {level_name} bounce + RSI"))
                        break
        return signals


@register_strategy
class FibonacciBounce_Volume(ExperimentStrategy):
    """Strategy 64: Fibonacci Bounce + Volume"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=64, name="Fibonacci Bounce + Volume", category=StrategyCategory.CATEGORY_I,
            description="Fibonacci level bounce with volume confirmation",
            indicators_used=["Fibonacci Levels", "Volume"], min_bars_required=50)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        vol_ratio = TI.volume_ratio(df, 20)
        atr = TI.atr(df, 14)
        
        for i in range(50, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            swing_high = df['high'].iloc[i-50:i-10].max()
            swing_low = df['low'].iloc[i-50:i-10].min()
            fib_levels = TI.fibonacci_levels(swing_high, swing_low)
            
            for level_name, level_price in [('382', fib_levels['level_382']), 
                                             ('500', fib_levels['level_500']),
                                             ('618', fib_levels['level_618'])]:
                if abs(price - level_price) < atr.iloc[i] * 0.5 and vol_ratio.iloc[i] > 1.3:
                    if price > df['close'].iloc[i-1]:
                        signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.7,
                            stop_loss=level_price * 0.97, take_profit=swing_high * 0.98,
                            indicators={"fib_level": level_name, "vol_ratio": vol_ratio.iloc[i]},
                            reason=f"Fib {level_name} bounce + volume"))
                        break
                    elif price < df['close'].iloc[i-1]:
                        signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.7,
                            stop_loss=level_price * 1.03, take_profit=swing_low * 1.02,
                            indicators={"fib_level": level_name, "vol_ratio": vol_ratio.iloc[i]},
                            reason=f"Fib {level_name} rejection + volume"))
                        break
        return signals


@register_strategy
class SupportResistance_Momentum(ExperimentStrategy):
    """Strategy 65: Support/Resistance + Momentum"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=65, name="S/R + Momentum", category=StrategyCategory.CATEGORY_I,
            description="Trade S/R level breaks with momentum confirmation",
            indicators_used=["S/R Levels", "ROC"], min_bars_required=30)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        roc = TI.roc(df['close'], 5)
        atr = TI.atr(df, 14)
        
        for i in range(30, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            resistance = df['high'].iloc[i-20:i-1].max()
            support = df['low'].iloc[i-20:i-1].min()
            
            # Resistance break with momentum
            if price > resistance and roc.iloc[i] > 1:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.72,
                    stop_loss=resistance * 0.98, take_profit=price + 2*atr.iloc[i],
                    indicators={"roc": roc.iloc[i], "resistance": resistance},
                    reason="Resistance break + momentum"))
            # Support break with momentum
            elif price < support and roc.iloc[i] < -1:
                signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.72,
                    stop_loss=support * 1.02, take_profit=price - 2*atr.iloc[i],
                    indicators={"roc": roc.iloc[i], "support": support},
                    reason="Support break + momentum"))
        return signals


__all__ = ['FlagPennant_Volume', 'HeadShoulders_RSIDivergence', 'BreakoutRetest_Momentum',
           'FibonacciBounce_RSI', 'FibonacciBounce_Volume', 'SupportResistance_Momentum']
