"""
Category J - Experimental / Quant Strategies (66-70)
Advanced quantitative strategies with adaptive and experimental logic.
"""

import pandas as pd
from typing import List
from .base import (
    ExperimentStrategy, StrategyInfo, SignalResult, SignalType,
    StrategyCategory, register_strategy
)
from ..indicators.technical import TechnicalIndicators as TI


@register_strategy
class VolatilityExpansion_Momentum(ExperimentStrategy):
    """Strategy 66: Volatility Expansion + Momentum"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=66, name="Volatility Expansion + Momentum", category=StrategyCategory.CATEGORY_J,
            description="Trade when volatility expands from compression with momentum",
            indicators_used=["ATR", "Bollinger Width", "ROC"], min_bars_required=30)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        atr = TI.atr(df, 14)
        atr_sma = TI.sma(atr, 20)
        upper, middle, lower = TI.bollinger_bands(df['close'], 20, 2.0)
        bb_width = (upper - lower) / middle * 100
        bb_width_sma = TI.sma(bb_width, 20)
        roc = TI.roc(df['close'], 5)
        
        for i in range(30, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            # Volatility expansion: ATR and BB width both above average
            if atr.iloc[i] > atr_sma.iloc[i] * 1.3 and bb_width.iloc[i] > bb_width_sma.iloc[i] * 1.2:
                if roc.iloc[i] > 2:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.75,
                        stop_loss=price - 1.5*atr.iloc[i], take_profit=price + 2*atr.iloc[i],
                        indicators={"atr_ratio": atr.iloc[i]/atr_sma.iloc[i], "roc": roc.iloc[i]},
                        reason="Volatility expansion + positive momentum"))
                elif roc.iloc[i] < -2:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.75,
                        stop_loss=price + 1.5*atr.iloc[i], take_profit=price - 2*atr.iloc[i],
                        indicators={"atr_ratio": atr.iloc[i]/atr_sma.iloc[i], "roc": roc.iloc[i]},
                        reason="Volatility expansion + negative momentum"))
        return signals


@register_strategy
class VolatilityCompression_Breakout(ExperimentStrategy):
    """Strategy 67: Volatility Compression → Breakout"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=67, name="Volatility Compression → Breakout", category=StrategyCategory.CATEGORY_J,
            description="Detect volatility squeeze and trade the subsequent breakout",
            indicators_used=["ATR", "Bollinger Width", "Keltner Channel"], min_bars_required=30)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        atr = TI.atr(df, 14)
        atr_sma = TI.sma(atr, 20)
        upper, middle, lower = TI.bollinger_bands(df['close'], 20, 2.0)
        
        # Track squeeze state
        in_squeeze = [False] * len(df)
        for i in range(30, len(df)):
            # Squeeze: ATR at historic lows
            if atr.iloc[i] < atr_sma.iloc[i] * 0.7:
                in_squeeze[i] = True
        
        for i in range(31, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            # Breakout after squeeze
            if in_squeeze[i-1] and not in_squeeze[i]:  # Squeeze just released
                if price > upper.iloc[i-1]:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.78,
                        stop_loss=middle.iloc[i], take_profit=price + 2.5*atr.iloc[i],
                        indicators={"squeeze_release": True},
                        reason="Squeeze breakout (bullish)"))
                elif price < lower.iloc[i-1]:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.78,
                        stop_loss=middle.iloc[i], take_profit=price - 2.5*atr.iloc[i],
                        indicators={"squeeze_release": True},
                        reason="Squeeze breakdown (bearish)"))
        return signals


@register_strategy
class TrendStrengthScore(ExperimentStrategy):
    """Strategy 68: Trend Strength Score (ADX + ROC)"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=68, name="Trend Strength Score", category=StrategyCategory.CATEGORY_J,
            description="Composite trend strength score combining ADX and momentum",
            indicators_used=["ADX", "ROC", "EMA"], min_bars_required=35)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        adx, plus_di, minus_di = TI.adx(df, 14)
        roc = TI.roc(df['close'], 10)
        ema20 = TI.ema(df['close'], 20)
        atr = TI.atr(df, 14)
        
        for i in range(35, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            # Calculate trend strength score (0-100)
            adx_score = min(adx.iloc[i], 50) / 50 * 40  # Max 40 points
            momentum_score = min(abs(roc.iloc[i]), 10) / 10 * 30  # Max 30 points
            trend_alignment = 30 if (price > ema20.iloc[i] and roc.iloc[i] > 0) or (price < ema20.iloc[i] and roc.iloc[i] < 0) else 0
            total_score = adx_score + momentum_score + trend_alignment
            
            if total_score > 70:  # Strong trend
                if plus_di.iloc[i] > minus_di.iloc[i] and roc.iloc[i] > 0:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, 
                        confidence=min(total_score/100, 0.9),
                        stop_loss=price - 2*atr.iloc[i], take_profit=price + 3*atr.iloc[i],
                        indicators={"trend_score": total_score, "adx": adx.iloc[i], "roc": roc.iloc[i]},
                        reason=f"Strong bullish trend (score: {total_score:.0f})"))
                elif minus_di.iloc[i] > plus_di.iloc[i] and roc.iloc[i] < 0:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price,
                        confidence=min(total_score/100, 0.9),
                        stop_loss=price + 2*atr.iloc[i], take_profit=price - 3*atr.iloc[i],
                        indicators={"trend_score": total_score, "adx": adx.iloc[i], "roc": roc.iloc[i]},
                        reason=f"Strong bearish trend (score: {total_score:.0f})"))
        return signals


@register_strategy
class RegimeBased(ExperimentStrategy):
    """Strategy 69: Regime-Based (Trend vs Range switch)"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=69, name="Regime-Based Strategy", category=StrategyCategory.CATEGORY_J,
            description="Automatically switch between trend and mean-reversion based on market regime",
            indicators_used=["ADX", "BB Width", "RSI"], min_bars_required=35)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        adx, plus_di, minus_di = TI.adx(df, 14)
        upper, middle, lower = TI.bollinger_bands(df['close'], 20, 2.0)
        rsi = TI.rsi(df['close'], 14)
        macd_line, signal_line, _ = TI.macd(df['close'])
        atr = TI.atr(df, 14)
        
        for i in range(35, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            
            # Determine regime
            is_trending = adx.iloc[i] > 25
            
            if is_trending:
                # TREND REGIME: Use trend-following logic
                if macd_line.iloc[i-1] <= signal_line.iloc[i-1] and macd_line.iloc[i] > signal_line.iloc[i] and plus_di.iloc[i] > minus_di.iloc[i]:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.75,
                        stop_loss=price - 2*atr.iloc[i], take_profit=price + 3*atr.iloc[i],
                        indicators={"regime": "TREND", "adx": adx.iloc[i]},
                        reason="Trend regime: MACD bullish crossover"))
                elif macd_line.iloc[i-1] >= signal_line.iloc[i-1] and macd_line.iloc[i] < signal_line.iloc[i] and minus_di.iloc[i] > plus_di.iloc[i]:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.75,
                        stop_loss=price + 2*atr.iloc[i], take_profit=price - 3*atr.iloc[i],
                        indicators={"regime": "TREND", "adx": adx.iloc[i]},
                        reason="Trend regime: MACD bearish crossover"))
            else:
                # RANGE REGIME: Use mean-reversion logic
                if price <= lower.iloc[i] and rsi.iloc[i] < 30:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.7,
                        stop_loss=lower.iloc[i] - atr.iloc[i], take_profit=middle.iloc[i],
                        indicators={"regime": "RANGE", "rsi": rsi.iloc[i]},
                        reason="Range regime: Mean reversion buy"))
                elif price >= upper.iloc[i] and rsi.iloc[i] > 70:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.7,
                        stop_loss=upper.iloc[i] + atr.iloc[i], take_profit=middle.iloc[i],
                        indicators={"regime": "RANGE", "rsi": rsi.iloc[i]},
                        reason="Range regime: Mean reversion sell"))
        return signals


@register_strategy
class AdaptiveStrategySelector(ExperimentStrategy):
    """Strategy 70: Adaptive Strategy Selector (best rolling performer)"""
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(id=70, name="Adaptive Strategy Selector", category=StrategyCategory.CATEGORY_J,
            description="Dynamically select between strategies based on recent performance",
            indicators_used=["Multiple (RSI, MACD, ADX, BB)"], min_bars_required=50)
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df): return []
        signals = []
        
        # Calculate all indicators
        rsi = TI.rsi(df['close'], 14)
        macd_line, signal_line, _ = TI.macd(df['close'])
        adx, plus_di, minus_di = TI.adx(df, 14)
        upper, middle, lower = TI.bollinger_bands(df['close'], 20, 2.0)
        atr = TI.atr(df, 14)
        
        # Rolling performance tracking (simplified)
        rsi_score = 0
        macd_score = 0
        adx_score = 0
        
        for i in range(50, len(df)):
            idx, price = df.index[i], df['close'].iloc[i]
            
            # Update rolling scores based on recent price action
            if i > 55:
                price_5_ago = df['close'].iloc[i-5]
                move = (price - price_5_ago) / price_5_ago * 100
                
                # Update scores based on which indicator would have been correct
                if rsi.iloc[i-5] < 30 and move > 0:
                    rsi_score += 1
                elif rsi.iloc[i-5] > 70 and move < 0:
                    rsi_score += 1
                
                if macd_line.iloc[i-5] > signal_line.iloc[i-5] and move > 0:
                    macd_score += 1
                elif macd_line.iloc[i-5] < signal_line.iloc[i-5] and move < 0:
                    macd_score += 1
                    
                if adx.iloc[i-5] > 25 and abs(move) > 1:
                    adx_score += 1
            
            # Select best performing strategy and generate signal
            best_strategy = max([('RSI', rsi_score), ('MACD', macd_score), ('ADX', adx_score)], key=lambda x: x[1])
            
            if best_strategy[0] == 'RSI':
                if rsi.iloc[i] < 30:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.7,
                        stop_loss=price - 2*atr.iloc[i], take_profit=price + 2*atr.iloc[i],
                        indicators={"selected_strategy": "RSI", "rsi": rsi.iloc[i]},
                        reason="Adaptive: RSI strategy selected"))
                elif rsi.iloc[i] > 70:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.7,
                        stop_loss=price + 2*atr.iloc[i], take_profit=price - 2*atr.iloc[i],
                        indicators={"selected_strategy": "RSI", "rsi": rsi.iloc[i]},
                        reason="Adaptive: RSI strategy selected"))
            
            elif best_strategy[0] == 'MACD':
                if macd_line.iloc[i-1] <= signal_line.iloc[i-1] and macd_line.iloc[i] > signal_line.iloc[i]:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.72,
                        stop_loss=price - 2*atr.iloc[i], take_profit=price + 2.5*atr.iloc[i],
                        indicators={"selected_strategy": "MACD", "macd": macd_line.iloc[i]},
                        reason="Adaptive: MACD strategy selected"))
                elif macd_line.iloc[i-1] >= signal_line.iloc[i-1] and macd_line.iloc[i] < signal_line.iloc[i]:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.72,
                        stop_loss=price + 2*atr.iloc[i], take_profit=price - 2.5*atr.iloc[i],
                        indicators={"selected_strategy": "MACD", "macd": macd_line.iloc[i]},
                        reason="Adaptive: MACD strategy selected"))
            
            elif best_strategy[0] == 'ADX':
                if adx.iloc[i] > 25 and plus_di.iloc[i] > minus_di.iloc[i]:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.BUY, price=price, confidence=0.75,
                        stop_loss=price - 2*atr.iloc[i], take_profit=price + 3*atr.iloc[i],
                        indicators={"selected_strategy": "ADX", "adx": adx.iloc[i]},
                        reason="Adaptive: ADX strategy selected"))
                elif adx.iloc[i] > 25 and minus_di.iloc[i] > plus_di.iloc[i]:
                    signals.append(SignalResult(timestamp=idx, signal=SignalType.SELL, price=price, confidence=0.75,
                        stop_loss=price + 2*atr.iloc[i], take_profit=price - 3*atr.iloc[i],
                        indicators={"selected_strategy": "ADX", "adx": adx.iloc[i]},
                        reason="Adaptive: ADX strategy selected"))
        
        return signals


__all__ = ['VolatilityExpansion_Momentum', 'VolatilityCompression_Breakout', 'TrendStrengthScore',
           'RegimeBased', 'AdaptiveStrategySelector']
