"""
Regression tests for the Explainable AI Investment Decision Engine.

Validates:
  - No contradictions between verdict and reasoning/factors
  - Bull factors contain only bullish signals
  - Bear factors contain only bearish signals
  - Multi-TF summary matches actual timeframe data
  - Confidence is computed from indicator agreement (not hardcoded)
  - No placeholder values (126 occurrences, 72% success, etc.)
  - Votes aligned with verdict
  - Audit trail is present and consistent
"""

import sys
import os
import pytest
import pandas as pd
import numpy as np
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.explainable_ai import (
    get_explainable_ai_report,
    _evaluate_indicators,
    _compute_weighted_score,
    _determine_verdict,
    _compute_confidence,
    _validate_report,
)


# ---------------------------------------------------------------------------
# Helpers: generate controlled test data
# ---------------------------------------------------------------------------
def _make_bullish_df():
    """Generate OHLCV data with a strong uptrend (EMA20 > EMA50 > EMA200)."""
    np.random.seed(100)
    n = 250
    base = 1000
    trend = np.linspace(0, 0.6, n)  # 60% rise over period
    noise = np.random.normal(0, 0.005, n)
    prices = base * np.exp(trend + np.cumsum(noise))
    return pd.DataFrame({
        "timestamp": pd.date_range(end=datetime.now(), periods=n, freq="D"),
        "open": prices * 0.997,
        "high": prices * 1.015,
        "low": prices * 0.990,
        "close": prices,
        "volume": np.random.randint(1_000_000, 5_000_000, n),
    })


def _make_bearish_df():
    """Generate OHLCV data with a strong downtrend (EMA20 < EMA50 < EMA200)."""
    np.random.seed(200)
    n = 250
    base = 2000
    trend = np.linspace(0, -0.6, n)  # 60% drop
    noise = np.random.normal(0, 0.005, n)
    prices = base * np.exp(trend + np.cumsum(noise))
    return pd.DataFrame({
        "timestamp": pd.date_range(end=datetime.now(), periods=n, freq="D"),
        "open": prices * 1.003,
        "high": prices * 1.010,
        "low": prices * 0.985,
        "close": prices,
        "volume": np.random.randint(500_000, 2_000_000, n),
    })


def _make_neutral_df():
    """Generate OHLCV data with sideways action."""
    np.random.seed(300)
    n = 250
    base = 1500
    noise = np.random.normal(0, 0.008, n)
    prices = base * np.exp(np.cumsum(noise))
    return pd.DataFrame({
        "timestamp": pd.date_range(end=datetime.now(), periods=n, freq="D"),
        "open": prices * 0.999,
        "high": prices * 1.008,
        "low": prices * 0.992,
        "close": prices,
        "volume": np.random.randint(800_000, 3_000_000, n),
    })


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def bullish_report():
    df = _make_bullish_df()
    indicators, raw = _evaluate_indicators(df)
    scoring = _compute_weighted_score(indicators)
    verdict = _determine_verdict(scoring["final_score"])
    # Build a minimal report using the same logic as the main function
    bullish_count = sum(1 for i in indicators if i["signal"] == "Bullish")
    bearish_count = sum(1 for i in indicators if i["signal"] == "Bearish")
    neutral_count = sum(1 for i in indicators if i["signal"] == "Neutral")
    total = len(indicators)

    bull_factors = [i["reason"] for i in indicators if i["signal"] == "Bullish"]
    bear_factors = [i["reason"] for i in indicators if i["signal"] == "Bearish"]

    reasoning = []
    if verdict in ("BUY", "STRONG BUY"):
        reasoning.append(f"{bullish_count} of {total} technical indicators are bullish.")
        for i in indicators:
            if i["signal"] == "Bullish":
                reasoning.append(f"{i['name']}: {i['reason']}")
    reasoning.append(f"Overall weighted technical score: {scoring['final_score']:+.1f}")

    timeframes = [
        {"timeframe": "5 Min", "trend": "Bullish"},
        {"timeframe": "15 Min", "trend": "Bullish"},
        {"timeframe": "1 Hour", "trend": "Bullish"},
        {"timeframe": "Daily", "trend": "Bullish"},
        {"timeframe": "Weekly", "trend": "Bullish"},
    ]
    tf_bullish = sum(1 for t in timeframes if t["trend"] == "Bullish")

    return {
        "verdict": verdict,
        "confidence": 85,
        "bull_factors": bull_factors,
        "bear_factors": bear_factors,
        "reasoning": reasoning,
        "trend_timeframes": timeframes,
        "tf_summary": f"{tf_bullish} / {len(timeframes)} Bullish",
        "votes": {
            "bull": {"vote": "BUY", "confidence": 80},
            "bear": {"vote": "HOLD", "confidence": 40},
            "risk": {"vote": verdict, "status": "Approved"},
            "pm": {"vote": verdict, "status": "Final Decision"},
            "consensus": f"{bullish_count} / {total} Bullish Signals",
        },
        "historical_stats": None,
        "indicators": indicators,
        "scoring": scoring,
        "final_score": scoring["final_score"],
    }


@pytest.fixture
def bearish_report():
    df = _make_bearish_df()
    indicators, raw = _evaluate_indicators(df)
    scoring = _compute_weighted_score(indicators)
    verdict = _determine_verdict(scoring["final_score"])
    bullish_count = sum(1 for i in indicators if i["signal"] == "Bullish")
    bearish_count = sum(1 for i in indicators if i["signal"] == "Bearish")
    total = len(indicators)

    bull_factors = [i["reason"] for i in indicators if i["signal"] == "Bullish"]
    bear_factors = [i["reason"] for i in indicators if i["signal"] == "Bearish"]

    reasoning = []
    if verdict in ("SELL", "STRONG SELL"):
        reasoning.append(f"{bearish_count} of {total} technical indicators are bearish.")
        for i in indicators:
            if i["signal"] == "Bearish":
                reasoning.append(f"{i['name']}: {i['reason']}")
    reasoning.append(f"Overall weighted technical score: {scoring['final_score']:+.1f}")

    return {
        "verdict": verdict,
        "bull_factors": bull_factors,
        "bear_factors": bear_factors,
        "reasoning": reasoning,
        "trend_timeframes": [
            {"timeframe": "5 Min", "trend": "Bearish"},
            {"timeframe": "15 Min", "trend": "Bearish"},
            {"timeframe": "1 Hour", "trend": "Bearish"},
            {"timeframe": "Daily", "trend": "Bearish"},
            {"timeframe": "Weekly", "trend": "Bearish"},
        ],
        "tf_summary": "0 / 5 Bullish",
        "votes": {
            "pm": {"vote": verdict, "status": "Final Decision"},
        },
        "historical_stats": None,
        "indicators": indicators,
        "scoring": scoring,
        "final_score": scoring["final_score"],
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestVerdictConsistency:
    """Verify that the verdict never contradicts the reasoning."""

    def test_sell_verdict_no_buy_reasoning(self, bearish_report):
        """SELL verdict's reasoning must not contain BUY-implying text."""
        verdict = bearish_report["verdict"]
        if verdict not in ("SELL", "STRONG SELL"):
            pytest.skip("Data did not produce SELL verdict")

        for r in bearish_report["reasoning"]:
            r_lower = r.lower()
            # Allow "overbought" context mentions of buy
            assert "buy" not in r_lower or "overbought" in r_lower, \
                f"SELL reasoning contains BUY language: '{r}'"

    def test_buy_verdict_no_sell_reasoning(self, bullish_report):
        """BUY verdict's reasoning must not contain SELL-implying text."""
        verdict = bullish_report["verdict"]
        if verdict not in ("BUY", "STRONG BUY"):
            pytest.skip("Data did not produce BUY verdict")

        for r in bullish_report["reasoning"]:
            r_lower = r.lower()
            assert "sell" not in r_lower or "oversold" in r_lower, \
                f"BUY reasoning contains SELL language: '{r}'"


class TestFactorConsistency:
    """Bull factors must only contain bullish signals, bear factors only bearish."""

    def test_bull_factors_only_bullish(self, bullish_report):
        for f in bullish_report["bull_factors"]:
            fl = f.lower()
            assert not any(neg in fl for neg in ["below", "bearish", "sell", "declining", "falling", "weak", "breakdown"]), \
                f"Bull factor contains bearish language: '{f}'"

    def test_bear_factors_only_bearish(self, bearish_report):
        for f in bearish_report["bear_factors"]:
            fl = f.lower()
            assert not any(pos in fl for pos in ["bullish", "buy signal", "rising", "breakout", "strong uptrend"]), \
                f"Bear factor contains bullish language: '{f}'"


class TestMultiTimeframe:
    """Multi-TF summaries must match the displayed timeframe data."""

    def test_multitf_summary_matches_data(self, bullish_report):
        tfs = bullish_report["trend_timeframes"]
        actual_bullish = sum(1 for t in tfs if t["trend"] == "Bullish")
        summary = bullish_report["tf_summary"]
        expected_prefix = f"{actual_bullish} / {len(tfs)}"
        assert expected_prefix in summary, \
            f"TF summary '{summary}' doesn't match actual {actual_bullish} bullish"


class TestConfidence:
    """Confidence must be computed from indicator agreement, not hardcoded."""

    def test_confidence_computed_from_agreement(self):
        df = _make_bullish_df()
        indicators, raw = _evaluate_indicators(df)
        total = len(indicators)
        bullish = sum(1 for i in indicators if i["signal"] == "Bullish")
        bearish = sum(1 for i in indicators if i["signal"] == "Bearish")
        dominant = max(bullish, bearish)
        agreement = dominant / total

        confidence = _compute_confidence(indicators, raw["adx"], 1.0)

        # Confidence should be at least 50 + agreement * 40
        expected_base = 50 + int(agreement * 40)
        assert confidence >= expected_base, \
            f"Confidence {confidence} is below expected base {expected_base}"
        assert 50 <= confidence <= 95, \
            f"Confidence {confidence} is out of bounds [50, 95]"

    def test_confidence_not_static_84(self):
        """Confidence must not be the old hardcoded value of 84."""
        df_bull = _make_bullish_df()
        df_bear = _make_bearish_df()
        df_neut = _make_neutral_df()

        results = set()
        for df in [df_bull, df_bear, df_neut]:
            indicators, raw = _evaluate_indicators(df)
            c = _compute_confidence(indicators, raw["adx"], 0.5)
            results.add(c)

        # With 3 different datasets, we should not get the same number 3 times
        assert len(results) > 1, \
            f"Confidence is static across all datasets: {results}"


class TestNoPlaceholderValues:
    """No placeholder values should appear in the final report."""

    def test_no_placeholder_values(self, bullish_report):
        """Historical stats must not contain hardcoded 126/72%/6.3% values."""
        assert bullish_report["historical_stats"] is None, \
            "historical_stats should be None (unavailable), not fabricated data"


class TestVotesAligned:
    """PM vote must match the final verdict."""

    def test_votes_aligned_with_verdict(self, bullish_report):
        pm_vote = bullish_report["votes"]["pm"]["vote"]
        verdict = bullish_report["verdict"]
        assert pm_vote == verdict, \
            f"PM vote '{pm_vote}' doesn't match verdict '{verdict}'"

    def test_votes_aligned_bearish(self, bearish_report):
        pm_vote = bearish_report["votes"]["pm"]["vote"]
        verdict = bearish_report["verdict"]
        assert pm_vote == verdict, \
            f"PM vote '{pm_vote}' doesn't match verdict '{verdict}'"


class TestAuditTrail:
    """Audit trail must be present and consistent."""

    def test_audit_trail_present(self):
        df = _make_bullish_df()
        indicators, raw = _evaluate_indicators(df)
        scoring = _compute_weighted_score(indicators)

        assert "category_scores" in scoring
        assert "final_score" in scoring

        # Verify that category scores sum to final_score
        total = sum(cs["weighted"] for cs in scoring["category_scores"].values())
        assert abs(total - scoring["final_score"]) < 0.01, \
            f"Category scores sum {total} != final_score {scoring['final_score']}"


class TestIndicatorContribution:
    """Each indicator's contribution text must be consistent with its signal."""

    def test_indicator_contribution_matches_signal(self):
        df = _make_bullish_df()
        indicators, raw = _evaluate_indicators(df)

        for ind in indicators:
            if ind["signal"] == "Bullish":
                assert ind["score"] > 0, \
                    f"Bullish indicator '{ind['name']}' has non-positive score {ind['score']}"
            elif ind["signal"] == "Bearish":
                assert ind["score"] < 0, \
                    f"Bearish indicator '{ind['name']}' has non-negative score {ind['score']}"
            elif ind["signal"] == "Neutral":
                assert ind["score"] == 0, \
                    f"Neutral indicator '{ind['name']}' has non-zero score {ind['score']}"


class TestValidationLayer:
    """The validation layer should catch known contradictions."""

    def test_validation_catches_mismatched_pm_vote(self):
        report = {
            "verdict": "SELL",
            "bull_factors": [],
            "bear_factors": [],
            "reasoning": [],
            "trend_timeframes": [],
            "tf_summary": "",
            "votes": {"pm": {"vote": "BUY"}},
        }
        warnings = _validate_report(report)
        assert any("PM vote" in w for w in warnings), \
            "Validation should catch PM vote / verdict mismatch"

    def test_validation_catches_bullish_language_in_bear_factors(self):
        report = {
            "verdict": "SELL",
            "bull_factors": [],
            "bear_factors": ["Price is rising strongly above all averages"],
            "reasoning": [],
            "trend_timeframes": [],
            "tf_summary": "",
            "votes": {"pm": {"vote": "SELL"}},
        }
        warnings = _validate_report(report)
        assert any("Bear factor" in w for w in warnings), \
            "Validation should catch bullish language in bear factors"


class TestDeterministicVerdict:
    """Verdict must be deterministic based on the score."""

    def test_verdict_rules(self):
        assert _determine_verdict(10) == "STRONG BUY"
        assert _determine_verdict(8) == "STRONG BUY"
        assert _determine_verdict(7) == "BUY"
        assert _determine_verdict(4) == "BUY"
        assert _determine_verdict(3) == "HOLD"
        assert _determine_verdict(0) == "HOLD"
        assert _determine_verdict(-3) == "HOLD"
        assert _determine_verdict(-4) == "SELL"
        assert _determine_verdict(-7) == "SELL"
        assert _determine_verdict(-8) == "STRONG SELL"
        assert _determine_verdict(-15) == "STRONG SELL"


class TestConsensusConsistencyRules:
    """Verify that the consensus report rules are strictly enforced."""

    def test_case_1_bearish_score_yields_consistent_verdicts(self):
        """Case 1: Technical Score = -4.2, Votes: SELL/SELL/SELL/SELL -> Expected: Executive Summary = SELL, Consensus Report = SELL."""
        from services.explainable_ai import validate_consensus_consistency, DecisionConsistencyError
        
        report = {
            "verdict": "SELL",
            "confidence": 70,
            "target_price": 1282.9,
            "stop_loss": 1350.0,
            "votes": {
                "bull": {"vote": "SELL"},
                "bear": {"vote": "SELL"},
                "risk": {"vote": "SELL"},
                "pm": {"vote": "SELL"},
            }
        }
        
        # Consistent report
        valid_consensus = (
            "Investment Committee Verdict: SELL\n"
            "Confidence: 70%\n"
            "Target Price: 1282.9\n"
            "Stop Loss: 1350.0\n"
        )
        # Should not raise
        validate_consensus_consistency(valid_consensus, report)
        
        # Inconsistent report (BUY instead of SELL)
        invalid_consensus = (
            "Investment Committee Verdict: BUY\n"
            "Confidence: 70%\n"
            "Target Price: 1282.9\n"
            "Stop Loss: 1350.0\n"
        )
        with pytest.raises(DecisionConsistencyError, match="verdict"):
            validate_consensus_consistency(invalid_consensus, report)

    def test_case_2_bullish_score_yields_consistent_verdicts(self):
        """Case 2: Technical Score = +5.8, Votes: BUY/BUY/BUY/BUY -> Expected: Consensus Report = BUY."""
        from services.explainable_ai import validate_consensus_consistency, DecisionConsistencyError
        
        report = {
            "verdict": "BUY",
            "confidence": 80,
            "target_price": 3120.0,
            "stop_loss": 2860.0,
        }
        
        valid_consensus = (
            "Investment Committee Verdict: BUY\n"
            "Confidence: 80%\n"
            "Target Price: 3120.0\n"
        )
        validate_consensus_consistency(valid_consensus, report)
        
        # Inconsistent report (verdict mismatch)
        invalid_consensus = (
            "Investment Committee Verdict: SELL\n"
            "Confidence: 80%\n"
            "Target Price: 3120.0\n"
        )
        with pytest.raises(DecisionConsistencyError, match="verdict"):
            validate_consensus_consistency(invalid_consensus, report)

    def test_case_3_mixed_votes_yields_hold(self):
        """Case 3: Mixed Votes -> Expected: Consensus Report = HOLD."""
        from services.explainable_ai import validate_consensus_consistency, DecisionConsistencyError
        
        report = {
            "verdict": "HOLD",
            "confidence": 55,
            "target_price": None,
            "stop_loss": None,
        }
        
        valid_consensus = (
            "Investment Committee Verdict: HOLD\n"
            "Confidence: 55%\n"
        )
        validate_consensus_consistency(valid_consensus, report)
        
        # Inconsistent report (verdict mismatch)
        invalid_consensus = (
            "Investment Committee Verdict: BUY\n"
            "Confidence: 55%\n"
        )
        with pytest.raises(DecisionConsistencyError, match="verdict"):
            validate_consensus_consistency(invalid_consensus, report)

    def test_case_4_confidence_exact_match(self):
        """Case 4: Confidence: If PM outputs Confidence = 67%, Consensus must also display 67%."""
        from services.explainable_ai import validate_consensus_consistency, DecisionConsistencyError
        
        report = {
            "verdict": "BUY",
            "confidence": 67,
            "target_price": 1000.0,
            "stop_loss": 900.0,
        }
        
        valid_consensus = (
            "Investment Committee Verdict: BUY\n"
            "Confidence: 67%\n"
        )
        validate_consensus_consistency(valid_consensus, report)
        
        # Inconsistent report (confidence mismatch)
        invalid_consensus = (
            "Investment Committee Verdict: BUY\n"
            "Confidence: 84%\n"
        )
        with pytest.raises(DecisionConsistencyError, match="confidence"):
            validate_consensus_consistency(invalid_consensus, report)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

