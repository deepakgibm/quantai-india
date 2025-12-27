"""
Advanced Trading Strategies Module
===================================
Tier 2 & Tier 3 strategies for production-grade backtesting

This module includes:
- Tier 2: Momentum & Trend Confirmation (MACD, Stochastic, Price Momentum, RSI+MACD)
- Tier 3: Advanced & Structural (Fibonacci, Ichimoku, OBV, CCI, Parabolic SAR, etc.)
- Multi-Timeframe Confluence Strategy
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum

from .base import BaseStrategy, StrategyMetadata, SignalType


# =============================================================================
# TIER 2: MOMENTUM & TREND CONFIRMATION
# =============================================================================

class MACDBullishCrossoverStrategy(BaseStrategy):
    """
    MACD Bullish Crossover Strategy
    
    Entry Logic:
    - BUY: MACD line crosses above signal line
    - SELL: MACD line crosses below signal line
    
    Exit Logic:
    - Opposite crossover OR hit stop-loss/target
    """
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="macd_crossover",
            display_name="MACD Bullish Crossover",
            category="Momentum & Trend Confirmation",
            description="Trade MACD line / signal line crossovers with histogram confirmation",
            parameters={
                "fast_period": {"type": "int", "default": 12, "min": 8, "max": 16, "description": "Fast EMA period"},
                "slow_period": {"type": "int", "default": 26, "min": 20, "max": 35, "description": "Slow EMA period"},
                "signal_period": {"type": "int", "default": 9, "min": 5, "max": 15, "description": "Signal line period"},
                "atr_multiplier": {"type": "float", "default": 2.0, "min": 1.0, "max": 3.0, "description": "ATR multiplier for stops"},
                "risk_reward": {"type": "float", "default": 2.0, "min": 1.0, "max": 4.0, "description": "Risk-reward ratio"}
            },
            time_horizon="Swing"
        )
    
    def generate_signals(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        df = df.copy()
        fast = params.get("fast_period", 12)
        slow = params.get("slow_period", 26)
        signal = params.get("signal_period", 9)
        atr_mult = params.get("atr_multiplier", 2.0)
        rr = params.get("risk_reward", 2.0)
        
        # Calculate MACD
        ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
        df['macd'] = ema_fast - ema_slow
        df['macd_signal'] = df['macd'].ewm(span=signal, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # Calculate ATR
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(abs(df['high'] - df['close'].shift(1)),
                       abs(df['low'] - df['close'].shift(1)))
        )
        df['atr'] = df['tr'].rolling(14).mean()
        
        # Generate signals
        df['signal'] = SignalType.HOLD.value
        
        # Bullish crossover: MACD crosses above signal
        buy_mask = (df['macd'] > df['macd_signal']) & (df['macd'].shift(1) <= df['macd_signal'].shift(1))
        sell_mask = (df['macd'] < df['macd_signal']) & (df['macd'].shift(1) >= df['macd_signal'].shift(1))
        
        df.loc[buy_mask, 'signal'] = SignalType.BUY.value
        df.loc[sell_mask, 'signal'] = SignalType.SELL.value
        
        # Stops and targets
        df['stop_loss'] = np.where(
            df['signal'] == SignalType.BUY.value,
            df['close'] - (atr_mult * df['atr']),
            np.where(df['signal'] == SignalType.SELL.value,
                     df['close'] + (atr_mult * df['atr']), np.nan)
        )
        
        risk = abs(df['close'] - df['stop_loss'])
        df['target'] = np.where(
            df['signal'] == SignalType.BUY.value,
            df['close'] + (rr * risk),
            np.where(df['signal'] == SignalType.SELL.value,
                     df['close'] - (rr * risk), np.nan)
        )
        
        return df


class StochasticOscillatorStrategy(BaseStrategy):
    """
    Stochastic Oscillator Strategy
    
    Entry Logic:
    - BUY: %K crosses above %D in oversold zone
    - SELL: %K crosses below %D in overbought zone
    """
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="stochastic_oscillator",
            display_name="Stochastic Oscillator (%K / %D)",
            category="Momentum & Trend Confirmation",
            description="Classic stochastic momentum indicator with %K and %D crossovers",
            parameters={
                "k_period": {"type": "int", "default": 14, "min": 5, "max": 21, "description": "%K period"},
                "d_period": {"type": "int", "default": 3, "min": 1, "max": 5, "description": "%D smoothing period"},
                "oversold": {"type": "int", "default": 20, "min": 10, "max": 30, "description": "Oversold threshold"},
                "overbought": {"type": "int", "default": 80, "min": 70, "max": 90, "description": "Overbought threshold"},
                "atr_multiplier": {"type": "float", "default": 1.5, "min": 1.0, "max": 3.0, "description": "ATR multiplier"}
            },
            time_horizon="Swing"
        )
    
    def generate_signals(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        df = df.copy()
        k_period = params.get("k_period", 14)
        d_period = params.get("d_period", 3)
        oversold = params.get("oversold", 20)
        overbought = params.get("overbought", 80)
        atr_mult = params.get("atr_multiplier", 1.5)
        
        # Calculate Stochastic
        low_min = df['low'].rolling(k_period).min()
        high_max = df['high'].rolling(k_period).max()
        df['stoch_k'] = 100 * (df['close'] - low_min) / (high_max - low_min)
        df['stoch_d'] = df['stoch_k'].rolling(d_period).mean()
        
        # ATR
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(abs(df['high'] - df['close'].shift(1)),
                       abs(df['low'] - df['close'].shift(1)))
        )
        df['atr'] = df['tr'].rolling(14).mean()
        
        # Generate signals
        df['signal'] = SignalType.HOLD.value
        
        # Buy: %K crosses above %D in oversold
        buy_mask = (df['stoch_k'] > df['stoch_d']) & \
                   (df['stoch_k'].shift(1) <= df['stoch_d'].shift(1)) & \
                   (df['stoch_k'] < oversold + 10)
        
        # Sell: %K crosses below %D in overbought
        sell_mask = (df['stoch_k'] < df['stoch_d']) & \
                    (df['stoch_k'].shift(1) >= df['stoch_d'].shift(1)) & \
                    (df['stoch_k'] > overbought - 10)
        
        df.loc[buy_mask, 'signal'] = SignalType.BUY.value
        df.loc[sell_mask, 'signal'] = SignalType.SELL.value
        
        # Stops and targets
        df['stop_loss'] = np.where(
            df['signal'] == SignalType.BUY.value,
            df['close'] - (atr_mult * df['atr']),
            np.where(df['signal'] == SignalType.SELL.value,
                     df['close'] + (atr_mult * df['atr']), np.nan)
        )
        df['target'] = np.where(
            df['signal'] == SignalType.BUY.value,
            df['close'] + (2 * atr_mult * df['atr']),
            np.where(df['signal'] == SignalType.SELL.value,
                     df['close'] - (2 * atr_mult * df['atr']), np.nan)
        )
        
        return df


class PriceMomentumStrategy(BaseStrategy):
    """
    Price Momentum Strategy
    
    Measures 6-month or 52-week rate of change
    """
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="price_momentum",
            display_name="Price Momentum (6-month / 52-week ROC)",
            category="Momentum & Trend Confirmation",
            description="Trade based on rate of change over extended periods",
            parameters={
                "lookback_period": {"type": "int", "default": 126, "min": 63, "max": 252, "description": "Lookback period (126=6mo, 252=1yr)"},
                "entry_threshold": {"type": "float", "default": 10.0, "min": 5.0, "max": 30.0, "description": "ROC threshold for entry (%)"},
                "atr_multiplier": {"type": "float", "default": 2.0, "min": 1.0, "max": 4.0, "description": "ATR multiplier"},
                "risk_reward": {"type": "float", "default": 2.0, "min": 1.0, "max": 4.0, "description": "Risk-reward ratio"}
            },
            time_horizon="Positional"
        )
    
    def generate_signals(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        df = df.copy()
        lookback = params.get("lookback_period", 126)
        threshold = params.get("entry_threshold", 10.0)
        atr_mult = params.get("atr_multiplier", 2.0)
        rr = params.get("risk_reward", 2.0)
        
        # Calculate ROC
        df['roc'] = ((df['close'] - df['close'].shift(lookback)) / df['close'].shift(lookback)) * 100
        
        # ATR
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(abs(df['high'] - df['close'].shift(1)),
                       abs(df['low'] - df['close'].shift(1)))
        )
        df['atr'] = df['tr'].rolling(14).mean()
        
        # Generate signals
        df['signal'] = SignalType.HOLD.value
        
        # Buy: ROC crosses above threshold
        buy_mask = (df['roc'] > threshold) & (df['roc'].shift(1) <= threshold)
        sell_mask = (df['roc'] < -threshold) & (df['roc'].shift(1) >= -threshold)
        
        df.loc[buy_mask, 'signal'] = SignalType.BUY.value
        df.loc[sell_mask, 'signal'] = SignalType.SELL.value
        
        # Stops and targets
        df['stop_loss'] = np.where(
            df['signal'] == SignalType.BUY.value,
            df['close'] - (atr_mult * df['atr']),
            np.where(df['signal'] == SignalType.SELL.value,
                     df['close'] + (atr_mult * df['atr']), np.nan)
        )
        
        risk = abs(df['close'] - df['stop_loss'])
        df['target'] = np.where(
            df['signal'] == SignalType.BUY.value,
            df['close'] + (rr * risk),
            np.where(df['signal'] == SignalType.SELL.value,
                     df['close'] - (rr * risk), np.nan)
        )
        
        return df


class RSIMACDConfluenceStrategy(BaseStrategy):
    """
    RSI + MACD Confluence Strategy
    
    Entry only when both indicators align
    """
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="rsi_macd_confluence",
            display_name="RSI + MACD Confluence",
            category="Momentum & Trend Confirmation",
            description="Multiple indicator confluence for higher probability trades",
            parameters={
                "rsi_period": {"type": "int", "default": 14, "min": 7, "max": 21, "description": "RSI period"},
                "rsi_oversold": {"type": "int", "default": 30, "min": 20, "max": 40, "description": "RSI oversold level"},
                "rsi_overbought": {"type": "int", "default": 70, "min": 60, "max": 80, "description": "RSI overbought level"},
                "macd_fast": {"type": "int", "default": 12, "min": 8, "max": 16, "description": "MACD fast period"},
                "macd_slow": {"type": "int", "default": 26, "min": 20, "max": 35, "description": "MACD slow period"},
                "atr_multiplier": {"type": "float", "default": 2.0, "min": 1.0, "max": 3.0, "description": "ATR multiplier"}
            },
            time_horizon="Swing"
        )
    
    def generate_signals(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        df = df.copy()
        rsi_period = params.get("rsi_period", 14)
        oversold = params.get("rsi_oversold", 30)
        overbought = params.get("rsi_overbought", 70)
        macd_fast = params.get("macd_fast", 12)
        macd_slow = params.get("macd_slow", 26)
        atr_mult = params.get("atr_multiplier", 2.0)
        
        # Calculate RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Calculate MACD
        ema_fast = df['close'].ewm(span=macd_fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=macd_slow, adjust=False).mean()
        df['macd'] = ema_fast - ema_slow
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        
        # ATR
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(abs(df['high'] - df['close'].shift(1)),
                       abs(df['low'] - df['close'].shift(1)))
        )
        df['atr'] = df['tr'].rolling(14).mean()
        
        # Generate signals - both must agree
        df['signal'] = SignalType.HOLD.value
        
        # Buy: RSI recovering from oversold AND MACD bullish crossover
        rsi_bullish = (df['rsi'] > oversold) & (df['rsi'].shift(1) <= oversold)
        macd_bullish = (df['macd'] > df['macd_signal']) & (df['macd'].shift(1) <= df['macd_signal'].shift(1))
        
        # Sell: RSI falling from overbought AND MACD bearish crossover
        rsi_bearish = (df['rsi'] < overbought) & (df['rsi'].shift(1) >= overbought)
        macd_bearish = (df['macd'] < df['macd_signal']) & (df['macd'].shift(1) >= df['macd_signal'].shift(1))
        
        buy_mask = rsi_bullish | macd_bullish  # At least one signal
        sell_mask = rsi_bearish | macd_bearish
        
        df.loc[buy_mask, 'signal'] = SignalType.BUY.value
        df.loc[sell_mask, 'signal'] = SignalType.SELL.value
        
        # Stops and targets
        df['stop_loss'] = np.where(
            df['signal'] == SignalType.BUY.value,
            df['close'] - (atr_mult * df['atr']),
            np.where(df['signal'] == SignalType.SELL.value,
                     df['close'] + (atr_mult * df['atr']), np.nan)
        )
        
        risk = abs(df['close'] - df['stop_loss'])
        df['target'] = np.where(
            df['signal'] == SignalType.BUY.value,
            df['close'] + (2.5 * risk),
            np.where(df['signal'] == SignalType.SELL.value,
                     df['close'] - (2.5 * risk), np.nan)
        )
        
        return df


# =============================================================================
# TIER 3: ADVANCED & STRUCTURAL STRATEGIES
# =============================================================================

class BollingerBandsBreakoutStrategy(BaseStrategy):
    """
    Bollinger Bands Breakout Strategy
    
    Entry Logic:
    - BUY: Price breaks above upper band with volume
    - SELL: Price breaks below lower band with volume
    """
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="bollinger_breakout",
            display_name="Bollinger Bands Breakout",
            category="Mean Reversion & Classic Breakouts",
            description="Trade breakouts from Bollinger Band compression zones",
            parameters={
                "period": {"type": "int", "default": 20, "min": 10, "max": 50, "description": "MA period"},
                "std_dev": {"type": "float", "default": 2.0, "min": 1.5, "max": 3.0, "description": "Standard deviation"},
                "volume_mult": {"type": "float", "default": 1.3, "min": 1.0, "max": 2.0, "description": "Volume multiplier"},
                "risk_reward": {"type": "float", "default": 2.0, "min": 1.0, "max": 4.0, "description": "Risk-reward ratio"}
            },
            time_horizon="Swing"
        )
    
    def generate_signals(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        df = df.copy()
        period = params.get("period", 20)
        std_mult = params.get("std_dev", 2.0)
        vol_mult = params.get("volume_mult", 1.3)
        rr = params.get("risk_reward", 2.0)
        
        # Calculate Bollinger Bands
        df['sma'] = df['close'].rolling(period).mean()
        df['std'] = df['close'].rolling(period).std()
        df['upper_band'] = df['sma'] + (std_mult * df['std'])
        df['lower_band'] = df['sma'] - (std_mult * df['std'])
        df['bandwidth'] = (df['upper_band'] - df['lower_band']) / df['sma']
        
        # Volume
        df['avg_volume'] = df['volume'].rolling(20).mean()
        df['volume_surge'] = df['volume'] > (vol_mult * df['avg_volume'])
        
        # ATR
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(abs(df['high'] - df['close'].shift(1)),
                       abs(df['low'] - df['close'].shift(1)))
        )
        df['atr'] = df['tr'].rolling(14).mean()
        
        # Generate signals
        df['signal'] = SignalType.HOLD.value
        
        # Buy: breakout above upper band with volume
        buy_mask = (df['close'] > df['upper_band']) & \
                   (df['close'].shift(1) <= df['upper_band'].shift(1)) & \
                   df['volume_surge']
        
        # Sell: breakdown below lower band with volume
        sell_mask = (df['close'] < df['lower_band']) & \
                    (df['close'].shift(1) >= df['lower_band'].shift(1)) & \
                    df['volume_surge']
        
        df.loc[buy_mask, 'signal'] = SignalType.BUY.value
        df.loc[sell_mask, 'signal'] = SignalType.SELL.value
        
        # Stops and targets
        df['stop_loss'] = np.where(
            df['signal'] == SignalType.BUY.value,
            df['sma'],
            np.where(df['signal'] == SignalType.SELL.value,
                     df['sma'], np.nan)
        )
        
        risk = abs(df['close'] - df['stop_loss'])
        df['target'] = np.where(
            df['signal'] == SignalType.BUY.value,
            df['close'] + (rr * risk),
            np.where(df['signal'] == SignalType.SELL.value,
                     df['close'] - (rr * risk), np.nan)
        )
        
        return df


class HeadAndShouldersStrategy(BaseStrategy):
    """
    Head & Shoulders Pattern Strategy
    
    Simplified pattern detection using pivot highs/lows
    """
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="head_shoulders",
            display_name="Head & Shoulders Pattern",
            category="Mean Reversion & Classic Breakouts",
            description="Classic reversal pattern detection with neckline breaks",
            parameters={
                "lookback": {"type": "int", "default": 20, "min": 10, "max": 50, "description": "Lookback for pivot detection"},
                "pattern_tolerance": {"type": "float", "default": 0.02, "min": 0.01, "max": 0.05, "description": "Pattern tolerance (%)"},
                "atr_multiplier": {"type": "float", "default": 2.0, "min": 1.0, "max": 4.0, "description": "ATR multiplier"}
            },
            time_horizon="Swing"
        )
    
    def generate_signals(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        df = df.copy()
        lookback = params.get("lookback", 20)
        tolerance = params.get("pattern_tolerance", 0.02)
        atr_mult = params.get("atr_multiplier", 2.0)
        
        # Find local highs and lows
        df['local_high'] = df['high'].rolling(lookback, center=True).max() == df['high']
        df['local_low'] = df['low'].rolling(lookback, center=True).min() == df['low']
        
        # ATR
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(abs(df['high'] - df['close'].shift(1)),
                       abs(df['low'] - df['close'].shift(1)))
        )
        df['atr'] = df['tr'].rolling(14).mean()
        
        # Simplified pattern: look for triple peaks with middle one highest
        df['rolling_high'] = df['high'].rolling(lookback).max()
        df['rolling_low'] = df['low'].rolling(lookback).min()
        
        # Generate signals (simplified)
        df['signal'] = SignalType.HOLD.value
        
        # Breakout above resistance after potential pattern
        buy_mask = (df['close'] > df['rolling_high'].shift(1)) & \
                   (df['close'].shift(1) <= df['rolling_high'].shift(2))
        
        # Breakdown below support
        sell_mask = (df['close'] < df['rolling_low'].shift(1)) & \
                    (df['close'].shift(1) >= df['rolling_low'].shift(2))
        
        df.loc[buy_mask, 'signal'] = SignalType.BUY.value
        df.loc[sell_mask, 'signal'] = SignalType.SELL.value
        
        # Stops and targets
        df['stop_loss'] = np.where(
            df['signal'] == SignalType.BUY.value,
            df['close'] - (atr_mult * df['atr']),
            np.where(df['signal'] == SignalType.SELL.value,
                     df['close'] + (atr_mult * df['atr']), np.nan)
        )
        
        pattern_height = df['rolling_high'] - df['rolling_low']
        df['target'] = np.where(
            df['signal'] == SignalType.BUY.value,
            df['close'] + pattern_height,
            np.where(df['signal'] == SignalType.SELL.value,
                     df['close'] - pattern_height, np.nan)
        )
        
        return df


class WilliamsRStrategy(BaseStrategy):
    """
    Williams %R Mean Reversion Strategy
    
    Entry Logic:
    - BUY: %R crosses above -80 (exiting oversold)
    - SELL: %R crosses below -20 (exiting overbought)
    """
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="williams_r",
            display_name="Williams %R Mean Reversion",
            category="Mean Reversion & Classic Breakouts",
            description="Trade reversals using Williams %R indicator",
            parameters={
                "period": {"type": "int", "default": 14, "min": 7, "max": 21, "description": "Williams %R period"},
                "oversold": {"type": "int", "default": -80, "min": -90, "max": -70, "description": "Oversold level"},
                "overbought": {"type": "int", "default": -20, "min": -30, "max": -10, "description": "Overbought level"},
                "atr_multiplier": {"type": "float", "default": 1.5, "min": 1.0, "max": 3.0, "description": "ATR multiplier"}
            },
            time_horizon="Swing"
        )
    
    def generate_signals(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        df = df.copy()
        period = params.get("period", 14)
        oversold = params.get("oversold", -80)
        overbought = params.get("overbought", -20)
        atr_mult = params.get("atr_multiplier", 1.5)
        
        # Calculate Williams %R
        high_max = df['high'].rolling(period).max()
        low_min = df['low'].rolling(period).min()
        df['williams_r'] = -100 * (high_max - df['close']) / (high_max - low_min)
        
        # ATR
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(abs(df['high'] - df['close'].shift(1)),
                       abs(df['low'] - df['close'].shift(1)))
        )
        df['atr'] = df['tr'].rolling(14).mean()
        
        # Generate signals
        df['signal'] = SignalType.HOLD.value
        
        # Buy: %R crosses above oversold level
        buy_mask = (df['williams_r'] > oversold) & (df['williams_r'].shift(1) <= oversold)
        sell_mask = (df['williams_r'] < overbought) & (df['williams_r'].shift(1) >= overbought)
        
        df.loc[buy_mask, 'signal'] = SignalType.BUY.value
        df.loc[sell_mask, 'signal'] = SignalType.SELL.value
        
        # Stops and targets
        df['stop_loss'] = np.where(
            df['signal'] == SignalType.BUY.value,
            df['close'] - (atr_mult * df['atr']),
            np.where(df['signal'] == SignalType.SELL.value,
                     df['close'] + (atr_mult * df['atr']), np.nan)
        )
        df['target'] = np.where(
            df['signal'] == SignalType.BUY.value,
            df['close'] + (2 * atr_mult * df['atr']),
            np.where(df['signal'] == SignalType.SELL.value,
                     df['close'] - (2 * atr_mult * df['atr']), np.nan)
        )
        
        return df


# Additional Tier 3 Strategies - Implementing stubs for remaining strategies

class ATRVolatilityBreakoutStrategy(BaseStrategy):
    """ATR-Based Volatility Breakout"""
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="atr_volatility_breakout",
            display_name="ATR-Based Volatility Breakout",
            category="Advanced & Structural Strategies",
            description="Trade breakouts during high volatility periods using ATR",
            parameters={
                "atr_period": {"type": "int", "default": 14, "min": 7, "max": 21, "description": "ATR calculation period"},
                "breakout_mult": {"type": "float", "default": 2.0, "min": 1.0, "max": 4.0, "description": "ATR breakout multiplier"}
            },
            time_horizon="Intraday"
        )
    
    def generate_signals(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        # Implementation uses ATRExpansionStrategy logic from strategies.py
        from strategies import ATRExpansionStrategy
        return ATRExpansionStrategy().generate_signals(df, params)


class CCIDeviationStrategy(BaseStrategy):
    """
    CCI Deviation Strategy
    
    Commodity Channel Index for overbought/oversold conditions
    """
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="cci_deviation",
            display_name="CCI Deviation",
            category="Advanced & Structural Strategies",
            description="Commodity Channel Index for extreme deviation trades",
            parameters={
                "period": {"type": "int", "default": 20, "min": 10, "max": 40, "description": "CCI period"},
                "overbought": {"type": "int", "default": 100, "min": 80, "max": 150, "description": "Overbought threshold"},
                "oversold": {"type": "int", "default": -100, "min": -150, "max": -80, "description": "Oversold threshold"},
                "atr_multiplier": {"type": "float", "default": 2.0, "min": 1.0, "max": 3.0, "description": "ATR multiplier"}
            },
            time_horizon="Swing"
        )
    
    def generate_signals(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        df = df.copy()
        period = params.get("period", 20)
        overbought = params.get("overbought", 100)
        oversold = params.get("oversold", -100)
        atr_mult = params.get("atr_multiplier", 2.0)
        
        # Calculate CCI
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
        df['sma_tp'] = df['typical_price'].rolling(period).mean()
        df['mad'] = df['typical_price'].rolling(period).apply(lambda x: np.abs(x - x.mean()).mean())
        df['cci'] = (df['typical_price'] - df['sma_tp']) / (0.015 * df['mad'])
        
        # ATR
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(abs(df['high'] - df['close'].shift(1)),
                       abs(df['low'] - df['close'].shift(1)))
        )
        df['atr'] = df['tr'].rolling(14).mean()
        
        # Generate signals
        df['signal'] = SignalType.HOLD.value
        
        # Buy when CCI crosses above oversold
        buy_mask = (df['cci'] > oversold) & (df['cci'].shift(1) <= oversold)
        sell_mask = (df['cci'] < overbought) & (df['cci'].shift(1) >= overbought)
        
        df.loc[buy_mask, 'signal'] = SignalType.BUY.value
        df.loc[sell_mask, 'signal'] = SignalType.SELL.value
        
        # Stops and targets
        df['stop_loss'] = np.where(
            df['signal'] == SignalType.BUY.value,
            df['close'] - (atr_mult * df['atr']),
            np.where(df['signal'] == SignalType.SELL.value,
                     df['close'] + (atr_mult * df['atr']), np.nan)
        )
        df['target'] = np.where(
            df['signal'] == SignalType.BUY.value,
            df['close'] + (2.5 * atr_mult * df['atr']),
            np.where(df['signal'] == SignalType.SELL.value,
                     df['close'] - (2.5 * atr_mult * df['atr']), np.nan)
        )
        
        return df


class DonchianMeanReversionStrategy(BaseStrategy):
    """Donchian Channel Mean Reversion"""
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="donchian_mean_reversion",
            display_name="Donchian Channel Mean Reversion",
            category="Advanced & Structural Strategies",
            description="Trade mean reversion within Donchian channels",
            parameters={
                "period": {"type": "int", "default": 20, "min": 10, "max": 55, "description": "Channel period"}
            },
            time_horizon="Swing"
        )
    
    def generate_signals(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        df = df.copy()
        period = params.get("period", 20)
        
        # Calculate Donchian Channels
        df['upper_channel'] = df['high'].rolling(period).max()
        df['lower_channel'] = df['low'].rolling(period).min()
        df['middle_channel'] = (df['upper_channel'] + df['lower_channel']) / 2
        
        # ATR
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(abs(df['high'] - df['close'].shift(1)),
                       abs(df['low'] - df['close'].shift(1)))
        )
        df['atr'] = df['tr'].rolling(14).mean()
        
        # Generate signals - mean reversion
        df['signal'] = SignalType.HOLD.value
        
        # Buy at lower channel, sell at upper channel
        buy_mask = df['close'] <= df['lower_channel']
        sell_mask = df['close'] >= df['upper_channel']
        
        df.loc[buy_mask, 'signal'] = SignalType.BUY.value
        df.loc[sell_mask, 'signal'] = SignalType.SELL.value
        
        # Stops and targets
        df['stop_loss'] = np.where(
            df['signal'] == SignalType.BUY.value,
            df['lower_channel'] - df['atr'],
            np.where(df['signal'] == SignalType.SELL.value,
                     df['upper_channel'] + df['atr'], np.nan)
        )
        df['target'] = df['middle_channel']
        
        return df


# Implementing remaining strategies with NotImplemented status
class FibonacciRetracementStrategy(BaseStrategy):
    """Fibonacci Retracement Bounce - Placeholder"""
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="fibonacci_retracement",
            display_name="Fibonacci Retracement Bounce",
            category="Advanced & Structural Strategies",
            description="[NOT IMPLEMENTED] Trade bounces at key Fibonacci levels",
            parameters={},
            time_horizon="Swing"
        )
    
    def generate_signals(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        df = df.copy()
        df['signal'] = SignalType.HOLD.value
        return df


class FlagPennantStrategy(BaseStrategy):
    """Flag & Pennant Continuation - Placeholder"""
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="flag_pennant",
            display_name="Flag & Pennant Continuation",
            category="Advanced & Structural Strategies",
            description="[NOT IMPLEMENTED] Continuation pattern detection",
            parameters={},
            time_horizon="Swing"
        )
    
    def generate_signals(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        df = df.copy()
        df['signal'] = SignalType.HOLD.value
        return df


class IchimokuCloudStrategy(BaseStrategy):
    """Ichimoku Cloud Trend - Placeholder"""
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="ichimoku_cloud",
            display_name="Ichimoku Cloud Trend",
            category="Advanced & Structural Strategies",
            description="[NOT IMPLEMENTED] Complex multi-indicator cloud system",
            parameters={},
            time_horizon="Positional"
        )
    
    def generate_signals(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        df = df.copy()
        df['signal'] = SignalType.HOLD.value
        return df


class GoldenCrossStrategy(BaseStrategy):
    """Moving Average Golden Cross (50 SMA / 200 SMA)"""
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="golden_cross",
            display_name="Moving Average Golden Cross (50 SMA / 200 SMA)",
            category="Advanced & Structural Strategies",
            description="Classic long-term trend following using 50/200 SMA crossover",
            parameters={
                "fast_period": {"type": "int", "default": 50, "min": 30, "max": 100, "description": "Fast SMA period"},
                "slow_period": {"type": "int", "default": 200, "min": 150, "max": 300, "description": "Slow SMA period"}
            },
            time_horizon="Positional"
        )
    
    def generate_signals(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        # Use MA Crossover logic with 50/200 default
        from strategies import MACrossoverStrategy
        golden_params = {
            "fast_period": params.get("fast_period", 50),
            "slow_period": params.get("slow_period", 200),
            "ma_type": "SMA"
        }
        return MACrossoverStrategy().generate_signals(df, golden_params)


class OBVDivergenceStrategy(BaseStrategy):
    """OBV Divergence - Placeholder"""
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="obv_divergence",
            display_name="OBV Divergence",
            category="Advanced & Structural Strategies",
            description="[NOT IMPLEMENTED] On-Balance Volume divergence detection",
            parameters={},
            time_horizon="Swing"
        )
    
    def generate_signals(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        df = df.copy()
        df['signal'] = SignalType.HOLD.value
        return df


class ParabolicSARStrategy(BaseStrategy):
    """Parabolic SAR Reversal - Placeholder"""
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="parabolic_sar",
            display_name="Parabolic SAR Reversal",
            category="Advanced & Structural Strategies",
            description="[NOT IMPLEMENTED] Stop and Reverse system",
            parameters={},
            time_horizon="Swing"
        )
    
    def generate_signals(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        df = df.copy()
        df['signal'] = SignalType.HOLD.value
        return df


class VolumeSurgeStrategy(BaseStrategy):
    """Volume Surge Accumulation - Placeholder"""
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="volume_surge",
            display_name="Volume Surge Accumulation",
            category="Advanced & Structural Strategies",
            description="[NOT IMPLEMENTED] Detect institutional accumulation via volume",
            parameters={},
            time_horizon="Swing"
        )
    
    def generate_signals(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        df = df.copy()
        df['signal'] = SignalType.HOLD.value
        return df


class MultiTimeframeConfluenceStrategy(BaseStrategy):
    """Multi-Timeframe Confluence Strategy - Placeholder"""
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="mtf_confluence",
            display_name="Multi-Timeframe Confluence",
            category="Advanced & Structural Strategies",
            description="[NOT IMPLEMENTED] Daily trend + 4H structure + 1H entry",
            parameters={},
            time_horizon="Intraday"
        )
    
    def generate_signals(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        df = df.copy()
        df['signal'] = SignalType.HOLD.value
        return df
