import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import text

from database import SessionLocal
from services.institutional_scanner_service import get_institutional_scanner_service
from models_institutional_scanner import VcpScore, TrendTemplateScore, RelativeStrengthRanking

@pytest.fixture
def dummy_candle_data():
    """Generate mock price candles simulating a Volatility Contraction Pattern (VCP)."""
    np.random.seed(42)
    dates = [datetime.utcnow() - timedelta(days=i) for i in range(150, -1, -1)]
    
    # Simulate a price series forming VCP:
    # Starts around 1000, swing high to 1100, down to 900 (contraction 1: 18%)
    # Swing high to 1050, down to 980 (contraction 2: 6.6%)
    # Swing high to 1030, down to 1010 (contraction 3: 2%)
    # Moving averages trending upwards
    prices = []
    base_price = 1000.0
    
    for idx in range(len(dates)):
        # Construct VCP contractions mathematically
        if idx < 50:
            # First wave (troughs around 900, peaks around 1100)
            wave = np.sin(idx / 8.0) * 100.0
            price = base_price + wave
        elif idx < 100:
            # Second wave (troughs around 970, peaks around 1040)
            wave = np.sin(idx / 6.0) * 35.0
            price = base_price + 20.0 + wave
        else:
            # Third wave (troughs around 1005, peaks 1025)
            wave = np.sin(idx / 4.0) * 10.0
            price = base_price + 15.0 + wave
            
        prices.append(price)
        
    df = pd.DataFrame({
        "timestamp": dates,
        "open": prices,
        "high": [p + 2.0 for p in prices],
        "low": [p - 2.0 for p in prices],
        "close": [p + 0.5 for p in prices],
        "volume": np.random.randint(10000, 50000, len(dates))
    })
    return df

def test_minervini_trend_template_math(dummy_candle_data):
    """Verify that Minervini Trend Template conditions match expectations."""
    service = get_institutional_scanner_service()
    
    # 1. Modify dummy data to guarantee MA crossover (Bullish trend)
    df = dummy_candle_data.copy()
    # Ensure strong upward trend: prices steadily rising
    df['close'] = [500 + i * 5.0 for i in range(len(df))]
    df['high'] = df['close'] + 2
    df['low'] = df['close'] - 2
    
    res = service._detect_trend_template(df)
    
    assert "score" in res
    assert "conditions" in res
    assert "price_above_sma50" in res["conditions"]
    assert "price_above_sma150" in res["conditions"]
    assert "price_above_sma200" in res["conditions"]
    
    # Since prices are strictly rising, the moving averages will be aligned: SMA50 > SMA150 > SMA200
    assert res["conditions"]["price_above_sma50"] is True
    assert res["conditions"]["price_above_sma150"] is True
    assert res["conditions"]["price_above_sma200"] is True
    assert res["conditions"]["sma50_above_sma150"] is True
    assert res["conditions"]["sma150_above_sma200"] is True

def test_vcp_compression_algorithm(dummy_candle_data):
    """Verify the contraction finding and VCP Quality Scoring engine."""
    service = get_institutional_scanner_service()
    
    # Force contraction heights and lows
    df = dummy_candle_data.copy()
    
    # Run VCP screening
    vcp_res = service._detect_vcp(df, rs_score=85.0)
    
    assert "is_vcp" in vcp_res
    assert "score" in vcp_res
    assert "num_contractions" in vcp_res
    assert "breakout_ready" in vcp_res
    assert "category" in vcp_res
    assert vcp_res["num_contractions"] >= 2
    assert vcp_res["score"] >= 60.0 # VCP mock pattern should rank as active

def test_relative_strength_weighted_formula(dummy_candle_data):
    """Confirm the Weighted Relative Strength score uses correct coefficients."""
    service = get_institutional_scanner_service()
    df = dummy_candle_data.copy()
    
    # We will set prices to double every month (21 days) to test calculations
    closes = [100.0]
    for i in range(1, len(df)):
        if i % 22 == 0:
            closes.append(closes[-1] * 2.0) # Double price
        else:
            closes.append(closes[-1] * 1.01)
            
    df['close'] = closes[:len(df)]
    
    rs_res = service._detect_relative_strength(df)
    
    # Extract returns
    r1 = rs_res["r1m"]
    r3 = rs_res["r3m"]
    r6 = rs_res["r6m"]
    expected_score = (0.4 * r6) + (0.3 * r3) + (0.3 * r1)
    
    assert abs(rs_res["rs_score"] - expected_score) < 1e-4

def test_database_table_schemas():
    """Verify that all postgres scanner tables are present with audit metadata."""
    db = SessionLocal()
    try:
        # Check vcp_scores columns
        columns_res = db.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'vcp_scores'
        """)).fetchall()
        
        column_names = [col[0] for col in columns_res]
        
        assert "symbol" in column_names
        assert "vcp_score" in column_names
        assert "breakout_ready" in column_names
        assert "created_at" in column_names
        assert "updated_at" in column_names
        
        # Check relative_strength_rankings columns
        rs_columns = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'relative_strength_rankings'
        """)).fetchall()
        
        rs_names = [col[0] for col in rs_columns]
        assert "rank" in rs_names
        assert "rs_score" in rs_names
        assert "sector_rank" in rs_names
        assert "industry_rank" in rs_names
    finally:
        db.close()
