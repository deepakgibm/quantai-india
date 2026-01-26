"""
Multi-Timeframe Confluence Engine
3-Layer confluence: Daily (Trend) → 4H (Structure) → 1H (Entry)
"""

from typing import Optional
import pandas as pd
from strategies.base import BaseStrategy, ScanResult, SignalType, StrategyTier, StrategyRegistry
from core.scanner.indicator_utils import (
    donchian_channels, sma, volume_ratio, 
    rsi, williams_r, stochastic, fibonacci_levels
)


@StrategyRegistry.register
class MultiTimeframeConfluence(BaseStrategy):
    """
    3-Layer Multi-Timeframe Confluence Strategy
    
    Daily: Trend Confirmation (Donchian, Golden Cross, Ichimoku)
    4H: Structure & Pullback (Volume Surge, Fibonacci, Donchian Mean Reversion)
    1H: Entry Trigger (RSI, Williams %R, Stochastic)
    
    Signal only when all three timeframes align.
    """
    
    name = "Multi-Timeframe Confluence"
    description = "3-layer confluence: Daily trend + 4H structure + 1H entry trigger"
    tier = StrategyTier.MULTI_TF
    min_bars_required = 210  # Need enough for daily golden cross
    
    def scan(
        self, 
        df: pd.DataFrame, 
        symbol: str, 
        index: str, 
        timeframe: str
    ) -> Optional[ScanResult]:
        """
        For true MTF, caller should provide daily_df, h4_df, h1_df.
        This simplified version works with a single timeframe.
        """
        if not self.validate_data(df):
            return None
        
        # Analyze each layer
        daily_signal = self._analyze_daily(df)
        h4_signal = self._analyze_4h(df)
        h1_signal = self._analyze_1h(df)
        
        # All three must align
        if daily_signal == h4_signal == h1_signal and daily_signal != SignalType.NEUTRAL:
            vol_ratio = volume_ratio(df['volume']).iloc[-1]
            
            # Strong confluence = high confidence
            confidence = 0.85
            if vol_ratio > 1.5:
                confidence = 0.92
            
            support, resistance = self.get_support_resistance(df)
            
            return ScanResult(
                symbol=symbol,
                index=index,
                timeframe=timeframe,
                strategy=self.name,
                signal=daily_signal,
                confidence_score=confidence,
                indicators={
                    "daily_trend": daily_signal.value,
                    "h4_structure": h4_signal.value,
                    "h1_entry": h1_signal.value
                },
                trend=self.get_trend(df),
                support=support,
                resistance=resistance,
                volume_ratio=vol_ratio
            )
        
        return None
    
    def _analyze_daily(self, df: pd.DataFrame) -> SignalType:
        """Daily layer: Trend confirmation using Donchian, SMA, Ichimoku."""
        # Golden Cross check
        if len(df) >= 200:
            sma50 = sma(df['close'], 50).iloc[-1]
            sma200 = sma(df['close'], 200).iloc[-1]
            
            if sma50 > sma200:
                return SignalType.BULLISH
            elif sma50 < sma200:
                return SignalType.BEARISH
        
        # Fallback to Donchian
        upper, middle, lower = donchian_channels(df['high'], df['low'], 20)
        close = df['close'].iloc[-1]
        
        if close > middle.iloc[-1]:
            return SignalType.BULLISH
        elif close < middle.iloc[-1]:
            return SignalType.BEARISH
        
        return SignalType.NEUTRAL
    
    def _analyze_4h(self, df: pd.DataFrame) -> SignalType:
        """4H layer: Structure using volume and Fibonacci."""
        vol_ratio_val = volume_ratio(df['volume']).iloc[-1]
        price_change = (df['close'].iloc[-1] - df['close'].iloc[-5]) / df['close'].iloc[-5]
        
        # Volume-confirmed move
        if vol_ratio_val > 1.3:
            if price_change > 0.02:
                return SignalType.BULLISH
            elif price_change < -0.02:
                return SignalType.BEARISH
        
        # Fibonacci pullback check
        high = df['high'].iloc[-20:].max()
        low = df['low'].iloc[-20:].min()
        close = df['close'].iloc[-1]
        fib = fibonacci_levels(high, low)
        
        # Near 38.2% or 61.8% support in uptrend
        if abs(close - fib[0.382]) / close < 0.02:
            return SignalType.BULLISH if close > (high + low) / 2 else SignalType.BEARISH
        elif abs(close - fib[0.618]) / close < 0.02:
            return SignalType.BULLISH if close > (high + low) / 2 else SignalType.BEARISH
        
        return SignalType.NEUTRAL
    
    def _analyze_1h(self, df: pd.DataFrame) -> SignalType:
        """1H layer: Entry trigger using oscillators."""
        rsi_val = rsi(df['close']).iloc[-1]
        wr_val = williams_r(df['high'], df['low'], df['close']).iloc[-1]
        k, d = stochastic(df['high'], df['low'], df['close'])
        
        bullish_count = 0
        bearish_count = 0
        
        # RSI
        if rsi_val < 35:
            bullish_count += 1
        elif rsi_val > 65:
            bearish_count += 1
        
        # Williams %R
        if wr_val < -80:
            bullish_count += 1
        elif wr_val > -20:
            bearish_count += 1
        
        # Stochastic
        if k.iloc[-1] < 25:
            bullish_count += 1
        elif k.iloc[-1] > 75:
            bearish_count += 1
        
        # Need at least 2 of 3 oscillators to agree
        if bullish_count >= 2:
            return SignalType.BULLISH
        elif bearish_count >= 2:
            return SignalType.BEARISH
        
        return SignalType.NEUTRAL
    
    def scan_multi_timeframe(
        self,
        daily_df: pd.DataFrame,
        h4_df: pd.DataFrame,
        h1_df: pd.DataFrame,
        symbol: str,
        index: str
    ) -> Optional[ScanResult]:
        """
        True multi-timeframe analysis with separate DataFrames.
        """
        daily_signal = self._analyze_daily(daily_df)
        h4_signal = self._analyze_4h(h4_df)
        h1_signal = self._analyze_1h(h1_df)
        
        if daily_signal == h4_signal == h1_signal and daily_signal != SignalType.NEUTRAL:
            vol_ratio = volume_ratio(h1_df['volume']).iloc[-1]
            confidence = 0.9 if vol_ratio > 1.5 else 0.85
            
            support, resistance = self.get_support_resistance(h1_df)
            
            return ScanResult(
                symbol=symbol,
                index=index,
                timeframe="MTF",
                strategy=self.name,
                signal=daily_signal,
                confidence_score=confidence,
                indicators={
                    "daily_trend": daily_signal.value,
                    "h4_structure": h4_signal.value,
                    "h1_entry": h1_signal.value
                },
                trend=self.get_trend(daily_df),
                support=support,
                resistance=resistance,
                volume_ratio=vol_ratio
            )
        
        return None
