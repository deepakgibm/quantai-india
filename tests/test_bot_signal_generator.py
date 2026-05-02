"""
Bot Signal Generator — Unit Tests

Tests for BUY/SELL logic, conviction scoring, thresholds, and output format.
"""

import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from services.bot.signal_generator import SignalGenerator, BotSignal
from services.bot.analysis_engine import CorrelationResult, VolatilityResult


def make_corr(sym, val):
    return CorrelationResult(symbol=sym, value=val, category=CorrelationResult.categorize(val))

def make_vol(sym, std=0.02, atr=5.0):
    return VolatilityResult(symbol=sym, std_dev=std, atr=atr, category=VolatilityResult.categorize(std))

def make_pc(cur, prev):
    pct = round(((cur - prev) / prev) * 100, 2) if prev > 0 else 0
    return {"current": cur, "previous": prev, "change_pct": pct}


class TestSignalGeneration:
    gen = SignalGenerator()

    def test_bearish_sell(self):
        sigs = self.gen.generate_signals("BEARISH", {"R": make_corr("R", 0.85)},
            {"R": make_vol("R")}, {"R": make_pc(950, 1000)}, {})
        assert len(sigs) == 1 and sigs[0].signal_type == "SELL"

    def test_bullish_buy(self):
        sigs = self.gen.generate_signals("BULLISH", {"T": make_corr("T", 0.90)},
            {"T": make_vol("T")}, {"T": make_pc(1050, 1000)}, {})
        assert len(sigs) == 1 and sigs[0].signal_type == "BUY"

    def test_below_threshold_no_signal(self):
        sigs = self.gen.generate_signals("BULLISH", {"I": make_corr("I", 0.85)},
            {"I": make_vol("I")}, {"I": make_pc(1019, 1000)}, {})
        assert len(sigs) == 0

    def test_exactly_2pct(self):
        sigs = self.gen.generate_signals("BULLISH", {"H": make_corr("H", 0.80)},
            {"H": make_vol("H")}, {"H": make_pc(1020, 1000)}, {})
        assert len(sigs) == 1

    def test_low_corr_filtered(self):
        sigs = self.gen.generate_signals("BEARISH", {"W": make_corr("W", 0.5)},
            {"W": make_vol("W")}, {"W": make_pc(900, 1000)}, {})
        assert len(sigs) == 0

    def test_bullish_no_sell(self):
        sigs = self.gen.generate_signals("BULLISH", {"D": make_corr("D", 0.90)},
            {"D": make_vol("D")}, {"D": make_pc(900, 1000)}, {})
        assert len(sigs) == 0

    def test_bearish_no_buy(self):
        sigs = self.gen.generate_signals("BEARISH", {"U": make_corr("U", 0.90)},
            {"U": make_vol("U")}, {"U": make_pc(1100, 1000)}, {})
        assert len(sigs) == 0

    def test_missing_price_skipped(self):
        sigs = self.gen.generate_signals("BULLISH", {"N": make_corr("N", 0.90)},
            {"N": make_vol("N")}, {}, {})
        assert len(sigs) == 0

    def test_missing_vol_uses_unknown(self):
        sigs = self.gen.generate_signals("BEARISH", {"V": make_corr("V", 0.85)},
            {}, {"V": make_pc(950, 1000)}, {})
        assert len(sigs) == 1
        assert sigs[0].volatility_level == "UNKNOWN"

    def test_sorted_by_conviction(self):
        sigs = self.gen.generate_signals("BEARISH",
            {"A": make_corr("A", 0.90), "B": make_corr("B", 0.75), "C": make_corr("C", 0.85)},
            {"A": make_vol("A"), "B": make_vol("B"), "C": make_vol("C")},
            {"A": make_pc(900, 1000), "B": make_pc(970, 1000), "C": make_pc(930, 1000)}, {})
        assert len(sigs) == 3
        ranks = [{"STRONG": 0, "MODERATE": 1, "WEAK": 2}[s.conviction] for s in sigs]
        assert ranks == sorted(ranks)

    def test_corr_boundary_0_7(self):
        sigs = self.gen.generate_signals("BULLISH", {"B": make_corr("B", 0.70)},
            {"B": make_vol("B")}, {"B": make_pc(1050, 1000)}, {})
        assert len(sigs) == 1

    def test_corr_boundary_0_69(self):
        sigs = self.gen.generate_signals("BULLISH", {"B": make_corr("B", 0.69)},
            {"B": make_vol("B")}, {"B": make_pc(1050, 1000)}, {})
        assert len(sigs) == 0

    def test_empty_correlations(self):
        assert self.gen.generate_signals("BULLISH", {}, {}, {}, {}) == []


class TestConviction:
    def test_strong(self):
        c = SignalGenerator._calculate_conviction("SELL", 0.90, 6.0, 0.5)
        assert c == "STRONG"

    def test_moderate(self):
        c = SignalGenerator._calculate_conviction("BUY", 0.78, 3.5, None)
        assert c == "MODERATE"

    def test_weak(self):
        c = SignalGenerator._calculate_conviction("BUY", 0.71, 2.1, None)
        assert c == "WEAK"

    def test_pcr_boosts_sell(self):
        base = SignalGenerator._calculate_conviction("SELL", 0.75, 2.5, None)
        boosted = SignalGenerator._calculate_conviction("SELL", 0.75, 2.5, 0.5)
        r = {"STRONG": 0, "MODERATE": 1, "WEAK": 2}
        assert r[boosted] <= r[base]

    def test_pcr_boosts_buy(self):
        base = SignalGenerator._calculate_conviction("BUY", 0.75, 2.5, None)
        boosted = SignalGenerator._calculate_conviction("BUY", 0.75, 2.5, 1.3)
        r = {"STRONG": 0, "MODERATE": 1, "WEAK": 2}
        assert r[boosted] <= r[base]


class TestOutputFormat:
    gen = SignalGenerator()

    def test_to_dict_fields(self):
        sigs = self.gen.generate_signals("BULLISH", {"T": make_corr("T", 0.85)},
            {"T": make_vol("T", 0.02, 8.5)}, {"T": make_pc(1050, 1000)},
            {"T": {"pcr": 1.2, "source": "simulated"}})
        d = sigs[0].to_dict()
        for f in ["symbol", "signal_type", "correlation", "correlation_category",
                   "price_change_pct", "current_price", "volatility_level",
                   "volatility_atr", "pcr_value", "pcr_source", "conviction"]:
            assert f in d

    def test_pcr_none_output(self):
        sigs = self.gen.generate_signals("BULLISH", {"A": make_corr("A", 0.80)},
            {"A": make_vol("A")}, {"A": make_pc(1030, 1000)}, {})
        assert sigs[0].pcr_value is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
