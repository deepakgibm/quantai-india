"""
Category A - Single-Logic Baseline Strategies (1-10)
These are foundational strategies using a single core logic.
"""

import pandas as pd
from typing import List
from .base import (
    ExperimentStrategy, StrategyInfo, SignalResult, SignalType,
    StrategyCategory, register_strategy
)
from ..indicators.technical import TechnicalIndicators as TI


@register_strategy
class RSIMeanReversion(ExperimentStrategy):
    """Strategy 1: RSI Mean Reversion"""
    
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(
            id=1,
            name="RSI Mean Reversion",
            category=StrategyCategory.CATEGORY_A,
            description="Buy when RSI is oversold (<30), sell when overbought (>70)",
            indicators_used=["RSI"],
            min_bars_required=20
        )
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df):
            return []
        
        signals = []
        rsi = TI.rsi(df['close'], 14)
        atr = TI.atr(df, 14)
        
        for i in range(20, len(df)):
            idx = df.index[i]
            price = df['close'].iloc[i]
            current_rsi = rsi.iloc[i]
            prev_rsi = rsi.iloc[i-1]
            current_atr = atr.iloc[i]
            
            # Buy signal: RSI crosses above 30
            if prev_rsi <= 30 and current_rsi > 30:
                signals.append(SignalResult(
                    timestamp=idx,
                    signal=SignalType.BUY,
                    price=price,
                    confidence=min((30 - prev_rsi) / 30, 1.0),
                    stop_loss=price - 2 * current_atr,
                    take_profit=price + 3 * current_atr,
                    indicators={"rsi": current_rsi},
                    reason="RSI oversold reversal"
                ))
            # Sell signal: RSI crosses below 70
            elif prev_rsi >= 70 and current_rsi < 70:
                signals.append(SignalResult(
                    timestamp=idx,
                    signal=SignalType.SELL,
                    price=price,
                    confidence=min((prev_rsi - 70) / 30, 1.0),
                    stop_loss=price + 2 * current_atr,
                    take_profit=price - 3 * current_atr,
                    indicators={"rsi": current_rsi},
                    reason="RSI overbought reversal"
                ))
        
        return signals


@register_strategy
class BollingerBreakout(ExperimentStrategy):
    """Strategy 2: Bollinger Bands Breakout"""
    
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(
            id=2,
            name="Bollinger Bands Breakout",
            category=StrategyCategory.CATEGORY_A,
            description="Trade breakouts above/below Bollinger Bands",
            indicators_used=["Bollinger Bands"],
            min_bars_required=25
        )
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df):
            return []
        
        signals = []
        upper, middle, lower = TI.bollinger_bands(df['close'], 20, 2.0)
        atr = TI.atr(df, 14)
        
        for i in range(25, len(df)):
            idx = df.index[i]
            price = df['close'].iloc[i]
            prev_price = df['close'].iloc[i-1]
            current_atr = atr.iloc[i]
            
            # Breakout above upper band
            if prev_price <= upper.iloc[i-1] and price > upper.iloc[i]:
                signals.append(SignalResult(
                    timestamp=idx,
                    signal=SignalType.BUY,
                    price=price,
                    confidence=0.7,
                    stop_loss=middle.iloc[i],
                    take_profit=price + 2 * current_atr,
                    indicators={"bb_upper": upper.iloc[i], "bb_middle": middle.iloc[i]},
                    reason="Bollinger upper band breakout"
                ))
            # Breakdown below lower band
            elif prev_price >= lower.iloc[i-1] and price < lower.iloc[i]:
                signals.append(SignalResult(
                    timestamp=idx,
                    signal=SignalType.SELL,
                    price=price,
                    confidence=0.7,
                    stop_loss=middle.iloc[i],
                    take_profit=price - 2 * current_atr,
                    indicators={"bb_lower": lower.iloc[i], "bb_middle": middle.iloc[i]},
                    reason="Bollinger lower band breakdown"
                ))
        
        return signals


@register_strategy
class DonchianBreakout(ExperimentStrategy):
    """Strategy 3: Donchian Channel Breakout"""
    
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(
            id=3,
            name="Donchian Channel Breakout",
            category=StrategyCategory.CATEGORY_A,
            description="Trade breakouts of 20-period high/low channels",
            indicators_used=["Donchian Channel"],
            min_bars_required=25
        )
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df):
            return []
        
        signals = []
        upper, middle, lower = TI.donchian_channel(df, 20)
        atr = TI.atr(df, 14)
        
        for i in range(25, len(df)):
            idx = df.index[i]
            price = df['close'].iloc[i]
            prev_upper = upper.iloc[i-1]
            prev_lower = lower.iloc[i-1]
            current_atr = atr.iloc[i]
            
            # Breakout above channel
            if price > prev_upper:
                signals.append(SignalResult(
                    timestamp=idx,
                    signal=SignalType.BUY,
                    price=price,
                    confidence=0.75,
                    stop_loss=middle.iloc[i],
                    take_profit=price + 2 * current_atr,
                    indicators={"donchian_upper": upper.iloc[i]},
                    reason="Donchian channel breakout"
                ))
            # Breakdown below channel
            elif price < prev_lower:
                signals.append(SignalResult(
                    timestamp=idx,
                    signal=SignalType.SELL,
                    price=price,
                    confidence=0.75,
                    stop_loss=middle.iloc[i],
                    take_profit=price - 2 * current_atr,
                    indicators={"donchian_lower": lower.iloc[i]},
                    reason="Donchian channel breakdown"
                ))
        
        return signals


@register_strategy
class MACDCrossover(ExperimentStrategy):
    """Strategy 4: MACD Crossover"""
    
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(
            id=4,
            name="MACD Crossover",
            category=StrategyCategory.CATEGORY_A,
            description="Trade MACD line crossing signal line",
            indicators_used=["MACD"],
            min_bars_required=35
        )
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df):
            return []
        
        signals = []
        macd_line, signal_line, histogram = TI.macd(df['close'])
        atr = TI.atr(df, 14)
        
        for i in range(35, len(df)):
            idx = df.index[i]
            price = df['close'].iloc[i]
            current_atr = atr.iloc[i]
            
            # Bullish crossover
            if macd_line.iloc[i-1] <= signal_line.iloc[i-1] and macd_line.iloc[i] > signal_line.iloc[i]:
                signals.append(SignalResult(
                    timestamp=idx,
                    signal=SignalType.BUY,
                    price=price,
                    confidence=0.65,
                    stop_loss=price - 2 * current_atr,
                    take_profit=price + 3 * current_atr,
                    indicators={"macd": macd_line.iloc[i], "macd_signal": signal_line.iloc[i]},
                    reason="MACD bullish crossover"
                ))
            # Bearish crossover
            elif macd_line.iloc[i-1] >= signal_line.iloc[i-1] and macd_line.iloc[i] < signal_line.iloc[i]:
                signals.append(SignalResult(
                    timestamp=idx,
                    signal=SignalType.SELL,
                    price=price,
                    confidence=0.65,
                    stop_loss=price + 2 * current_atr,
                    take_profit=price - 3 * current_atr,
                    indicators={"macd": macd_line.iloc[i], "macd_signal": signal_line.iloc[i]},
                    reason="MACD bearish crossover"
                ))
        
        return signals


@register_strategy
class GoldenCross(ExperimentStrategy):
    """Strategy 5: Moving Average Golden Cross (50/200)"""
    
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(
            id=5,
            name="MA Golden Cross",
            category=StrategyCategory.CATEGORY_A,
            description="Trade 50/200 SMA crossovers",
            indicators_used=["SMA50", "SMA200"],
            min_bars_required=210
        )
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df):
            return []
        
        signals = []
        sma50 = TI.sma(df['close'], 50)
        sma200 = TI.sma(df['close'], 200)
        atr = TI.atr(df, 14)
        
        for i in range(210, len(df)):
            idx = df.index[i]
            price = df['close'].iloc[i]
            current_atr = atr.iloc[i]
            
            # Golden cross
            if sma50.iloc[i-1] <= sma200.iloc[i-1] and sma50.iloc[i] > sma200.iloc[i]:
                signals.append(SignalResult(
                    timestamp=idx,
                    signal=SignalType.BUY,
                    price=price,
                    confidence=0.8,
                    stop_loss=sma200.iloc[i],
                    take_profit=price + 4 * current_atr,
                    indicators={"sma50": sma50.iloc[i], "sma200": sma200.iloc[i]},
                    reason="Golden cross (50 crosses above 200)"
                ))
            # Death cross
            elif sma50.iloc[i-1] >= sma200.iloc[i-1] and sma50.iloc[i] < sma200.iloc[i]:
                signals.append(SignalResult(
                    timestamp=idx,
                    signal=SignalType.SELL,
                    price=price,
                    confidence=0.8,
                    stop_loss=sma200.iloc[i],
                    take_profit=price - 4 * current_atr,
                    indicators={"sma50": sma50.iloc[i], "sma200": sma200.iloc[i]},
                    reason="Death cross (50 crosses below 200)"
                ))
        
        return signals


@register_strategy
class ADXTrendStrength(ExperimentStrategy):
    """Strategy 6: ADX Trend Strength"""
    
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(
            id=6,
            name="ADX Trend Strength",
            category=StrategyCategory.CATEGORY_A,
            description="Trade strong trends using ADX > 25 with DI crossovers",
            indicators_used=["ADX", "+DI", "-DI"],
            min_bars_required=30
        )
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df):
            return []
        
        signals = []
        adx, plus_di, minus_di = TI.adx(df, 14)
        atr = TI.atr(df, 14)
        
        for i in range(30, len(df)):
            idx = df.index[i]
            price = df['close'].iloc[i]
            current_atr = atr.iloc[i]
            
            # Strong trend with bullish DI crossover
            if adx.iloc[i] > 25:
                if plus_di.iloc[i-1] <= minus_di.iloc[i-1] and plus_di.iloc[i] > minus_di.iloc[i]:
                    signals.append(SignalResult(
                        timestamp=idx,
                        signal=SignalType.BUY,
                        price=price,
                        confidence=min(adx.iloc[i] / 50, 1.0),
                        stop_loss=price - 2 * current_atr,
                        take_profit=price + 3 * current_atr,
                        indicators={"adx": adx.iloc[i], "plus_di": plus_di.iloc[i], "minus_di": minus_di.iloc[i]},
                        reason="ADX strong trend with +DI crossover"
                    ))
                elif plus_di.iloc[i-1] >= minus_di.iloc[i-1] and plus_di.iloc[i] < minus_di.iloc[i]:
                    signals.append(SignalResult(
                        timestamp=idx,
                        signal=SignalType.SELL,
                        price=price,
                        confidence=min(adx.iloc[i] / 50, 1.0),
                        stop_loss=price + 2 * current_atr,
                        take_profit=price - 3 * current_atr,
                        indicators={"adx": adx.iloc[i], "plus_di": plus_di.iloc[i], "minus_di": minus_di.iloc[i]},
                        reason="ADX strong trend with -DI crossover"
                    ))
        
        return signals


@register_strategy
class ATRVolatilityBreakout(ExperimentStrategy):
    """Strategy 7: ATR Volatility Breakout"""
    
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(
            id=7,
            name="ATR Volatility Breakout",
            category=StrategyCategory.CATEGORY_A,
            description="Trade breakouts when price moves > 2 ATR from previous close",
            indicators_used=["ATR"],
            min_bars_required=20
        )
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df):
            return []
        
        signals = []
        atr = TI.atr(df, 14)
        
        for i in range(20, len(df)):
            idx = df.index[i]
            price = df['close'].iloc[i]
            prev_close = df['close'].iloc[i-1]
            current_atr = atr.iloc[i-1]  # Use previous ATR for breakout detection
            
            price_change = price - prev_close
            
            # Bullish volatility breakout
            if price_change > 2 * current_atr:
                signals.append(SignalResult(
                    timestamp=idx,
                    signal=SignalType.BUY,
                    price=price,
                    confidence=min(price_change / (3 * current_atr), 1.0),
                    stop_loss=price - 1.5 * current_atr,
                    take_profit=price + 2 * current_atr,
                    indicators={"atr": current_atr, "price_change": price_change},
                    reason="ATR volatility breakout (bullish)"
                ))
            # Bearish volatility breakout
            elif price_change < -2 * current_atr:
                signals.append(SignalResult(
                    timestamp=idx,
                    signal=SignalType.SELL,
                    price=price,
                    confidence=min(abs(price_change) / (3 * current_atr), 1.0),
                    stop_loss=price + 1.5 * current_atr,
                    take_profit=price - 2 * current_atr,
                    indicators={"atr": current_atr, "price_change": price_change},
                    reason="ATR volatility breakout (bearish)"
                ))
        
        return signals


@register_strategy
class IchimokuTrend(ExperimentStrategy):
    """Strategy 8: Ichimoku Trend"""
    
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(
            id=8,
            name="Ichimoku Trend",
            category=StrategyCategory.CATEGORY_A,
            description="Trade based on price position relative to Ichimoku cloud",
            indicators_used=["Ichimoku Cloud"],
            min_bars_required=60
        )
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df):
            return []
        
        signals = []
        ichimoku = TI.ichimoku(df)
        atr = TI.atr(df, 14)
        
        tenkan = ichimoku['tenkan_sen']
        kijun = ichimoku['kijun_sen']
        senkou_a = ichimoku['senkou_a']
        senkou_b = ichimoku['senkou_b']
        
        for i in range(60, len(df)):
            idx = df.index[i]
            price = df['close'].iloc[i]
            current_atr = atr.iloc[i]
            
            cloud_top = max(senkou_a.iloc[i], senkou_b.iloc[i]) if not pd.isna(senkou_a.iloc[i]) else price
            cloud_bottom = min(senkou_a.iloc[i], senkou_b.iloc[i]) if not pd.isna(senkou_a.iloc[i]) else price
            
            # Tenkan/Kijun crossover above cloud
            if price > cloud_top:
                if tenkan.iloc[i-1] <= kijun.iloc[i-1] and tenkan.iloc[i] > kijun.iloc[i]:
                    signals.append(SignalResult(
                        timestamp=idx,
                        signal=SignalType.BUY,
                        price=price,
                        confidence=0.75,
                        stop_loss=kijun.iloc[i],
                        take_profit=price + 3 * current_atr,
                        indicators={"tenkan": tenkan.iloc[i], "kijun": kijun.iloc[i]},
                        reason="Ichimoku bullish crossover above cloud"
                    ))
            # Tenkan/Kijun crossover below cloud
            elif price < cloud_bottom:
                if tenkan.iloc[i-1] >= kijun.iloc[i-1] and tenkan.iloc[i] < kijun.iloc[i]:
                    signals.append(SignalResult(
                        timestamp=idx,
                        signal=SignalType.SELL,
                        price=price,
                        confidence=0.75,
                        stop_loss=kijun.iloc[i],
                        take_profit=price - 3 * current_atr,
                        indicators={"tenkan": tenkan.iloc[i], "kijun": kijun.iloc[i]},
                        reason="Ichimoku bearish crossover below cloud"
                    ))
        
        return signals


@register_strategy
class OBVTrend(ExperimentStrategy):
    """Strategy 9: OBV Trend"""
    
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(
            id=9,
            name="OBV Trend",
            category=StrategyCategory.CATEGORY_A,
            description="Trade based on On-Balance Volume trend confirmation",
            indicators_used=["OBV"],
            min_bars_required=30
        )
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df):
            return []
        
        signals = []
        obv = TI.obv(df)
        obv_sma = TI.sma(obv, 20)
        atr = TI.atr(df, 14)
        
        for i in range(30, len(df)):
            idx = df.index[i]
            price = df['close'].iloc[i]
            current_atr = atr.iloc[i]
            
            # OBV crosses above its SMA (accumulation)
            if obv.iloc[i-1] <= obv_sma.iloc[i-1] and obv.iloc[i] > obv_sma.iloc[i]:
                signals.append(SignalResult(
                    timestamp=idx,
                    signal=SignalType.BUY,
                    price=price,
                    confidence=0.6,
                    stop_loss=price - 2 * current_atr,
                    take_profit=price + 2.5 * current_atr,
                    indicators={"obv": obv.iloc[i]},
                    reason="OBV bullish crossover (accumulation)"
                ))
            # OBV crosses below its SMA (distribution)
            elif obv.iloc[i-1] >= obv_sma.iloc[i-1] and obv.iloc[i] < obv_sma.iloc[i]:
                signals.append(SignalResult(
                    timestamp=idx,
                    signal=SignalType.SELL,
                    price=price,
                    confidence=0.6,
                    stop_loss=price + 2 * current_atr,
                    take_profit=price - 2.5 * current_atr,
                    indicators={"obv": obv.iloc[i]},
                    reason="OBV bearish crossover (distribution)"
                ))
        
        return signals


@register_strategy
class VolumeSurgeBreakout(ExperimentStrategy):
    """Strategy 10: Volume Surge Breakout"""
    
    @property
    def info(self) -> StrategyInfo:
        return StrategyInfo(
            id=10,
            name="Volume Surge Breakout",
            category=StrategyCategory.CATEGORY_A,
            description="Trade breakouts confirmed by volume > 2x average",
            indicators_used=["Volume", "Price"],
            min_bars_required=25
        )
    
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        if not self.validate_data(df):
            return []
        
        signals = []
        vol_ratio = TI.volume_ratio(df, 20)
        atr = TI.atr(df, 14)
        high_20 = df['high'].rolling(20).max()
        low_20 = df['low'].rolling(20).min()
        
        for i in range(25, len(df)):
            idx = df.index[i]
            price = df['close'].iloc[i]
            current_atr = atr.iloc[i]
            
            # Volume surge with price breakout
            if vol_ratio.iloc[i] > 2.0:
                # Bullish breakout
                if price > high_20.iloc[i-1]:
                    signals.append(SignalResult(
                        timestamp=idx,
                        signal=SignalType.BUY,
                        price=price,
                        confidence=min(vol_ratio.iloc[i] / 3, 1.0),
                        stop_loss=price - 1.5 * current_atr,
                        take_profit=price + 2.5 * current_atr,
                        indicators={"volume_ratio": vol_ratio.iloc[i]},
                        reason="Volume surge breakout (bullish)"
                    ))
                # Bearish breakdown
                elif price < low_20.iloc[i-1]:
                    signals.append(SignalResult(
                        timestamp=idx,
                        signal=SignalType.SELL,
                        price=price,
                        confidence=min(vol_ratio.iloc[i] / 3, 1.0),
                        stop_loss=price + 1.5 * current_atr,
                        take_profit=price - 2.5 * current_atr,
                        indicators={"volume_ratio": vol_ratio.iloc[i]},
                        reason="Volume surge breakdown (bearish)"
                    ))
        
        return signals


__all__ = [
    'RSIMeanReversion',
    'BollingerBreakout', 
    'DonchianBreakout',
    'MACDCrossover',
    'GoldenCross',
    'ADXTrendStrength',
    'ATRVolatilityBreakout',
    'IchimokuTrend',
    'OBVTrend',
    'VolumeSurgeBreakout'
]
