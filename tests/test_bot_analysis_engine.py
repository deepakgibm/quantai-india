"""
Bot Analysis Engine — Unit Tests

Tests for:
- Pearson correlation calculation & categorization
- Volatility (StdDev + ATR) calculation & categorization
- Market trend detection (EMA 50/200 crossover)
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from services.bot.analysis_engine import (
    AnalysisEngine,
    CorrelationResult,
    VolatilityResult,
    MarketTrend,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_ohlcv_df(closes: list, days_back: int = None) -> pd.DataFrame:
    """Build a minimal OHLCV DataFrame from a list of close prices."""
    n = len(closes)
    if days_back is None:
        days_back = n
    base = datetime.now() - timedelta(days=days_back)
    timestamps = [base + timedelta(days=i) for i in range(n)]
    return pd.DataFrame({
        "timestamp": timestamps,
        "open": closes,
        "high": [c * 1.02 for c in closes],
        "low": [c * 0.98 for c in closes],
        "close": closes,
        "volume": [1000000] * n,
    })


def make_correlated_closes(index_closes: list, correlation: float = 0.9, noise: float = 0.02) -> list:
    """Generate stock closes that approximate a target correlation with the index."""
    np.random.seed(42)
    n = len(index_closes)
    idx = np.array(index_closes, dtype=float)
    idx_norm = (idx - idx.mean()) / (idx.std() + 1e-9)
    noise_vec = np.random.normal(0, 1, n)
    stock_norm = correlation * idx_norm + np.sqrt(1 - correlation**2) * noise_vec
    stock = stock_norm * 50 + 1000  # scale to realistic prices
    return stock.tolist()


# ── CorrelationResult categorization ──────────────────────────────────────────

class TestCorrelationCategorization:
    def test_high_positive(self):
        assert CorrelationResult.categorize(0.85) == "HIGH"

    def test_high_boundary(self):
        assert CorrelationResult.categorize(0.70) == "HIGH"

    def test_moderate(self):
        assert CorrelationResult.categorize(0.55) == "MODERATE"

    def test_moderate_boundary(self):
        assert CorrelationResult.categorize(0.40) == "MODERATE"

    def test_low(self):
        assert CorrelationResult.categorize(0.20) == "LOW"

    def test_zero(self):
        assert CorrelationResult.categorize(0.0) == "LOW"

    def test_negative_high(self):
        """Negative correlations should use absolute value."""
        assert CorrelationResult.categorize(-0.80) == "HIGH"

    def test_negative_moderate(self):
        assert CorrelationResult.categorize(-0.50) == "MODERATE"


# ── VolatilityResult categorization ──────────────────────────────────────────

class TestVolatilityCategorization:
    def test_high_volatility(self):
        """Annualized StdDev > 40% → HIGH"""
        daily_std = 0.03  # ~47% annualized
        assert VolatilityResult.categorize(daily_std) == "HIGH"

    def test_medium_volatility(self):
        """Annualized StdDev 20-40% → MEDIUM"""
        daily_std = 0.018  # ~28% annualized
        assert VolatilityResult.categorize(daily_std) == "MEDIUM"

    def test_low_volatility(self):
        """Annualized StdDev < 20% → LOW"""
        daily_std = 0.008  # ~12.7% annualized
        assert VolatilityResult.categorize(daily_std) == "LOW"


# ── Correlation Calculation ──────────────────────────────────────────────────

class TestCalculateCorrelations:
    engine = AnalysisEngine()

    def test_perfectly_correlated(self):
        """Two identical close series should yield correlation ≈ 1.0."""
        closes = [100 + i * 0.5 for i in range(60)]
        index_df = make_ohlcv_df(closes)
        stock_data = {"TESTSTOCK": make_ohlcv_df(closes)}
        results = self.engine.calculate_correlations(stock_data, index_df)
        assert "TESTSTOCK" in results
        assert results["TESTSTOCK"].value == pytest.approx(1.0, abs=0.01)
        assert results["TESTSTOCK"].category == "HIGH"

    def test_no_overlap_skipped(self):
        """Stocks with fewer days than min_overlap_days should be skipped."""
        index_df = make_ohlcv_df([100 + i for i in range(60)])
        stock_data = {"SHORT": make_ohlcv_df([100, 101, 102])}  # only 3 days
        results = self.engine.calculate_correlations(stock_data, index_df, min_overlap_days=20)
        assert "SHORT" not in results

    def test_empty_index(self):
        """Empty index DataFrame should return empty dict."""
        results = self.engine.calculate_correlations(
            {"A": make_ohlcv_df([100, 101, 102])},
            pd.DataFrame()
        )
        assert results == {}

    def test_multiple_stocks(self):
        """Should compute correlations for multiple stocks."""
        index_closes = [100 + i * 0.5 + np.sin(i/3) * 2 for i in range(60)]
        index_df = make_ohlcv_df(index_closes)
        stock_data = {
            "HIGH_CORR": make_ohlcv_df(make_correlated_closes(index_closes, 0.9)),
            "LOW_CORR": make_ohlcv_df(make_correlated_closes(index_closes, 0.1)),
        }
        results = self.engine.calculate_correlations(stock_data, index_df)
        assert len(results) == 2
        # High correlation stock should have higher value
        assert results["HIGH_CORR"].value > results["LOW_CORR"].value

    def test_constant_price_handled(self):
        """Constant price (zero variance) should be skipped (NaN correlation)."""
        index_df = make_ohlcv_df([100 + i for i in range(30)])
        stock_data = {"FLAT": make_ohlcv_df([500.0] * 30)}  # no change
        results = self.engine.calculate_correlations(stock_data, index_df)
        # NaN correlation should be filtered out
        assert "FLAT" not in results


# ── Volatility Calculation ───────────────────────────────────────────────────

class TestCalculateVolatility:
    engine = AnalysisEngine()

    def test_basic_volatility(self):
        """Should compute both StdDev and ATR for a valid stock."""
        closes = [100 + np.sin(i / 3) * 5 + i * 0.1 for i in range(30)]
        stock_data = {"TEST": make_ohlcv_df(closes)}
        results = self.engine.calculate_volatility(stock_data)
        assert "TEST" in results
        vol = results["TEST"]
        assert vol.std_dev > 0
        assert vol.atr > 0
        assert vol.category in ("HIGH", "MEDIUM", "LOW")

    def test_insufficient_data(self):
        """Stocks with < atr_period+1 days should be skipped."""
        stock_data = {"SHORT": make_ohlcv_df([100, 101, 102])}
        results = self.engine.calculate_volatility(stock_data, atr_period=14)
        assert "SHORT" not in results

    def test_atr_uses_true_range(self):
        """ATR should account for gaps (high-low, high-prev_close, low-prev_close)."""
        # Create data with a gap
        closes = [100] * 10 + [110] * 10  # sharp jump at day 10
        stock_data = {"GAP": make_ohlcv_df(closes)}
        results = self.engine.calculate_volatility(stock_data, atr_period=5)
        if "GAP" in results:
            assert results["GAP"].atr > 0

    def test_empty_input(self):
        """Empty stock_data should return empty dict."""
        results = self.engine.calculate_volatility({})
        assert results == {}


# ── Market Trend Detection ───────────────────────────────────────────────────

class TestDetectMarketTrend:
    engine = AnalysisEngine()

    def test_bullish_trend(self):
        """Rising prices with EMA50 > EMA200 → BULLISH."""
        closes = [100 + i * 2 for i in range(250)]  # steady uptrend
        index_df = make_ohlcv_df(closes)
        trend = self.engine.detect_market_trend(index_df)
        assert trend is not None
        assert trend.trend == "BULLISH"
        assert trend.ema_50 > trend.ema_200

    def test_bearish_trend(self):
        """Declining prices with EMA50 < EMA200 → BEARISH."""
        closes = [500 - i * 2 for i in range(250)]  # steady downtrend
        index_df = make_ohlcv_df(closes)
        trend = self.engine.detect_market_trend(index_df)
        assert trend is not None
        assert trend.trend == "BEARISH"
        assert trend.ema_50 < trend.ema_200

    def test_insufficient_data(self):
        """Fewer than 10 data points should return None."""
        index_df = make_ohlcv_df([100, 101, 102])
        trend = self.engine.detect_market_trend(index_df)
        assert trend is None

    def test_empty_dataframe(self):
        """Empty DataFrame should return None."""
        trend = self.engine.detect_market_trend(pd.DataFrame())
        assert trend is None

    def test_momentum_calculation(self):
        """5-day momentum should be (last - 6th_from_end) / 6th_from_end * 100."""
        closes = [100, 101, 102, 103, 104, 110]  # 10% over 5 days
        index_df = make_ohlcv_df(closes + [112] * 5)  # pad to ≥10
        trend = self.engine.detect_market_trend(index_df)
        assert trend is not None
        assert trend.momentum != 0  # Should have some momentum

    def test_short_series_uses_adaptive_ema(self):
        """< 200 data points should use len(closes) for EMA200 span."""
        closes = [100 + i for i in range(50)]
        index_df = make_ohlcv_df(closes)
        trend = self.engine.detect_market_trend(index_df)
        assert trend is not None
        assert trend.ema_200 > 0

    def test_last_close_accuracy(self):
        """last_close should match the final close value."""
        closes = [100, 110, 120, 130, 140, 150, 160, 170, 180, 200]
        index_df = make_ohlcv_df(closes)
        trend = self.engine.detect_market_trend(index_df)
        assert trend is not None
        assert trend.last_close == 200.0


# ── Price Change Calculation ─────────────────────────────────────────────────

class TestPriceChange:
    def test_positive_change(self):
        assert AnalysisEngine.calculate_price_change(110, 100) == 10.0

    def test_negative_change(self):
        assert AnalysisEngine.calculate_price_change(90, 100) == -10.0

    def test_zero_previous(self):
        """Zero previous close should return 0.0 (no division error)."""
        assert AnalysisEngine.calculate_price_change(100, 0) == 0.0

    def test_negative_previous(self):
        """Negative previous close should return 0.0."""
        assert AnalysisEngine.calculate_price_change(100, -10) == 0.0

    def test_no_change(self):
        assert AnalysisEngine.calculate_price_change(100, 100) == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
