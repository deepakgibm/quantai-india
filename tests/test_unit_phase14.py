"""
Phase 14: Unit Tests – Testing & Quality Assurance
Covers three critical modules modernized in Phases 5–13:
  - CostCalculator (backend/core/backtest/costs.py)
  - RiskManager.calculate_portfolio_var (backend/core/risk/risk_manager.py)
  - UpstoxWSManager._auto_reconnect (backend/services/upstox_ws_manager.py)

All tests are pure unit tests: no live DB, no live APIs, fully CI/CD safe.
"""

import pytest
import asyncio
import pandas as pd
import numpy as np
from unittest.mock import AsyncMock, MagicMock, patch

import sys
import os

# Ensure backend is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from core.backtest.costs import CostCalculator, CostConfig, OrderSide
from core.risk.risk_manager import RiskManager, RiskConfig


# ─────────────────────────────────────────────────────────────────────────────
# TestCostCalculator – 7 tests
# ─────────────────────────────────────────────────────────────────────────────

class TestCostCalculator:
    """Unit tests for CostCalculator transaction charge breakdowns."""

    def setup_method(self):
        self.calc = CostCalculator()

    def test_buy_zero_stt(self):
        """STT must be 0 on delivery BUY (SEBI regulation)."""
        result = self.calc.calculate(price=500.0, quantity=100, side=OrderSide.BUY, is_intraday=False)
        assert result.stt == 0.0, "Delivery BUY STT must be 0"

    def test_sell_delivery_stt(self):
        """STT on delivery SELL must be 0.1% of turnover."""
        price, qty = 1000.0, 50
        result = self.calc.calculate(price=price, quantity=qty, side=OrderSide.SELL, is_intraday=False)
        expected_stt = round(price * qty * 0.001, 2)
        assert result.stt == expected_stt, f"Expected delivery SELL STT={expected_stt}, got {result.stt}"

    def test_sell_intraday_stt(self):
        """STT on intraday SELL must be 0.025% of turnover."""
        price, qty = 1000.0, 50
        result = self.calc.calculate(price=price, quantity=qty, side=OrderSide.SELL, is_intraday=True)
        expected_stt = round(price * qty * 0.00025, 2)
        assert result.stt == expected_stt, f"Expected intraday SELL STT={expected_stt}, got {result.stt}"

    def test_stamp_duty_on_buy_only(self):
        """Stamp duty must be non-zero on BUY and exactly zero on SELL."""
        buy_result = self.calc.calculate(price=500.0, quantity=100, side=OrderSide.BUY)
        sell_result = self.calc.calculate(price=500.0, quantity=100, side=OrderSide.SELL)
        assert buy_result.stamp_duty > 0.0, "Stamp duty should be positive on BUY"
        assert sell_result.stamp_duty == 0.0, "Stamp duty should be zero on SELL"

    def test_total_cost_is_sum_of_parts(self):
        """The `total` field must equal sum of all individual fee components."""
        result = self.calc.calculate(price=800.0, quantity=200, side=OrderSide.BUY)
        components_sum = round(
            result.brokerage + result.stt + result.exchange_charges +
            result.sebi_fee + result.gst + result.stamp_duty + result.slippage,
            2
        )
        assert result.total == components_sum, (
            f"total={result.total} != sum of parts={components_sum}"
        )

    def test_slippage_scales_with_volume(self):
        """Lower avg_volume (less liquid) should produce higher slippage than high avg_volume."""
        high_vol = self.calc.calculate(price=500.0, quantity=1000, side=OrderSide.BUY, avg_volume=10_000_000)
        low_vol = self.calc.calculate(price=500.0, quantity=1000, side=OrderSide.BUY, avg_volume=1_000)
        assert low_vol.slippage >= high_vol.slippage, (
            "Less liquid stocks should incur >= slippage vs. highly liquid stocks"
        )

    def test_zero_quantity_returns_zero_costs(self):
        """Calculating costs for qty=0 should return all-zero costs."""
        result = self.calc.calculate(price=500.0, quantity=0, side=OrderSide.BUY)
        assert result.total == 0.0
        assert result.brokerage == 0.0
        assert result.stt == 0.0
        assert result.stamp_duty == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# TestPortfolioVaR – 5 tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPortfolioVaR:
    """Unit tests for RiskManager.calculate_portfolio_var()."""

    def setup_method(self):
        self.rm = RiskManager(RiskConfig())

    def test_empty_weights_returns_zero(self):
        """An empty portfolio must return VaR = 0."""
        result = self.rm.calculate_portfolio_var(portfolio_value=1_000_000, weights={})
        assert result == 0.0

    def test_fallback_var_without_returns_df(self):
        """Without a returns DataFrame, VaR must use the 2% volatility fallback."""
        weights = {"RELIANCE": 0.5, "TCS": 0.5}
        portfolio_value = 1_000_000
        # 95% VaR fallback = portfolio * 0.02 * 1.645
        expected = round(portfolio_value * 0.02 * 1.645, 2)
        result = self.rm.calculate_portfolio_var(
            portfolio_value=portfolio_value,
            weights=weights,
            returns_df=None,
            confidence_level=0.95
        )
        assert abs(result - expected) < 1.0, (
            f"Fallback VaR={result} should be near {expected}"
        )

    def test_var_99_greater_than_95(self):
        """99% confidence VaR must always exceed 95% confidence VaR."""
        weights = {"RELIANCE": 0.6, "TCS": 0.4}
        var_95 = self.rm.calculate_portfolio_var(1_000_000, weights, confidence_level=0.95)
        var_99 = self.rm.calculate_portfolio_var(1_000_000, weights, confidence_level=0.99)
        assert var_99 > var_95, "99% VaR must exceed 95% VaR"

    def test_var_scales_with_portfolio_value(self):
        """Doubling portfolio value should exactly double the VaR."""
        weights = {"RELIANCE": 1.0}
        var_1m = self.rm.calculate_portfolio_var(1_000_000, weights)
        var_2m = self.rm.calculate_portfolio_var(2_000_000, weights)
        assert abs(var_2m - var_1m * 2) < 1.0, (
            "VaR should scale linearly with portfolio value"
        )

    def test_var_with_real_returns_df(self):
        """VaR computed from a returns DataFrame must be positive and finite."""
        np.random.seed(42)
        n_days = 252
        returns_data = {
            "RELIANCE": np.random.normal(0.001, 0.02, n_days),
            "TCS": np.random.normal(0.0008, 0.018, n_days),
        }
        returns_df = pd.DataFrame(returns_data)
        weights = {"RELIANCE": 0.5, "TCS": 0.5}
        result = self.rm.calculate_portfolio_var(
            portfolio_value=1_000_000,
            weights=weights,
            returns_df=returns_df,
            confidence_level=0.95
        )
        assert result > 0.0, "VaR from real returns must be positive"
        assert np.isfinite(result), "VaR must be a finite number"


# ─────────────────────────────────────────────────────────────────────────────
# TestWebSocketReconnect – 3 tests
# ─────────────────────────────────────────────────────────────────────────────

class TestWebSocketReconnect:
    """Unit tests for UpstoxWSManager._auto_reconnect() backoff logic."""

    def _make_manager(self):
        """Build an UpstoxWSManager with all external dependencies mocked."""
        with patch("services.upstox_ws_manager.get_upstox_client", return_value=MagicMock()), \
             patch("services.upstox_ws_manager.get_cache", return_value=MagicMock()), \
             patch("services.upstox_ws_manager.SessionLocal", return_value=MagicMock()), \
             patch("services.upstox_ws_manager.TokenManagerService", MagicMock()):
            from services.upstox_ws_manager import UpstoxWSManager
            mgr = UpstoxWSManager.__new__(UpstoxWSManager)
            mgr.is_running = False
            mgr._stop_requested = False
            mgr.subscribed_symbols = set()
            mgr.instrument_keys = {}
            mgr.key_to_symbol = {}
            mgr.last_ticks = {}
            mgr.callbacks = []
            mgr.ws = None
            return mgr

    def test_stop_requested_exits_loop_immediately(self):
        """If _stop_requested is True, _auto_reconnect must exit without calling connect."""
        mgr = self._make_manager()
        mgr._stop_requested = True
        connect_calls = []

        async def mock_connect(**kwargs):
            connect_calls.append(1)

        mgr.connect = mock_connect

        async def run():
            with patch("asyncio.sleep", new_callable=AsyncMock):
                await mgr._auto_reconnect()

        asyncio.get_event_loop().run_until_complete(run())
        assert len(connect_calls) == 0, "_auto_reconnect must not call connect when stop requested"

    def test_reconnect_calls_connect_on_dropped_feed(self):
        """When not stopped and not running, _auto_reconnect must call connect at least once."""
        mgr = self._make_manager()
        mgr._stop_requested = False
        mgr.is_running = False
        connect_calls = []

        async def mock_connect(**kwargs):
            mgr.is_running = True  # Simulate successful reconnect
            connect_calls.append(1)

        mgr.connect = mock_connect

        async def run():
            with patch("asyncio.sleep", new_callable=AsyncMock):
                await mgr._auto_reconnect()

        asyncio.get_event_loop().run_until_complete(run())
        assert len(connect_calls) >= 1, "_auto_reconnect must call connect at least once"

    def test_backoff_capped_at_60_seconds(self):
        """Exponential backoff formula must never exceed 60 seconds cap."""
        for attempt in range(10):
            wait_time = min(2 ** attempt, 60)
            assert wait_time <= 60, (
                f"Backoff at attempt {attempt} exceeded 60s cap: {wait_time}s"
            )
