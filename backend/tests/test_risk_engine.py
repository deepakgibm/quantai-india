import sys
import os
import unittest
from datetime import date

# Add backend to path
sys.path.append(os.path.join(os.getcwd()))

from core.risk.risk_manager import RiskManager, RiskConfig
from core.backtest.executor import OrderSide

class TestRiskEngine(unittest.TestCase):
    def setUp(self):
        self.config = RiskConfig(
            max_concentration=0.20,
            risk_per_trade=0.01,
            atr_multiplier=2.0
        )
        self.rm = RiskManager(self.config)

    def test_atr_stop_calculation(self):
        # Buy at 100, ATR is 2 -> Stop should be 100 - (2 * 2) = 96
        stop = self.rm.calculate_atr_stop(100.0, 2.0, "BUY")
        self.assertEqual(stop, 96.0)
        
        # Sell at 100, ATR is 2 -> Stop should be 100 + (2 * 2) = 104
        stop = self.rm.calculate_atr_stop(100.0, 2.0, "SELL")
        self.assertEqual(stop, 104.0)

    def test_position_sizing(self):
        equity = 100000.0
        price = 100.0
        stop = 95.0 # $5 risk per share
        
        # Risk is 1% of 100,000 = $1,000
        # Qty = 1,000 / 5 = 200
        qty = self.rm.calculate_position_size(equity, price, stop)
        self.assertEqual(qty, 200)

    def test_concentration_limit(self):
        equity = 100000.0
        price = 1000.0
        stop = 900.0 # $100 risk per share
        
        # Risk amount = $1,000 -> Qty = 1,000 / 100 = 10 shares
        # Notional = 10 * 1,000 = $10,000 (10% of equity)
        # Limit is 20% ($20,000) -> OK
        qty = self.rm.calculate_position_size(equity, price, stop)
        self.assertEqual(qty, 10)
        
        # Now lower concentration to 5%
        self.rm.config.max_concentration = 0.05 # $5,000 limit
        qty = self.rm.calculate_position_size(equity, price, stop)
        # Limit hits: $5,000 / 1,000 = 5 shares
        self.assertEqual(qty, 5)

if __name__ == "__main__":
    unittest.main()
