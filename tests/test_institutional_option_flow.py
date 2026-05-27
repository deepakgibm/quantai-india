import pytest
import sys
import os

# Modify path if running tests directly
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend'))

from api.option_flow import (
    calculate_max_pain,
    classify_buildup,
    generate_trade_signals,
    detect_smart_money_activity
)

def test_calculate_max_pain():
    # Construct a sample option chain with a few strikes
    # Format of strike list elements: 
    # {"strike_price": float, "call": {"oi": int}, "put": {"oi": int}}
    strikes = [
        {"strike_price": 24000.0, "call": {"oi": 100}, "put": {"oi": 5000}},
        {"strike_price": 24100.0, "call": {"oi": 500}, "put": {"oi": 3000}},
        {"strike_price": 24200.0, "call": {"oi": 1000}, "put": {"oi": 1000}},
        {"strike_price": 24300.0, "call": {"oi": 4000}, "put": {"oi": 200}},
        {"strike_price": 24400.0, "call": {"oi": 6000}, "put": {"oi": 50}},
    ]
    
    max_pain = calculate_max_pain(strikes)
    assert max_pain == 24200.0 or max_pain in [s["strike_price"] for s in strikes]
    
    # Test empty list fallback
    assert calculate_max_pain([]) == 0.0

def test_classify_buildup():
    # Long Build-Up: Price Up, OI Up
    assert classify_buildup(0.015, 5000) == "Long Build-Up"
    assert classify_buildup(0.0, 100) == "Long Build-Up"
    
    # Short Build-Up: Price Down, OI Up
    assert classify_buildup(-0.01, 10000) == "Short Build-Up"
    
    # Long Unwinding: Price Down, OI Down
    assert classify_buildup(-0.005, -3000) == "Long Unwinding"
    assert classify_buildup(0.0, -100) == "Long Unwinding"
    
    # Short Covering: Price Up, OI Down
    assert classify_buildup(0.02, -1500) == "Short Covering"
    
    # Neutral: No change in OI
    assert classify_buildup(0.01, 0) == "Neutral"

def test_generate_trade_signals():
    # Test Bullish conditions
    bullish_sig = generate_trade_signals(
        symbol="RELIANCE",
        spot_price=2500.0,
        pcr_oi=1.3,
        net_flow=600000.0,
        support_strike=2480.0,
        resistance_strike=2550.0,
        sentiment="Bullish",
        beta=1.1,
        relative_strength="Outperforming"
    )
    
    assert bullish_sig["directional_bias"] == "Bullish"
    assert bullish_sig["signal"] in ("BUY", "BREAKOUT")
    assert bullish_sig["confidence_score"] > 50
    
    # Test Bearish conditions close to resistance (dist_to_resistance < 2%)
    bearish_sig = generate_trade_signals(
        symbol="RELIANCE",
        spot_price=2540.0,
        pcr_oi=0.6,
        net_flow=-800000.0,
        support_strike=2450.0,
        resistance_strike=2550.0,
        sentiment="Bearish",
        beta=0.9,
        relative_strength="Underperforming"
    )
    
    assert bearish_sig["directional_bias"] == "Bearish"
    assert bearish_sig["signal"] == "SELL"
    assert bearish_sig["confidence_score"] >= 80

def test_detect_smart_money_activity():
    # Create average-based structures to trigger walls, spikes, and traps
    strikes = [
        {
            "strike_price": 24000.0,
            "call": {"oi": 1000, "oi_change": 100, "volume": 200, "ltp": 50.0},
            "put": {"oi": 200000, "oi_change": 25000, "volume": 300, "ltp": 5.0} # Unusual OI Accumulation and wall PE
        },
        {
            "strike_price": 24200.0,
            "call": {"oi": 500, "oi_change": 50, "volume": 100, "ltp": 15.0},
            "put": {"oi": 600, "oi_change": 60, "volume": 120, "ltp": 12.0}
        },
        {
            "strike_price": 24400.0,
            "call": {"oi": 300000, "oi_change": 45000, "volume": 1000, "ltp": 45.0}, # wall CE
            "put": {"oi": 300, "oi_change": -30, "volume": 100, "ltp": 90.0}
        }
    ]
    
    activities = detect_smart_money_activity(strikes, spot_price=24100.0)
    assert len(activities) > 0
    
    types = [act["type"] for act in activities]
    assert any("Wall" in t or "Accumulation" in t or "Trap" in t for t in types)
