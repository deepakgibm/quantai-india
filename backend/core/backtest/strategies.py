"""
Enhanced Backtest Strategies Module
====================================
Industry-standard trading strategies with proper entry/exit logic,
stop-loss/target rules, and configurable parameters.

Strategy Categories:
1. Trend & Momentum (MA Crossover, SuperTrend, ADX, Donchian)
2. Mean Reversion (RSI, Bollinger Bands, Z-Score)
3. Breakout & Volatility (ORB, Volume Breakout, ATR Expansion)
4. VWAP & Institutional (VWAP Pullback, VWAP Trend)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
from enum import Enum


class SignalType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class TradeSignal:
    """Standard trade signal structure."""
    timestamp: str
    signal: SignalType
    entry_price: float
    stop_loss: float
    target_1: float
    target_2: Optional[float] = None
    confidence: float = 0.0
    reason: str = ""


@dataclass
class StrategyMetadata:
    """Strategy metadata for UI display."""
    name: str
    display_name: str
    category: str
    description: str
    parameters: Dict[str, Dict[str, Any]]
    time_horizon: str  # "Intraday", "Swing", "Positional"


class BaseStrategy(ABC):
    """Abstract base class for all strategies."""
    
    @property
    @abstractmethod
    def metadata(self) -> StrategyMetadata:
        """Return strategy metadata."""
        pass
    
    @abstractmethod
    def generate_signals(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        """
        Generate trading signals.
        
        Args:
            df: OHLCV DataFrame with columns [timestamp, open, high, low, close, volume]
            params: Strategy-specific parameters
            
        Returns:
            DataFrame with additional signal columns
        """
        pass
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate common indicators. Override in subclass if needed."""
        return df.copy()


# =============================================================================
# TREND & MOMENTUM STRATEGIES
# =============================================================================

class MACrossoverStrategy(BaseStrategy):
    """
    Moving Average Crossover Strategy
    
    Entry Logic:
    - BUY: Fast MA crosses above Slow MA
    - SELL: Fast MA crosses below Slow MA
    
    Exit Logic:
    - Opposite crossover OR hit stop-loss/target
    
    Stop-Loss: ATR-based or fixed percentage
    Target: Risk-reward ratio based
    """
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="ma_crossover",
            display_name="Moving Average Crossover",
            category="Trend & Momentum",
            description="Classic SMA/EMA crossover strategy with trend confirmation",
            parameters={
                "fast_period": {"type": "int", "default": 9, "min": 5, "max": 50, "description": "Fast MA period"},
                "slow_period": {"type": "int", "default": 21, "min": 10, "max": 200, "description": "Slow MA period"},
                "ma_type": {"type": "select", "default": "EMA", "options": ["SMA", "EMA"], "description": "Moving average type"},
                "atr_multiplier": {"type": "float", "default": 2.0, "min": 1.0, "max": 5.0, "description": "ATR multiplier for stop-loss"},
                "risk_reward": {"type": "float", "default": 2.0, "min": 1.0, "max": 5.0, "description": "Risk-reward ratio for target"}
            },
            time_horizon="Swing"
        )
    
    def generate_signals(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        df = df.copy()
        fast = params.get("fast_period", 9)
        slow = params.get("slow_period", 21)
        ma_type = params.get("ma_type", "EMA")
        atr_mult = params.get("atr_multiplier", 2.0)
        rr = params.get("risk_reward", 2.0)
        
        # Calculate MAs
        if ma_type == "EMA":
            df['fast_ma'] = df['close'].ewm(span=fast, adjust=False).mean()
            df['slow_ma'] = df['close'].ewm(span=slow, adjust=False).mean()
        else:
            df['fast_ma'] = df['close'].rolling(fast).mean()
            df['slow_ma'] = df['close'].rolling(slow).mean()
        
        # Calculate ATR for stops
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        df['atr'] = df['tr'].rolling(14).mean()
        
        # Generate signals
        df['signal'] = SignalType.HOLD.value
        df['crossover'] = (df['fast_ma'] > df['slow_ma']).astype(int).diff()
        
        # BUY on golden cross
        buy_mask = df['crossover'] == 1
        df.loc[buy_mask, 'signal'] = SignalType.BUY.value
        
        # SELL on death cross
        sell_mask = df['crossover'] == -1
        df.loc[sell_mask, 'signal'] = SignalType.SELL.value
        
        # Calculate stops and targets
        df['stop_loss'] = np.where(
            df['signal'] == SignalType.BUY.value,
            df['close'] - (atr_mult * df['atr']),
            np.where(
                df['signal'] == SignalType.SELL.value,
                df['close'] + (atr_mult * df['atr']),
                np.nan
            )
        )
        
        df['target'] = np.where(
            df['signal'] == SignalType.BUY.value,
            df['close'] + (rr * atr_mult * df['atr']),
            np.where(
                df['signal'] == SignalType.SELL.value,
                df['close'] - (rr * atr_mult * df['atr']),
                np.nan
            )
        )
        
        return df


class SuperTrendStrategy(BaseStrategy):
    """
    SuperTrend Strategy
    
    Popular indicator that adapts to volatility using ATR.
    
    Entry Logic:
    - BUY: Price closes above SuperTrend line (trend turns bullish)
    - SELL: Price closes below SuperTrend line (trend turns bearish)
    """
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="supertrend",
            display_name="SuperTrend",
            category="Trend & Momentum",
            description="ATR-based trailing stop system that identifies trend direction",
            parameters={
                "period": {"type": "int", "default": 10, "min": 5, "max": 50, "description": "ATR period"},
                "multiplier": {"type": "float", "default": 3.0, "min": 1.0, "max": 5.0, "description": "ATR multiplier"},
                "risk_reward": {"type": "float", "default": 2.0, "min": 1.0, "max": 4.0, "description": "Risk-reward ratio"}
            },
            time_horizon="Swing"
        )
    
    def generate_signals(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        df = df.copy()
        period = params.get("period", 10)
        multiplier = params.get("multiplier", 3.0)
        rr = params.get("risk_reward", 2.0)
        
        # Calculate ATR
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        df['atr'] = df['tr'].rolling(period).mean()
        
        # Calculate basic bands
        df['hl2'] = (df['high'] + df['low']) / 2
        df['basic_upper'] = df['hl2'] + (multiplier * df['atr'])
        df['basic_lower'] = df['hl2'] - (multiplier * df['atr'])
        
        # Calculate SuperTrend
        df['upper_band'] = df['basic_upper']
        df['lower_band'] = df['basic_lower']
        df['supertrend'] = np.nan
        df['direction'] = 1  # 1 = bullish, -1 = bearish
        
        for i in range(period, len(df)):
            if df['close'].iloc[i-1] > df['upper_band'].iloc[i-1]:
                df.loc[df.index[i], 'direction'] = 1
            elif df['close'].iloc[i-1] < df['lower_band'].iloc[i-1]:
                df.loc[df.index[i], 'direction'] = -1
            else:
                df.loc[df.index[i], 'direction'] = df['direction'].iloc[i-1]
            
            if df['direction'].iloc[i] == 1:
                df.loc[df.index[i], 'supertrend'] = df['lower_band'].iloc[i]
            else:
                df.loc[df.index[i], 'supertrend'] = df['upper_band'].iloc[i]
        
        # Generate signals on direction change
        df['signal'] = SignalType.HOLD.value
        df['dir_change'] = df['direction'].diff()
        
        df.loc[df['dir_change'] == 2, 'signal'] = SignalType.BUY.value
        df.loc[df['dir_change'] == -2, 'signal'] = SignalType.SELL.value
        
        # Stops and targets
        df['stop_loss'] = df['supertrend']
        risk = abs(df['close'] - df['supertrend'])
        df['target'] = np.where(
            df['direction'] == 1,
            df['close'] + (rr * risk),
            df['close'] - (rr * risk)
        )
        
        return df


class ADXTrendStrategy(BaseStrategy):
    """
    ADX Trend Following Strategy
    
    Uses ADX to identify strong trends and DI+/DI- for direction.
    
    Entry Logic:
    - BUY: ADX > threshold AND DI+ > DI-
    - SELL: ADX > threshold AND DI- > DI+
    """
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="adx_trend",
            display_name="ADX Trend Following",
            category="Trend & Momentum",
            description="Enter trades only when trend strength is confirmed by ADX",
            parameters={
                "adx_period": {"type": "int", "default": 14, "min": 7, "max": 30, "description": "ADX calculation period"},
                "adx_threshold": {"type": "int", "default": 25, "min": 15, "max": 40, "description": "Minimum ADX for trend confirmation"},
                "atr_multiplier": {"type": "float", "default": 2.0, "min": 1.0, "max": 4.0, "description": "ATR multiplier for stops"},
                "risk_reward": {"type": "float", "default": 2.0, "min": 1.0, "max": 4.0, "description": "Risk-reward ratio"}
            },
            time_horizon="Swing"
        )
    
    def generate_signals(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        df = df.copy()
        period = params.get("adx_period", 14)
        threshold = params.get("adx_threshold", 25)
        atr_mult = params.get("atr_multiplier", 2.0)
        rr = params.get("risk_reward", 2.0)
        
        # Calculate True Range
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        df['atr'] = df['tr'].rolling(period).mean()
        
        # Calculate +DM and -DM
        df['up_move'] = df['high'] - df['high'].shift(1)
        df['down_move'] = df['low'].shift(1) - df['low']
        
        df['plus_dm'] = np.where((df['up_move'] > df['down_move']) & (df['up_move'] > 0), df['up_move'], 0)
        df['minus_dm'] = np.where((df['down_move'] > df['up_move']) & (df['down_move'] > 0), df['down_move'], 0)
        
        # Smooth DM and TR
        df['smoothed_plus_dm'] = df['plus_dm'].rolling(period).sum()
        df['smoothed_minus_dm'] = df['minus_dm'].rolling(period).sum()
        df['smoothed_tr'] = df['tr'].rolling(period).sum()
        
        # Calculate DI+ and DI-
        df['plus_di'] = 100 * (df['smoothed_plus_dm'] / df['smoothed_tr'])
        df['minus_di'] = 100 * (df['smoothed_minus_dm'] / df['smoothed_tr'])
        
        # Calculate DX and ADX
        df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
        df['adx'] = df['dx'].rolling(period).mean()
        
        # Generate signals
        df['signal'] = SignalType.HOLD.value
        
        buy_mask = (df['adx'] > threshold) & (df['plus_di'] > df['minus_di']) & \
                   (df['plus_di'].shift(1) <= df['minus_di'].shift(1))
        sell_mask = (df['adx'] > threshold) & (df['minus_di'] > df['plus_di']) & \
                    (df['minus_di'].shift(1) <= df['plus_di'].shift(1))
        
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
            df['close'] + (rr * atr_mult * df['atr']),
            np.where(df['signal'] == SignalType.SELL.value,
                     df['close'] - (rr * atr_mult * df['atr']), np.nan)
        )
        
        return df


class DonchianBreakoutStrategy(BaseStrategy):
    """
    Donchian Channel Breakout Strategy
    
    Classic turtle trading approach.
    
    Entry Logic:
    - BUY: Price breaks above N-period high
    - SELL: Price breaks below N-period low
    """
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="donchian_breakout",
            display_name="Donchian Channel Breakout",
            category="Trend & Momentum",
            description="Classic turtle trading breakout strategy using price channels",
            parameters={
                "entry_period": {"type": "int", "default": 20, "min": 10, "max": 55, "description": "Period for entry breakout"},
                "exit_period": {"type": "int", "default": 10, "min": 5, "max": 30, "description": "Period for exit (opposite breakout)"},
                "atr_period": {"type": "int", "default": 14, "min": 7, "max": 21, "description": "ATR period for position sizing"}
            },
            time_horizon="Positional"
        )
    
    def generate_signals(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        df = df.copy()
        entry_period = params.get("entry_period", 20)
        exit_period = params.get("exit_period", 10)
        atr_period = params.get("atr_period", 14)
        
        # Calculate channels
        df['entry_high'] = df['high'].rolling(entry_period).max()
        df['entry_low'] = df['low'].rolling(entry_period).min()
        df['exit_high'] = df['high'].rolling(exit_period).max()
        df['exit_low'] = df['low'].rolling(exit_period).min()
        
        # ATR for stops
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        df['atr'] = df['tr'].rolling(atr_period).mean()
        
        # Generate signals
        df['signal'] = SignalType.HOLD.value
        
        # Breakout above entry high (use yesterday's high to avoid look-ahead)
        buy_mask = df['close'] > df['entry_high'].shift(1)
        sell_mask = df['close'] < df['entry_low'].shift(1)
        
        df.loc[buy_mask, 'signal'] = SignalType.BUY.value
        df.loc[sell_mask, 'signal'] = SignalType.SELL.value
        
        # Stops at exit channel
        df['stop_loss'] = np.where(
            df['signal'] == SignalType.BUY.value,
            df['exit_low'],
            np.where(df['signal'] == SignalType.SELL.value,
                     df['exit_high'], np.nan)
        )
        
        # Target based on channel width
        channel_width = df['entry_high'] - df['entry_low']
        df['target'] = np.where(
            df['signal'] == SignalType.BUY.value,
            df['close'] + channel_width,
            np.where(df['signal'] == SignalType.SELL.value,
                     df['close'] - channel_width, np.nan)
        )
        
        return df


# =============================================================================
# MEAN REVERSION STRATEGIES
# =============================================================================

class RSIMeanReversionStrategy(BaseStrategy):
    """
    RSI Mean Reversion Strategy
    
    Entry Logic:
    - BUY: RSI crosses above oversold level (recovery from oversold)
    - SELL: RSI crosses below overbought level (decline from overbought)
    """
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="rsi_mean_reversion",
            display_name="RSI Mean Reversion",
            category="Mean Reversion",
            description="Trade reversals when RSI indicates extreme conditions",
            parameters={
                "rsi_period": {"type": "int", "default": 14, "min": 7, "max": 21, "description": "RSI calculation period"},
                "oversold": {"type": "int", "default": 30, "min": 20, "max": 40, "description": "Oversold threshold"},
                "overbought": {"type": "int", "default": 70, "min": 60, "max": 80, "description": "Overbought threshold"},
                "atr_multiplier": {"type": "float", "default": 1.5, "min": 1.0, "max": 3.0, "description": "ATR multiplier for stops"},
                "risk_reward": {"type": "float", "default": 1.5, "min": 1.0, "max": 3.0, "description": "Risk-reward ratio"}
            },
            time_horizon="Swing"
        )
    
    def generate_signals(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        df = df.copy()
        period = params.get("rsi_period", 14)
        oversold = params.get("oversold", 30)
        overbought = params.get("overbought", 70)
        atr_mult = params.get("atr_multiplier", 1.5)
        rr = params.get("risk_reward", 1.5)
        
        # Calculate RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Calculate ATR
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(abs(df['high'] - df['close'].shift(1)),
                       abs(df['low'] - df['close'].shift(1)))
        )
        df['atr'] = df['tr'].rolling(14).mean()
        
        # Generate signals
        df['signal'] = SignalType.HOLD.value
        
        # Buy when RSI crosses above oversold
        buy_mask = (df['rsi'] > oversold) & (df['rsi'].shift(1) <= oversold)
        sell_mask = (df['rsi'] < overbought) & (df['rsi'].shift(1) >= overbought)
        
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
            df['close'] + (rr * atr_mult * df['atr']),
            np.where(df['signal'] == SignalType.SELL.value,
                     df['close'] - (rr * atr_mult * df['atr']), np.nan)
        )
        
        return df


class BollingerBandsReversionStrategy(BaseStrategy):
    """
    Bollinger Bands Mean Reversion Strategy
    
    Entry Logic:
    - BUY: Price touches/crosses below lower band, then bounces back
    - SELL: Price touches/crosses above upper band, then reverts
    """
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="bollinger_reversion",
            display_name="Bollinger Bands Reversion",
            category="Mean Reversion",
            description="Trade reversals at Bollinger Band extremes",
            parameters={
                "period": {"type": "int", "default": 20, "min": 10, "max": 50, "description": "MA period for bands"},
                "std_dev": {"type": "float", "default": 2.0, "min": 1.5, "max": 3.0, "description": "Standard deviation multiplier"},
                "risk_reward": {"type": "float", "default": 1.5, "min": 1.0, "max": 3.0, "description": "Risk-reward ratio"}
            },
            time_horizon="Swing"
        )
    
    def generate_signals(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        df = df.copy()
        period = params.get("period", 20)
        std_mult = params.get("std_dev", 2.0)
        rr = params.get("risk_reward", 1.5)
        
        # Calculate Bollinger Bands
        df['sma'] = df['close'].rolling(period).mean()
        df['std'] = df['close'].rolling(period).std()
        df['upper_band'] = df['sma'] + (std_mult * df['std'])
        df['lower_band'] = df['sma'] - (std_mult * df['std'])
        
        # Generate signals
        df['signal'] = SignalType.HOLD.value
        
        # Buy when price bounces from lower band
        df['below_lower'] = df['close'] < df['lower_band']
        buy_mask = (~df['below_lower']) & (df['below_lower'].shift(1))
        
        # Sell when price reverts from upper band
        df['above_upper'] = df['close'] > df['upper_band']
        sell_mask = (~df['above_upper']) & (df['above_upper'].shift(1))
        
        df.loc[buy_mask, 'signal'] = SignalType.BUY.value
        df.loc[sell_mask, 'signal'] = SignalType.SELL.value
        
        # Stops and targets
        band_width = df['upper_band'] - df['lower_band']
        df['stop_loss'] = np.where(
            df['signal'] == SignalType.BUY.value,
            df['lower_band'] - (0.1 * band_width),
            np.where(df['signal'] == SignalType.SELL.value,
                     df['upper_band'] + (0.1 * band_width), np.nan)
        )
        df['target'] = np.where(
            df['signal'] == SignalType.BUY.value,
            df['sma'] + (0.5 * band_width * rr),
            np.where(df['signal'] == SignalType.SELL.value,
                     df['sma'] - (0.5 * band_width * rr), np.nan)
        )
        
        return df


class ZScoreReversionStrategy(BaseStrategy):
    """
    Z-Score Price Reversion Strategy
    
    Uses statistical z-score to identify price extremes.
    """
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="zscore_reversion",
            display_name="Z-Score Price Reversion",
            category="Mean Reversion",
            description="Statistical mean reversion using z-score of price",
            parameters={
                "lookback": {"type": "int", "default": 20, "min": 10, "max": 60, "description": "Lookback period for z-score"},
                "entry_threshold": {"type": "float", "default": 2.0, "min": 1.5, "max": 3.0, "description": "Z-score entry threshold"},
                "exit_threshold": {"type": "float", "default": 0.5, "min": 0.0, "max": 1.0, "description": "Z-score exit threshold"},
                "atr_multiplier": {"type": "float", "default": 2.0, "min": 1.0, "max": 4.0, "description": "ATR multiplier for stops"}
            },
            time_horizon="Swing"
        )
    
    def generate_signals(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        df = df.copy()
        lookback = params.get("lookback", 20)
        entry_z = params.get("entry_threshold", 2.0)
        exit_z = params.get("exit_threshold", 0.5)
        atr_mult = params.get("atr_multiplier", 2.0)
        
        # Calculate z-score
        df['ma'] = df['close'].rolling(lookback).mean()
        df['std'] = df['close'].rolling(lookback).std()
        df['zscore'] = (df['close'] - df['ma']) / df['std']
        
        # ATR for stops
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(abs(df['high'] - df['close'].shift(1)),
                       abs(df['low'] - df['close'].shift(1)))
        )
        df['atr'] = df['tr'].rolling(14).mean()
        
        # Generate signals
        df['signal'] = SignalType.HOLD.value
        
        # Buy when z-score crosses above -entry_z (recovering from extreme low)
        buy_mask = (df['zscore'] > -entry_z) & (df['zscore'].shift(1) <= -entry_z)
        sell_mask = (df['zscore'] < entry_z) & (df['zscore'].shift(1) >= entry_z)
        
        df.loc[buy_mask, 'signal'] = SignalType.BUY.value
        df.loc[sell_mask, 'signal'] = SignalType.SELL.value
        
        # Stops and targets
        df['stop_loss'] = np.where(
            df['signal'] == SignalType.BUY.value,
            df['close'] - (atr_mult * df['atr']),
            np.where(df['signal'] == SignalType.SELL.value,
                     df['close'] + (atr_mult * df['atr']), np.nan)
        )
        df['target'] = df['ma']  # Target is the mean
        
        return df


# =============================================================================
# BREAKOUT & VOLATILITY STRATEGIES
# =============================================================================

class ORBStrategy(BaseStrategy):
    """
    Opening Range Breakout Strategy
    
    Classic intraday strategy that trades breakouts from the opening range.
    """
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="orb",
            display_name="Opening Range Breakout",
            category="Breakout & Volatility",
            description="Trade breakouts from the first N minutes of trading",
            parameters={
                "orb_minutes": {"type": "int", "default": 15, "min": 5, "max": 60, "description": "Opening range duration in minutes"},
                "buffer_pct": {"type": "float", "default": 0.1, "min": 0.0, "max": 0.5, "description": "Buffer percentage for breakout confirmation"},
                "risk_reward": {"type": "float", "default": 2.0, "min": 1.0, "max": 4.0, "description": "Risk-reward ratio"}
            },
            time_horizon="Intraday"
        )
    
    def generate_signals(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        df = df.copy()
        orb_mins = params.get("orb_minutes", 15)
        buffer_pct = params.get("buffer_pct", 0.1)
        rr = params.get("risk_reward", 2.0)
        
        # For daily data, use first candle high/low as proxy
        # In real implementation, this would use intraday data
        df['orb_high'] = df['high'].shift(1)
        df['orb_low'] = df['low'].shift(1)
        df['orb_range'] = df['orb_high'] - df['orb_low']
        
        buffer = df['orb_range'] * buffer_pct
        
        # Generate signals
        df['signal'] = SignalType.HOLD.value
        
        buy_mask = df['close'] > (df['orb_high'] + buffer)
        sell_mask = df['close'] < (df['orb_low'] - buffer)
        
        df.loc[buy_mask, 'signal'] = SignalType.BUY.value
        df.loc[sell_mask, 'signal'] = SignalType.SELL.value
        
        # Stops and targets
        df['stop_loss'] = np.where(
            df['signal'] == SignalType.BUY.value,
            df['orb_low'],
            np.where(df['signal'] == SignalType.SELL.value,
                     df['orb_high'], np.nan)
        )
        
        risk = abs(df['close'] - df['stop_loss'])
        df['target'] = np.where(
            df['signal'] == SignalType.BUY.value,
            df['close'] + (rr * risk),
            np.where(df['signal'] == SignalType.SELL.value,
                     df['close'] - (rr * risk), np.nan)
        )
        
        return df


class VolumeBreakoutStrategy(BaseStrategy):
    """
    Volume Breakout Strategy
    
    Trades price breakouts confirmed by above-average volume.
    """
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="volume_breakout",
            display_name="Volume Breakout",
            category="Breakout & Volatility",
            description="Trade price breakouts confirmed by volume surge",
            parameters={
                "price_period": {"type": "int", "default": 20, "min": 10, "max": 50, "description": "Period for price breakout"},
                "volume_period": {"type": "int", "default": 20, "min": 10, "max": 50, "description": "Period for volume average"},
                "volume_mult": {"type": "float", "default": 1.5, "min": 1.2, "max": 3.0, "description": "Volume multiplier for confirmation"},
                "atr_multiplier": {"type": "float", "default": 2.0, "min": 1.0, "max": 4.0, "description": "ATR multiplier for stops"}
            },
            time_horizon="Swing"
        )
    
    def generate_signals(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        df = df.copy()
        price_period = params.get("price_period", 20)
        vol_period = params.get("volume_period", 20)
        vol_mult = params.get("volume_mult", 1.5)
        atr_mult = params.get("atr_multiplier", 2.0)
        
        # Calculate indicators
        df['highest_high'] = df['high'].rolling(price_period).max()
        df['lowest_low'] = df['low'].rolling(price_period).min()
        df['avg_volume'] = df['volume'].rolling(vol_period).mean()
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
        
        buy_mask = (df['close'] > df['highest_high'].shift(1)) & df['volume_surge']
        sell_mask = (df['close'] < df['lowest_low'].shift(1)) & df['volume_surge']
        
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


class ATRExpansionStrategy(BaseStrategy):
    """
    ATR Volatility Expansion Strategy
    
    Trades when volatility expands after a period of contraction.
    """
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="atr_expansion",
            display_name="ATR Volatility Expansion",
            category="Breakout & Volatility",
            description="Trade volatility expansion after contraction periods",
            parameters={
                "atr_period": {"type": "int", "default": 14, "min": 7, "max": 21, "description": "ATR period"},
                "expansion_mult": {"type": "float", "default": 1.5, "min": 1.2, "max": 2.5, "description": "ATR expansion threshold multiplier"},
                "lookback": {"type": "int", "default": 20, "min": 10, "max": 50, "description": "Lookback for ATR comparison"},
                "risk_reward": {"type": "float", "default": 2.0, "min": 1.0, "max": 4.0, "description": "Risk-reward ratio"}
            },
            time_horizon="Swing"
        )
    
    def generate_signals(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        df = df.copy()
        atr_period = params.get("atr_period", 14)
        exp_mult = params.get("expansion_mult", 1.5)
        lookback = params.get("lookback", 20)
        rr = params.get("risk_reward", 2.0)
        
        # Calculate ATR
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(abs(df['high'] - df['close'].shift(1)),
                       abs(df['low'] - df['close'].shift(1)))
        )
        df['atr'] = df['tr'].rolling(atr_period).mean()
        df['atr_ma'] = df['atr'].rolling(lookback).mean()
        
        # Detect expansion
        df['atr_expansion'] = df['atr'] > (exp_mult * df['atr_ma'])
        
        # Direction based on candle
        df['bullish'] = df['close'] > df['open']
        
        # Generate signals
        df['signal'] = SignalType.HOLD.value
        
        exp_start = df['atr_expansion'] & (~df['atr_expansion'].shift(1).fillna(False))
        buy_mask = exp_start & df['bullish']
        sell_mask = exp_start & (~df['bullish'])
        
        df.loc[buy_mask, 'signal'] = SignalType.BUY.value
        df.loc[sell_mask, 'signal'] = SignalType.SELL.value
        
        # Stops and targets
        df['stop_loss'] = np.where(
            df['signal'] == SignalType.BUY.value,
            df['low'] - (0.5 * df['atr']),
            np.where(df['signal'] == SignalType.SELL.value,
                     df['high'] + (0.5 * df['atr']), np.nan)
        )
        
        risk = abs(df['close'] - df['stop_loss'])
        df['target'] = np.where(
            df['signal'] == SignalType.BUY.value,
            df['close'] + (rr * risk),
            np.where(df['signal'] == SignalType.SELL.value,
                     df['close'] - (rr * risk), np.nan)
        )
        
        return df


# =============================================================================
# VWAP & INSTITUTIONAL STRATEGIES
# =============================================================================

class VWAPPullbackStrategy(BaseStrategy):
    """
    VWAP Pullback Strategy
    
    Trade pullbacks to VWAP as support/resistance.
    """
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="vwap_pullback",
            display_name="VWAP Pullback",
            category="VWAP & Institutional",
            description="Trade pullbacks to VWAP when price is trending",
            parameters={
                "trend_ema": {"type": "int", "default": 20, "min": 10, "max": 50, "description": "EMA period for trend filter"},
                "vwap_buffer": {"type": "float", "default": 0.1, "min": 0.05, "max": 0.5, "description": "VWAP touch buffer (%)"},
                "atr_multiplier": {"type": "float", "default": 1.5, "min": 1.0, "max": 3.0, "description": "ATR multiplier for stops"},
                "risk_reward": {"type": "float", "default": 2.0, "min": 1.0, "max": 4.0, "description": "Risk-reward ratio"}
            },
            time_horizon="Intraday"
        )
    
    def generate_signals(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        df = df.copy()
        trend_ema = params.get("trend_ema", 20)
        vwap_buffer = params.get("vwap_buffer", 0.1) / 100
        atr_mult = params.get("atr_multiplier", 1.5)
        rr = params.get("risk_reward", 2.0)
        
        # Calculate VWAP (cumulative)
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
        df['tp_volume'] = df['typical_price'] * df['volume']
        df['cum_tpv'] = df['tp_volume'].cumsum()
        df['cum_volume'] = df['volume'].cumsum()
        df['vwap'] = df['cum_tpv'] / df['cum_volume']
        
        # Trend filter
        df['ema'] = df['close'].ewm(span=trend_ema, adjust=False).mean()
        df['uptrend'] = df['close'] > df['ema']
        
        # ATR
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(abs(df['high'] - df['close'].shift(1)),
                       abs(df['low'] - df['close'].shift(1)))
        )
        df['atr'] = df['tr'].rolling(14).mean()
        
        # VWAP touch detection
        vwap_lower = df['vwap'] * (1 - vwap_buffer)
        vwap_upper = df['vwap'] * (1 + vwap_buffer)
        df['near_vwap'] = (df['low'] <= vwap_upper) & (df['high'] >= vwap_lower)
        
        # Generate signals
        df['signal'] = SignalType.HOLD.value
        
        # Buy: uptrend + price touches VWAP from above + bounces
        buy_mask = df['uptrend'] & df['near_vwap'] & (df['close'] > df['vwap'])
        sell_mask = (~df['uptrend']) & df['near_vwap'] & (df['close'] < df['vwap'])
        
        df.loc[buy_mask, 'signal'] = SignalType.BUY.value
        df.loc[sell_mask, 'signal'] = SignalType.SELL.value
        
        # Stops and targets
        df['stop_loss'] = np.where(
            df['signal'] == SignalType.BUY.value,
            df['vwap'] - (atr_mult * df['atr']),
            np.where(df['signal'] == SignalType.SELL.value,
                     df['vwap'] + (atr_mult * df['atr']), np.nan)
        )
        
        risk = abs(df['close'] - df['stop_loss'])
        df['target'] = np.where(
            df['signal'] == SignalType.BUY.value,
            df['close'] + (rr * risk),
            np.where(df['signal'] == SignalType.SELL.value,
                     df['close'] - (rr * risk), np.nan)
        )
        
        return df


class VWAPTrendStrategy(BaseStrategy):
    """
    VWAP Trend Confirmation Strategy
    
    Use VWAP as a trend filter - only trade with VWAP direction.
    """
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="vwap_trend",
            display_name="VWAP Trend Confirmation",
            category="VWAP & Institutional",
            description="Use VWAP as institutional reference for trend direction",
            parameters={
                "confirmation_bars": {"type": "int", "default": 3, "min": 1, "max": 10, "description": "Bars above/below VWAP for confirmation"},
                "atr_multiplier": {"type": "float", "default": 2.0, "min": 1.0, "max": 4.0, "description": "ATR multiplier for stops"},
                "risk_reward": {"type": "float", "default": 2.0, "min": 1.0, "max": 4.0, "description": "Risk-reward ratio"}
            },
            time_horizon="Intraday"
        )
    
    def generate_signals(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        df = df.copy()
        confirm_bars = params.get("confirmation_bars", 3)
        atr_mult = params.get("atr_multiplier", 2.0)
        rr = params.get("risk_reward", 2.0)
        
        # Calculate VWAP
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
        df['tp_volume'] = df['typical_price'] * df['volume']
        df['cum_tpv'] = df['tp_volume'].cumsum()
        df['cum_volume'] = df['volume'].cumsum()
        df['vwap'] = df['cum_tpv'] / df['cum_volume']
        
        # ATR
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(abs(df['high'] - df['close'].shift(1)),
                       abs(df['low'] - df['close'].shift(1)))
        )
        df['atr'] = df['tr'].rolling(14).mean()
        
        # VWAP position
        df['above_vwap'] = df['close'] > df['vwap']
        
        # Count consecutive bars
        df['above_count'] = 0
        df['below_count'] = 0
        
        for i in range(confirm_bars, len(df)):
            if df['above_vwap'].iloc[i-confirm_bars:i].all():
                df.loc[df.index[i], 'above_count'] = confirm_bars
            if (~df['above_vwap']).iloc[i-confirm_bars:i].all():
                df.loc[df.index[i], 'below_count'] = confirm_bars
        
        # Generate signals
        df['signal'] = SignalType.HOLD.value
        
        # Buy after confirm_bars above VWAP
        buy_mask = (df['above_count'] == confirm_bars) & (df['above_count'].shift(1) < confirm_bars)
        sell_mask = (df['below_count'] == confirm_bars) & (df['below_count'].shift(1) < confirm_bars)
        
        df.loc[buy_mask, 'signal'] = SignalType.BUY.value
        df.loc[sell_mask, 'signal'] = SignalType.SELL.value
        
        # Stops at VWAP
        df['stop_loss'] = np.where(
            df['signal'] == SignalType.BUY.value,
            df['vwap'] - (0.5 * df['atr']),
            np.where(df['signal'] == SignalType.SELL.value,
                     df['vwap'] + (0.5 * df['atr']), np.nan)
        )
        
        risk = abs(df['close'] - df['stop_loss'])
        df['target'] = np.where(
            df['signal'] == SignalType.BUY.value,
            df['close'] + (rr * risk),
            np.where(df['signal'] == SignalType.SELL.value,
                     df['close'] - (rr * risk), np.nan)
        )
        
        return df


# =============================================================================
# STRATEGY REGISTRY
# =============================================================================

class StrategyRegistry:
    """Registry of all available strategies."""
    
    _strategies: Dict[str, BaseStrategy] = {}
    
    @classmethod
    def register(cls, strategy: BaseStrategy):
        """Register a strategy."""
        cls._strategies[strategy.metadata.name] = strategy
    
    @classmethod
    def get(cls, name: str) -> Optional[BaseStrategy]:
        """Get a strategy by name."""
        return cls._strategies.get(name)
    
    @classmethod
    def list_all(cls) -> List[StrategyMetadata]:
        """Get metadata for all registered strategies."""
        return [s.metadata for s in cls._strategies.values()]
    
    @classmethod
    def list_by_category(cls) -> Dict[str, List[StrategyMetadata]]:
        """Get strategies grouped by category."""
        categories: Dict[str, List[StrategyMetadata]] = {}
        for strategy in cls._strategies.values():
            cat = strategy.metadata.category
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(strategy.metadata)
        return categories


# Register all strategies
StrategyRegistry.register(MACrossoverStrategy())
StrategyRegistry.register(SuperTrendStrategy())
StrategyRegistry.register(ADXTrendStrategy())
StrategyRegistry.register(DonchianBreakoutStrategy())
StrategyRegistry.register(RSIMeanReversionStrategy())
StrategyRegistry.register(BollingerBandsReversionStrategy())
StrategyRegistry.register(ZScoreReversionStrategy())
StrategyRegistry.register(ORBStrategy())
StrategyRegistry.register(VolumeBreakoutStrategy())
StrategyRegistry.register(ATRExpansionStrategy())
StrategyRegistry.register(VWAPPullbackStrategy())
StrategyRegistry.register(VWAPTrendStrategy())


def get_strategy_catalog() -> Dict[str, Any]:
    """Get full strategy catalog for API/UI."""
    categories = StrategyRegistry.list_by_category()
    result = {}
    
    for cat, strategies in categories.items():
        result[cat] = [
            {
                "name": s.name,
                "display_name": s.display_name,
                "description": s.description,
                "parameters": s.parameters,
                "time_horizon": s.time_horizon
            }
            for s in strategies
        ]
    
    return result
