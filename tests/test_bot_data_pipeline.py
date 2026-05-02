"""
Bot Data Pipeline — Unit Tests

Tests for NIFTY 500 CSV loading, DB data schema, and batch quote logic.
"""

import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from services.bot.data_collector import DataCollector


class TestNifty500CSVLoading:
    collector = DataCollector()

    def test_loads_symbols(self):
        """Should load symbols from nifty_500.csv."""
        symbols = self.collector.load_nifty500_symbols()
        assert len(symbols) > 400, f"Expected 400+ symbols, got {len(symbols)}"

    def test_symbol_format(self):
        """Each entry should be a (symbol, instrument_key) tuple."""
        symbols = self.collector.load_nifty500_symbols()
        for sym, ik in symbols[:5]:
            assert isinstance(sym, str) and len(sym) > 0
            assert isinstance(ik, str) and ik.startswith("NSE_EQ|")

    def test_no_empty_symbols(self):
        """No symbol or instrument_key should be empty."""
        symbols = self.collector.load_nifty500_symbols()
        for sym, ik in symbols:
            assert sym.strip() != ""
            assert ik.strip() != ""

    def test_cache_works(self):
        """Second call should use cached data."""
        c = DataCollector()
        first = c.load_nifty500_symbols()
        second = c.load_nifty500_symbols()
        assert first is second  # same list object (cached)

    def test_contains_known_stocks(self):
        """Should contain well-known NIFTY stocks."""
        symbols = self.collector.load_nifty500_symbols()
        names = [s[0] for s in symbols]
        # Check for a few major stocks (using partial match for names with "Ltd")
        found_reliance = any("Reliance" in n for n in names)
        found_tcs = any("Tata Consultancy" in n for n in names)
        found_infosys = any("Infosys" in n for n in names)
        assert found_reliance, "Reliance Industries not found"
        assert found_tcs, "TCS not found"
        assert found_infosys, "Infosys not found"


class TestNifty50InstrumentKey:
    def test_instrument_key_format(self):
        """NIFTY 50 instrument key should be correct."""
        assert DataCollector.NIFTY50_INSTRUMENT_KEY == "NSE_INDEX|Nifty 50"


class TestBatchLogic:
    """Test the batch splitting logic used for live quote fetching."""

    def test_batch_splitting(self):
        """500 keys with batch_size=50 should produce 10 batches."""
        keys = [f"NSE_EQ|KEY{i}" for i in range(500)]
        batch_size = 50
        batches = [keys[i:i+batch_size] for i in range(0, len(keys), batch_size)]
        assert len(batches) == 10
        assert all(len(b) == 50 for b in batches)

    def test_uneven_batch(self):
        """Non-even split should have a smaller last batch."""
        keys = [f"NSE_EQ|KEY{i}" for i in range(123)]
        batch_size = 50
        batches = [keys[i:i+batch_size] for i in range(0, len(keys), batch_size)]
        assert len(batches) == 3
        assert len(batches[-1]) == 23


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
