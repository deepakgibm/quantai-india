"""
Strategy Registry for Experiment Lab
Central registry of all 70 strategy combinations.
"""

from typing import Dict, List, Optional, Type
from .lab_strategies.base import ExperimentStrategy, get_all_strategies, get_strategy_by_id

# Import all strategy modules to trigger registration


# Complete catalog of all 70 strategies
STRATEGY_CATALOG = [
    # Category A - Single-Logic Baselines (1-10)
    {"id": 1, "name": "RSI Mean Reversion", "category": "A", "description": "Buy when RSI is oversold (<30), sell when overbought (>70)"},
    {"id": 2, "name": "Bollinger Bands Breakout", "category": "A", "description": "Trade breakouts above/below Bollinger Bands"},
    {"id": 3, "name": "Donchian Channel Breakout", "category": "A", "description": "Trade breakouts of 20-period high/low channels"},
    {"id": 4, "name": "MACD Crossover", "category": "A", "description": "Trade MACD line crossing signal line"},
    {"id": 5, "name": "MA Golden Cross", "category": "A", "description": "Trade 50/200 SMA crossovers"},
    {"id": 6, "name": "ADX Trend Strength", "category": "A", "description": "Trade strong trends using ADX > 25 with DI crossovers"},
    {"id": 7, "name": "ATR Volatility Breakout", "category": "A", "description": "Trade breakouts when price moves > 2 ATR from previous close"},
    {"id": 8, "name": "Ichimoku Trend", "category": "A", "description": "Trade based on price position relative to Ichimoku cloud"},
    {"id": 9, "name": "OBV Trend", "category": "A", "description": "Trade based on On-Balance Volume trend confirmation"},
    {"id": 10, "name": "Volume Surge Breakout", "category": "A", "description": "Trade breakouts confirmed by volume > 2x average"},
    
    # Category B - Price + Momentum (11-18)
    {"id": 11, "name": "RSI + MACD", "category": "B", "description": "RSI oversold/overbought confirmed by MACD crossover"},
    {"id": 12, "name": "RSI + Stochastic", "category": "B", "description": "Dual oscillator confirmation for entries"},
    {"id": 13, "name": "RSI + Williams %R", "category": "B", "description": "RSI confirmed by Williams %R extremes"},
    {"id": 14, "name": "MACD + Momentum", "category": "B", "description": "MACD crossover confirmed by Rate of Change"},
    {"id": 15, "name": "MACD + Stochastic", "category": "B", "description": "MACD trend with Stochastic timing"},
    {"id": 16, "name": "Momentum + MA Trend", "category": "B", "description": "Trade momentum in direction of EMA trend"},
    {"id": 17, "name": "RSI + Price Momentum", "category": "B", "description": "RSI with price momentum confirmation"},
    {"id": 18, "name": "RSI + ADX Filter", "category": "B", "description": "RSI mean reversion only in ranging markets (ADX < 25)"},
    
    # Category C - Breakout + Filter (19-25)
    {"id": 19, "name": "Bollinger Breakout + ADX", "category": "C", "description": "Bollinger breakout confirmed by strong trend (ADX > 25)"},
    {"id": 20, "name": "Bollinger Breakout + RSI", "category": "C", "description": "Bollinger breakout with RSI momentum confirmation"},
    {"id": 21, "name": "Donchian Breakout + ADX", "category": "C", "description": "Donchian channel breakout with ADX trend filter"},
    {"id": 22, "name": "Donchian Breakout + ATR", "category": "C", "description": "Donchian breakout with volatility expansion filter"},
    {"id": 23, "name": "ATR Breakout + Volume", "category": "C", "description": "ATR volatility breakout confirmed by volume surge"},
    {"id": 24, "name": "High-Low Breakout + Trend", "category": "C", "description": "N-period high/low breakout with EMA trend filter"},
    {"id": 25, "name": "Range Expansion + Momentum", "category": "C", "description": "Trade when daily range expands significantly with momentum"},
    
    # Category D - Trend + Momentum Confluence (26-34)
    {"id": 26, "name": "EMA 9/21 + MACD", "category": "D", "description": "Fast EMA crossover confirmed by MACD"},
    {"id": 27, "name": "EMA 20/50 + RSI", "category": "D", "description": "EMA trend with RSI momentum filter"},
    {"id": 28, "name": "SMA Trend + Momentum", "category": "D", "description": "SMA trend direction with ROC momentum"},
    {"id": 29, "name": "ADX + MACD", "category": "D", "description": "Strong trend (ADX) with MACD timing"},
    {"id": 30, "name": "ADX + RSI + Momentum", "category": "D", "description": "Triple confluence: trend strength, momentum oscillator, rate of change"},
    {"id": 31, "name": "Ichimoku + MACD", "category": "D", "description": "Ichimoku cloud position with MACD crossover"},
    {"id": 32, "name": "Ichimoku + RSI", "category": "D", "description": "Ichimoku cloud with RSI momentum filter"},
    {"id": 33, "name": "Supertrend + RSI", "category": "D", "description": "Supertrend direction with RSI timing"},
    {"id": 34, "name": "Supertrend + MACD", "category": "D", "description": "Supertrend with MACD momentum confirmation"},
    
    # Category E - Volume-Confirmed (35-40)
    {"id": 35, "name": "RSI + Volume Surge", "category": "E", "description": "RSI extremes confirmed by volume > 1.5x average"},
    {"id": 36, "name": "MACD + OBV", "category": "E", "description": "MACD crossover confirmed by OBV trend"},
    {"id": 37, "name": "Breakout + Volume Expansion", "category": "E", "description": "Price breakout with volume > 2x average"},
    {"id": 38, "name": "Donchian Breakout + OBV", "category": "E", "description": "Donchian channel breakout with OBV trend confirmation"},
    {"id": 39, "name": "Price Trend + Accumulation", "category": "E", "description": "EMA trend with sustained volume accumulation"},
    {"id": 40, "name": "Volume Spike + ATR Breakout", "category": "E", "description": "Extreme volume spike with ATR-based price move"},

    # Category F - Mean Reversion (41-46)
    {"id": 41, "name": "Bollinger Mean Reversion + RSI", "category": "F", "description": "Bollinger band touch with RSI extreme for mean reversion"},
    {"id": 42, "name": "Donchian Mean Reversion + RSI", "category": "F", "description": "Trade reversals at Donchian channel extremes with RSI"},
    {"id": 43, "name": "Williams %R + RSI", "category": "F", "description": "Dual oscillator extreme for mean reversion"},
    {"id": 44, "name": "CCI Deviation + RSI", "category": "F", "description": "CCI extreme deviation with RSI confirmation"},
    {"id": 45, "name": "RSI + VWAP Deviation", "category": "F", "description": "Trade deviation from VWAP with RSI confirmation"},
    {"id": 46, "name": "ATR Compression Mean Reversion", "category": "F", "description": "Low volatility compression followed by mean reversion setup"},
    
    # Category G - Multi-Indicator Confluence (47-53)
    {"id": 47, "name": "RSI + MACD + ADX", "category": "G", "description": "Triple confluence: momentum, trend signal, trend strength"},
    {"id": 48, "name": "RSI + MACD + Volume", "category": "G", "description": "Momentum confluence with volume confirmation"},
    {"id": 49, "name": "Bollinger + RSI + ADX", "category": "G", "description": "Bollinger breakout with RSI and ADX filters"},
    {"id": 50, "name": "EMA Trend + Momentum + Volume", "category": "G", "description": "EMA trend with ROC momentum and volume confirmation"},
    {"id": 51, "name": "Supertrend + RSI + Volume", "category": "G", "description": "Supertrend direction with RSI and volume confirmation"},
    {"id": 52, "name": "Ichimoku + MACD + Volume", "category": "G", "description": "Ichimoku cloud with MACD crossover and volume"},
    {"id": 53, "name": "ATR Breakout + ADX + Momentum", "category": "G", "description": "Volatility breakout with trend strength and momentum"},
    
    # Category H - Multi-Timeframe (54-59)
    {"id": 54, "name": "Daily Trend + 1H Entry", "category": "H", "description": "Daily EMA trend direction with 1H RSI entry timing"},
    {"id": 55, "name": "Daily Trend + 30m Momentum", "category": "H", "description": "Daily trend with 30m momentum breakout"},
    {"id": 56, "name": "4H Structure + 15m Breakout", "category": "H", "description": "4H support/resistance with 15m breakout entry"},
    {"id": 57, "name": "Weekly Trend + Daily Pullback", "category": "H", "description": "Weekly trend with daily pullback to moving average"},
    {"id": 58, "name": "HTF ADX + LTF RSI", "category": "H", "description": "Higher TF ADX for trend, lower TF RSI for timing"},
    {"id": 59, "name": "HTF Ichimoku + LTF MACD", "category": "H", "description": "Higher TF Ichimoku cloud for bias, lower TF MACD for entry"},
    
    # Category I - Pattern + Indicator (60-65)
    {"id": 60, "name": "Flag/Pennant + Volume", "category": "I", "description": "Consolidation breakout (flag pattern) with volume"},
    {"id": 61, "name": "Head & Shoulders + RSI Divergence", "category": "I", "description": "H&S pattern reversal confirmed by RSI divergence"},
    {"id": 62, "name": "Breakout Retest + Momentum", "category": "I", "description": "Enter on retest of breakout level with momentum confirmation"},
    {"id": 63, "name": "Fibonacci Bounce + RSI", "category": "I", "description": "Trade bounce from Fibonacci levels with RSI confirmation"},
    {"id": 64, "name": "Fibonacci Bounce + Volume", "category": "I", "description": "Fibonacci level bounce with volume confirmation"},
    {"id": 65, "name": "S/R + Momentum", "category": "I", "description": "Trade S/R level breaks with momentum confirmation"},
    
    # Category J - Experimental / Quant (66-70)
    {"id": 66, "name": "Volatility Expansion + Momentum", "category": "J", "description": "Trade when volatility expands from compression with momentum"},
    {"id": 67, "name": "Volatility Compression → Breakout", "category": "J", "description": "Detect volatility squeeze and trade the subsequent breakout"},
    {"id": 68, "name": "Trend Strength Score", "category": "J", "description": "Composite trend strength score combining ADX and momentum"},
    {"id": 69, "name": "Regime-Based Strategy", "category": "J", "description": "Automatically switch between trend and mean-reversion based on market regime"},
    {"id": 70, "name": "Adaptive Strategy Selector", "category": "J", "description": "Dynamically select between strategies based on recent performance"},
]


class StrategyRegistry:
    """Central registry for accessing all 70 strategies."""
    
    @staticmethod
    def get_all() -> Dict[int, Type[ExperimentStrategy]]:
        """Get all registered strategies."""
        return get_all_strategies()
    
    @staticmethod
    def get_by_id(strategy_id: int) -> Optional[Type[ExperimentStrategy]]:
        """Get a strategy class by its ID."""
        return get_strategy_by_id(strategy_id)
    
    @staticmethod
    def get_catalog() -> List[Dict]:
        """Get the strategy catalog with metadata."""
        return STRATEGY_CATALOG
    
    @staticmethod
    def get_by_category(category: str) -> List[Dict]:
        """Get strategies filtered by category."""
        return [s for s in STRATEGY_CATALOG if s['category'] == category.upper()]
    
    @staticmethod
    def get_categories() -> List[Dict]:
        """Get list of categories with counts."""
        categories = {
            "A": {"name": "Single-Logic Baselines", "count": 10},
            "B": {"name": "Price + Momentum", "count": 8},
            "C": {"name": "Breakout + Filter", "count": 7},
            "D": {"name": "Trend + Momentum Confluence", "count": 9},
            "E": {"name": "Volume-Confirmed", "count": 6},
            "F": {"name": "Mean Reversion", "count": 6},
            "G": {"name": "Multi-Indicator Confluence", "count": 7},
            "H": {"name": "Multi-Timeframe", "count": 6},
            "I": {"name": "Pattern + Indicator", "count": 6},
            "J": {"name": "Experimental / Quant", "count": 5},
        }
        return [{"id": k, **v} for k, v in categories.items()]
    
    @staticmethod
    def instantiate(strategy_id: int) -> Optional[ExperimentStrategy]:
        """Create an instance of a strategy by ID."""
        strategy_class = get_strategy_by_id(strategy_id)
        if strategy_class:
            return strategy_class()
        return None


__all__ = ['StrategyRegistry', 'STRATEGY_CATALOG']
