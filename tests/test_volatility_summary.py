import pytest
from backend.api.volatility import generate_investor_summary

def test_strong_buy_volatility():
    summary = generate_investor_summary(
        iv=15.0,
        hv=20.0,
        iv_rank=20.0,
        iv_percentile=18.0,
        volatility_regime="Low Volatility",
        mean_reversion_score=35.0,
        price_change_pct=1.2,
        symbol="RELIANCE"
    )
    assert summary["action"] == "STRONG BUY"
    assert summary["risk_level"] == "Low"
    assert "options market expects lower future volatility" in summary["reasons"][0].lower()
    assert "cheap" in summary["reasons"][1].lower()

def test_buy_volatility():
    summary = generate_investor_summary(
        iv=22.0,
        hv=23.0,
        iv_rank=45.0,
        iv_percentile=52.0,
        volatility_regime="Normal Volatility",
        mean_reversion_score=50.0,
        price_change_pct=0.5,
        symbol="TCS"
    )
    assert summary["action"] == "BUY"
    assert summary["risk_level"] == "Moderate"

def test_hold_volatility():
    summary = generate_investor_summary(
        iv=24.0,
        hv=22.0,
        iv_rank=55.0,
        iv_percentile=60.0,
        volatility_regime="Normal Volatility",
        mean_reversion_score=50.0,
        price_change_pct=-2.0,
        symbol="INFY"
    )
    assert summary["action"] == "HOLD"

def test_sell_volatility():
    summary = generate_investor_summary(
        iv=45.0,
        hv=35.0,
        iv_rank=78.0,
        iv_percentile=80.0,
        volatility_regime="High Volatility",
        mean_reversion_score=85.0,
        price_change_pct=-3.5,
        symbol="SBIN"
    )
    assert summary["action"] == "SELL"
    assert summary["risk_level"] == "High"

def test_wait_volatility():
    summary = generate_investor_summary(
        iv=60.0,
        hv=40.0,
        iv_rank=92.0,
        iv_percentile=95.0,
        volatility_regime="High Volatility",
        mean_reversion_score=90.0,
        price_change_pct=1.5,
        symbol="HDFCBANK"
    )
    assert summary["action"] == "WAIT FOR BETTER ENTRY"
    assert summary["risk_level"] == "High"
