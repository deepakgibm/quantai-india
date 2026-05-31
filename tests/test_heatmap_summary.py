import pytest
import pandas as pd
import requests
from backend.api.heatmap import generate_market_summary

def test_generate_market_summary_empty():
    summary = generate_market_summary(
        df=pd.DataFrame(),
        active_metric="performance",
        sectors_list=[]
    )
    assert summary["signal"] == "HOLD"
    assert summary["confidence"] == 50
    assert summary["sentiment"] == "Neutral"
    assert "No market data available" in summary["summary"]

def test_generate_market_summary_buy():
    # 72% green, positive momentum, stable volatility, high delivery
    df = pd.DataFrame([
        {"change_pct": 1.5, "momentum_pct": 2.5, "rs_score": 1.0, "delivery_pct": 65.0, "volatility_score": 1.0},
        {"change_pct": 2.0, "momentum_pct": 3.0, "rs_score": 1.5, "delivery_pct": 70.0, "volatility_score": 1.2},
        {"change_pct": -0.5, "momentum_pct": 0.5, "rs_score": -1.0, "delivery_pct": 55.0, "volatility_score": 1.5},
        {"change_pct": 1.2, "momentum_pct": 1.8, "rs_score": 0.8, "delivery_pct": 60.0, "volatility_score": 0.8},
    ])
    sectors_list = [
        {"name": "Financial Services", "avg_value": 1.5, "total_market_cap": 1000},
        {"name": "IT", "avg_value": 0.2, "total_market_cap": 800},
    ]
    summary = generate_market_summary(df, "performance", sectors_list)
    assert summary["signal"] in ["BUY", "HOLD"]
    assert summary["confidence"] >= 50
    assert "Financial Services" in summary["top_sectors"]
    assert "IT" in summary["weak_sectors"]

def test_generate_market_summary_sell():
    # Mostly red, negative momentum, high volatility, low delivery
    df = pd.DataFrame([
        {"change_pct": -2.5, "momentum_pct": -3.5, "rs_score": -1.0, "delivery_pct": 35.0, "volatility_score": 4.5},
        {"change_pct": -1.8, "momentum_pct": -2.0, "rs_score": -0.5, "delivery_pct": 38.0, "volatility_score": 3.8},
        {"change_pct": 0.5, "momentum_pct": -1.0, "rs_score": 1.0, "delivery_pct": 42.0, "volatility_score": 2.5},
        {"change_pct": -3.2, "momentum_pct": -4.0, "rs_score": -2.0, "delivery_pct": 32.0, "volatility_score": 5.0},
    ])
    sectors_list = [
        {"name": "Financial Services", "avg_value": -2.5, "total_market_cap": 1000},
        {"name": "IT", "avg_value": 0.5, "total_market_cap": 800},
    ]
    summary = generate_market_summary(df, "performance", sectors_list)
    assert summary["signal"] == "SELL"
    assert "IT" in summary["top_sectors"]
    assert "Financial Services" in summary["weak_sectors"]

def test_live_api_heatmap_summary():
    # Attempt to log in and fetch heatmap data
    base_url = "http://localhost:8000"
    session = requests.Session()
    login_response = session.post(
        f"{base_url}/api/auth/login",
        json={"email": "dthat53@gmail.com", "password": "admin1243"},
        timeout=10,
    )
    if login_response.status_code != 200:
        pytest.skip("Live server auth failed or server offline")
        
    token = login_response.json().get("access_token")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    # Test for each mode
    for mode in ["performance", "volatility", "momentum", "delivery", "relative_strength"]:
        r = session.get(f"{base_url}/api/heatmap?mode={mode}", headers=headers, timeout=10)
        assert r.status_code == 200, f"API failed for mode {mode}: {r.text}"
        data = r.json()
        assert data.get("status") == "success"
        assert "market_summary" in data
        summary = data["market_summary"]
        for field in ["signal", "confidence", "sentiment", "top_sectors", "weak_sectors", "summary", "actionable_insight", "score", "reasoning"]:
            assert field in summary, f"Missing field {field} in summary for mode {mode}"
        
        # Verify signal type
        assert summary["signal"] in ["BUY", "HOLD", "SELL"]
        assert isinstance(summary["confidence"], int)
        assert isinstance(summary["score"], (int, float))
        print(f"Mode {mode} summary: {summary['signal']} (Conf: {summary['confidence']}%) - {summary['summary'][:60]}...")
