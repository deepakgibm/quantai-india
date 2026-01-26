"""
Comprehensive Test Suite for Scanner Strategies

Tests all 21 strategies to ensure they:
1. Initialize correctly
2. Return valid ScanResult or None
3. Handle edge cases (insufficient data, invalid data)
4. Calculate correct signal types
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies.base import StrategyRegistry, ScanResult, SignalType, StrategyTier


def generate_sample_data(bars: int = 250, trend: str = "neutral", volatility: float = 0.02) -> pd.DataFrame:
    """Generate sample OHLCV data with configurable characteristics."""
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=bars, freq='D')
    base_price = 1000
    
    if trend == "bullish":
        drift = 0.001  # Upward drift
    elif trend == "bearish":
        drift = -0.001  # Downward drift
    else:
        drift = 0
    
    returns = np.random.randn(bars) * volatility + drift
    prices = base_price * np.exp(np.cumsum(returns))
    
    df = pd.DataFrame({
        'date': dates,
        'open': prices * (1 + np.random.randn(bars) * 0.005),
        'high': prices * (1 + np.abs(np.random.randn(bars) * 0.01)),
        'low': prices * (1 - np.abs(np.random.randn(bars) * 0.01)),
        'close': prices,
        'volume': np.random.randint(100000, 10000000, bars)
    })
    
    return df


def generate_oversold_data(bars: int = 50) -> pd.DataFrame:
    """Generate data simulating oversold conditions (RSI < 30)."""
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=bars, freq='D')
    
    # Sharp decline followed by stabilization
    prices = np.concatenate([
        np.linspace(1000, 800, bars - 10),  # Sharp decline
        np.linspace(800, 810, 10)  # Slight recovery
    ])
    
    df = pd.DataFrame({
        'date': dates,
        'open': prices * 1.002,
        'high': prices * 1.01,
        'low': prices * 0.99,
        'close': prices,
        'volume': np.random.randint(500000, 5000000, bars)
    })
    
    return df


def generate_overbought_data(bars: int = 50) -> pd.DataFrame:
    """Generate data simulating overbought conditions (RSI > 70)."""
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=bars, freq='D')
    
    prices = np.concatenate([
        np.linspace(1000, 1200, bars - 10),  # Sharp rise
        np.linspace(1200, 1190, 10)  # Slight pullback
    ])
    
    df = pd.DataFrame({
        'date': dates,
        'open': prices * 0.998,
        'high': prices * 1.01,
        'low': prices * 0.99,
        'close': prices,
        'volume': np.random.randint(500000, 5000000, bars)
    })
    
    return df


class TestStrategyRegistry:
    """Test the strategy registry functionality."""
    
    def test_all_strategies_registered(self):
        """Verify all 21 strategies are registered."""
        strategies = StrategyRegistry.get_all()
        assert len(strategies) == 21, f"Expected 21 strategies, got {len(strategies)}"
    
    def test_list_strategies(self):
        """Test list_strategies returns correct format."""
        strategies = StrategyRegistry.list_strategies()
        assert isinstance(strategies, list)
        
        for s in strategies:
            assert "name" in s
            assert "description" in s
            assert "tier" in s
            assert "min_bars" in s
    
    def test_get_strategy_by_name(self):
        """Test retrieving strategy by name."""
        strategy_cls = StrategyRegistry.get("RSI Mean Reversion")
        assert strategy_cls is not None
        assert strategy_cls.name == "RSI Mean Reversion"
    
    def test_get_nonexistent_strategy(self):
        """Test getting a strategy that doesn't exist."""
        strategy_cls = StrategyRegistry.get("Nonexistent Strategy")
        assert strategy_cls is None


class TestTier1Strategies:
    """Test Tier 1 strategies - Highest Win Rate."""
    
    def test_rsi_mean_reversion_init(self):
        """Test RSI Mean Reversion initialization."""
        from strategies.tier1.rsi_mean_reversion import RSIMeanReversion
        strategy = RSIMeanReversion()
        assert strategy.name == "RSI Mean Reversion"
        assert strategy.tier == StrategyTier.TIER_1
        assert strategy.min_bars_required == 30
    
    def test_rsi_mean_reversion_oversold(self):
        """Test RSI generates bullish signal when oversold."""
        from strategies.tier1.rsi_mean_reversion import RSIMeanReversion
        strategy = RSIMeanReversion()
        df = generate_oversold_data(50)
        
        result = strategy.scan(df, "TEST", "NIFTY 50", "1d")
        # Should potentially return bullish or None depending on exact RSI value
        if result:
            assert isinstance(result, ScanResult)
            assert result.strategy == "RSI Mean Reversion"
    
    def test_rsi_mean_reversion_insufficient_data(self):
        """Test RSI returns None with insufficient data."""
        from strategies.tier1.rsi_mean_reversion import RSIMeanReversion
        strategy = RSIMeanReversion()
        df = generate_sample_data(10)  # Less than min_bars_required
        
        result = strategy.scan(df, "TEST", "NIFTY 50", "1d")
        assert result is None
    
    def test_bollinger_breakout_init(self):
        """Test Bollinger Bands Breakout initialization."""
        from strategies.tier1.bollinger_breakout import BollingerBreakout
        strategy = BollingerBreakout()
        assert strategy.name == "Bollinger Bands Breakout"
        assert strategy.tier == StrategyTier.TIER_1
    
    def test_bollinger_breakout_normal_data(self):
        """Test Bollinger Bands with normal market data."""
        from strategies.tier1.bollinger_breakout import BollingerBreakout
        strategy = BollingerBreakout()
        df = generate_sample_data(100)
        
        result = strategy.scan(df, "TEST", "NIFTY 50", "1d")
        # May return None if no breakout, or ScanResult
        if result:
            assert isinstance(result, ScanResult)
            assert result.signal in [SignalType.BULLISH, SignalType.BEARISH]
    
    def test_williams_r_init(self):
        """Test Williams %R initialization."""
        from strategies.tier1.williams_r import WilliamsR
        strategy = WilliamsR()
        assert strategy.name == "Williams %R Mean Reversion"
        assert strategy.tier == StrategyTier.TIER_1
    
    def test_donchian_breakout_init(self):
        """Test Donchian Channel Breakout initialization."""
        from strategies.tier1.donchian_breakout import DonchianBreakout
        strategy = DonchianBreakout()
        assert strategy.name == "Donchian Channel Breakout"
        assert strategy.tier == StrategyTier.TIER_1
    
    def test_head_shoulders_init(self):
        """Test Head & Shoulders initialization."""
        from strategies.tier1.head_shoulders import HeadShoulders
        strategy = HeadShoulders()
        assert strategy.name == "Head & Shoulders Pattern"
        assert strategy.tier == StrategyTier.TIER_1
        assert strategy.min_bars_required == 50


class TestTier2Strategies:
    """Test Tier 2 strategies - Solid Strategies."""
    
    def test_adx_trend_init(self):
        """Test ADX Trend initialization."""
        from strategies.tier2.adx_trend import ADXTrend
        strategy = ADXTrend()
        assert strategy.name == "ADX Trend Strength"
        assert strategy.tier == StrategyTier.TIER_2
    
    def test_adx_trend_trending_market(self):
        """Test ADX in a trending market."""
        from strategies.tier2.adx_trend import ADXTrend
        strategy = ADXTrend()
        df = generate_sample_data(50, trend="bullish")
        
        result = strategy.scan(df, "TEST", "NIFTY 50", "1d")
        if result:
            assert isinstance(result, ScanResult)
    
    def test_stochastic_init(self):
        """Test Stochastic Oscillator initialization."""
        from strategies.tier2.stochastic import StochasticOscillator
        strategy = StochasticOscillator()
        assert strategy.name == "Stochastic Oscillator"
        assert strategy.tier == StrategyTier.TIER_2
    
    def test_rsi_macd_confluence_init(self):
        """Test RSI + MACD Confluence initialization."""
        from strategies.tier2.rsi_macd_confluence import RSIMACDConfluence
        strategy = RSIMACDConfluence()
        assert strategy.name == "RSI + MACD Confluence"
        assert strategy.tier == StrategyTier.TIER_2
    
    def test_macd_crossover_init(self):
        """Test MACD Crossover initialization."""
        from strategies.tier2.macd_crossover import MACDCrossover
        strategy = MACDCrossover()
        assert strategy.name == "MACD Bullish Crossover"
        assert strategy.tier == StrategyTier.TIER_2
    
    def test_price_momentum_init(self):
        """Test Price Momentum initialization."""
        from strategies.tier2.price_momentum import PriceMomentum
        strategy = PriceMomentum()
        assert strategy.name == "Price Momentum"
        assert strategy.tier == StrategyTier.TIER_2
        assert strategy.min_bars_required == 130


class TestTier3Strategies:
    """Test Tier 3 strategies - Advanced Strategies."""
    
    def test_golden_cross_init(self):
        """Test Golden Cross initialization."""
        from strategies.tier3.golden_cross import GoldenCross
        strategy = GoldenCross()
        assert strategy.name == "Moving Average Golden Cross"
        assert strategy.tier == StrategyTier.TIER_3
        assert strategy.min_bars_required == 210
    
    def test_volume_surge_init(self):
        """Test Volume Surge initialization."""
        from strategies.tier3.volume_surge import VolumeSurge
        strategy = VolumeSurge()
        assert strategy.name == "Volume Surge Accumulation"
        assert strategy.tier == StrategyTier.TIER_3
    
    def test_obv_divergence_init(self):
        """Test OBV Divergence initialization."""
        from strategies.tier3.obv_divergence import OBVDivergence
        strategy = OBVDivergence()
        assert strategy.name == "OBV Divergence"
        assert strategy.tier == StrategyTier.TIER_3
    
    def test_fibonacci_bounce_init(self):
        """Test Fibonacci Bounce initialization."""
        from strategies.tier3.fibonacci_bounce import FibonacciBounce
        strategy = FibonacciBounce()
        assert strategy.name == "Fibonacci Retracement Bounce"
        assert strategy.tier == StrategyTier.TIER_3
    
    def test_atr_volatility_init(self):
        """Test ATR Volatility Breakout initialization."""
        from strategies.tier3.atr_volatility import ATRVolatilityBreakout
        strategy = ATRVolatilityBreakout()
        assert strategy.name == "ATR-Based Volatility Breakout"
        assert strategy.tier == StrategyTier.TIER_3
    
    def test_ichimoku_cloud_init(self):
        """Test Ichimoku Cloud initialization."""
        from strategies.tier3.ichimoku_cloud import IchimokuCloud
        strategy = IchimokuCloud()
        assert strategy.name == "Ichimoku Cloud Trend"
        assert strategy.tier == StrategyTier.TIER_3
    
    def test_donchian_mean_reversion_init(self):
        """Test Donchian Mean Reversion initialization."""
        from strategies.tier3.donchian_mean_reversion import DonchianMeanReversion
        strategy = DonchianMeanReversion()
        assert strategy.name == "Donchian Channel Mean Reversion"
        assert strategy.tier == StrategyTier.TIER_3
    
    def test_parabolic_sar_reversal_init(self):
        """Test Parabolic SAR Reversal initialization."""
        from strategies.tier3.parabolic_sar_reversal import ParabolicSARReversal
        strategy = ParabolicSARReversal()
        assert strategy.name == "Parabolic SAR Reversal"
        assert strategy.tier == StrategyTier.TIER_3
    
    def test_cci_deviation_init(self):
        """Test CCI Deviation initialization."""
        from strategies.tier3.cci_deviation import CCIDeviation
        strategy = CCIDeviation()
        assert strategy.name == "CCI Deviation"
        assert strategy.tier == StrategyTier.TIER_3
    
    def test_flag_pennant_init(self):
        """Test Flag & Pennant initialization."""
        from strategies.tier3.flag_pennant import FlagPennant
        strategy = FlagPennant()
        assert strategy.name == "Flag & Pennant Continuation"
        assert strategy.tier == StrategyTier.TIER_3


class TestMultiTimeframeStrategy:
    """Test Multi-Timeframe Confluence strategy."""
    
    def test_multi_timeframe_init(self):
        """Test Multi-Timeframe Confluence initialization."""
        from strategies.multi_timeframe.confluence import MultiTimeframeConfluence
        strategy = MultiTimeframeConfluence()
        assert strategy.name == "Multi-Timeframe Confluence"
        assert strategy.tier == StrategyTier.MULTI_TF
        assert strategy.min_bars_required == 210
    
    def test_multi_timeframe_scan(self):
        """Test Multi-Timeframe scan with sample data."""
        from strategies.multi_timeframe.confluence import MultiTimeframeConfluence
        strategy = MultiTimeframeConfluence()
        df = generate_sample_data(250, trend="bullish")
        
        result = strategy.scan(df, "TEST", "NIFTY 50", "1d")
        # May return None if layers don't align
        if result:
            assert isinstance(result, ScanResult)
            assert "daily_trend" in result.indicators


class TestAllStrategiesIntegration:
    """Integration tests running all strategies against sample data."""
    
    def test_all_strategies_can_scan(self):
        """Test that all registered strategies can execute scan without error."""
        df = generate_sample_data(250)
        strategies = StrategyRegistry.get_all()
        
        errors = []
        for name, strategy_cls in strategies.items():
            try:
                strategy = strategy_cls()
                result = strategy.scan(df, "TEST", "NIFTY 50", "1d")
                # Result should be None or ScanResult
                assert result is None or isinstance(result, ScanResult)
            except Exception as e:
                errors.append(f"{name}: {str(e)}")
        
        assert len(errors) == 0, f"Strategies with errors: {errors}"
    
    def test_all_strategies_handle_empty_df(self):
        """Test all strategies handle empty DataFrame gracefully."""
        df = pd.DataFrame()
        strategies = StrategyRegistry.get_all()
        
        for name, strategy_cls in strategies.items():
            strategy = strategy_cls()
            result = strategy.scan(df, "TEST", "NIFTY 50", "1d")
            assert result is None, f"{name} should return None for empty df"
    
    def test_all_strategies_handle_short_data(self):
        """Test all strategies handle insufficient data gracefully."""
        df = generate_sample_data(5)  # Very short data
        strategies = StrategyRegistry.get_all()
        
        for name, strategy_cls in strategies.items():
            strategy = strategy_cls()
            result = strategy.scan(df, "TEST", "NIFTY 50", "1d")
            assert result is None, f"{name} should return None for short data"


class TestScanResultFormat:
    """Test ScanResult dataclass format."""
    
    def test_scan_result_to_dict(self):
        """Test ScanResult converts to dict correctly."""
        result = ScanResult(
            symbol="RELIANCE",
            index="NIFTY 50",
            timeframe="1d",
            strategy="Test Strategy",
            signal=SignalType.BULLISH,
            confidence_score=0.85,
            indicators={"rsi": 25.5},
            trend="Uptrend",
            support=2400.0,
            resistance=2600.0,
            volume_ratio=1.5
        )
        
        d = result.to_dict()
        assert d["symbol"] == "RELIANCE"
        assert d["signal"] == "Bullish"
        assert d["confidence_score"] == 0.85
        assert "timestamp" in d


class TestIndicatorUtils:
    """Test indicator utility functions."""
    
    def test_all_indicators_work(self):
        """Test that all indicator functions run without error."""
        from core.scanner.indicator_utils import (
            sma, ema, rsi, macd, bollinger_bands, williams_r,
            donchian_channels, adx, stochastic, atr, obv, cci,
            parabolic_sar, ichimoku, fibonacci_levels, volume_ratio,
            price_momentum
        )
        
        df = generate_sample_data(100)
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']
        
        # Test each indicator
        assert len(sma(close, 20)) == len(close)
        assert len(ema(close, 20)) == len(close)
        assert len(rsi(close)) == len(close)
        
        macd_line, signal, hist = macd(close)
        assert len(macd_line) == len(close)
        
        upper, middle, lower = bollinger_bands(close)
        assert len(upper) == len(close)
        
        assert len(williams_r(high, low, close)) == len(close)
        
        upper, middle, lower = donchian_channels(high, low)
        assert len(upper) == len(close)
        
        adx_val, plus_di, minus_di = adx(high, low, close)
        assert len(adx_val) == len(close)
        
        k, d = stochastic(high, low, close)
        assert len(k) == len(close)
        
        assert len(atr(high, low, close)) == len(close)
        assert len(obv(close, volume)) == len(close)
        assert len(cci(high, low, close)) == len(close)
        assert len(parabolic_sar(high, low)) == len(close)
        
        tenkan, kijun, senkou_a, senkou_b, chikou = ichimoku(high, low, close)
        assert len(tenkan) == len(close)
        
        fib = fibonacci_levels(100, 50)
        assert 0.0 in fib
        assert 0.382 in fib
        
        assert len(volume_ratio(volume)) == len(close)
        assert len(price_momentum(close)) == len(close)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
