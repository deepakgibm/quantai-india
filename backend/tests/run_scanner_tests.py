import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import text

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from database import SessionLocal
from services.institutional_scanner_service import get_institutional_scanner_service

def get_dummy_data():
    np.random.seed(42)
    dates = [datetime.utcnow() - timedelta(days=i) for i in range(150, -1, -1)]
    prices = []
    base_price = 1000.0
    for idx in range(len(dates)):
        if idx < 50:
            wave = np.sin(idx / 8.0) * 100.0
            price = base_price + wave
        elif idx < 100:
            wave = np.sin(idx / 6.0) * 35.0
            price = base_price + 20.0 + wave
        else:
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

def test_minervini():
    service = get_institutional_scanner_service()
    df = get_dummy_data()
    df['close'] = [500 + i * 5.0 for i in range(len(df))]
    df['high'] = df['close'] + 2
    df['low'] = df['close'] - 2
    res = service._detect_trend_template(df)
    assert res["conditions"]["price_above_sma50"] is True
    assert res["conditions"]["price_above_sma150"] is True
    assert res["conditions"]["price_above_sma200"] is True
    assert res["conditions"]["sma50_above_sma150"] is True
    assert res["conditions"]["sma150_above_sma200"] is True
    print("✅ test_minervini passed!")

def test_vcp():
    service = get_institutional_scanner_service()
    df = get_dummy_data()
    vcp_res = service._detect_vcp(df, rs_score=85.0)
    assert vcp_res["num_contractions"] >= 2
    print(f"✅ test_vcp passed! Num Contractions: {vcp_res['num_contractions']}, Score: {vcp_res['score']:.1f}, Category: {vcp_res['category']}")


def test_rs():
    service = get_institutional_scanner_service()
    df = get_dummy_data()
    closes = [100.0]
    for i in range(1, len(df)):
        if i % 22 == 0:
            closes.append(closes[-1] * 2.0)
        else:
            closes.append(closes[-1] * 1.01)
    df['close'] = closes[:len(df)]
    rs_res = service._detect_relative_strength(df)
    r1 = rs_res["r1m"]
    r3 = rs_res["r3m"]
    r6 = rs_res["r6m"]
    expected_score = (0.4 * r6) + (0.3 * r3) + (0.3 * r1)
    assert abs(rs_res["rs_score"] - expected_score) < 1e-4
    print("✅ test_rs passed!")

def test_db():
    db = SessionLocal()
    try:
        columns_res = db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'vcp_scores'")).fetchall()
        column_names = [col[0] for col in columns_res]
        assert "symbol" in column_names
        assert "vcp_score" in column_names
        assert "created_at" in column_names
        print("✅ test_db schema verified!")
    finally:
        db.close()

if __name__ == "__main__":
    test_minervini()
    test_vcp()
    test_rs()
    test_db()
    print("🎉 All Institutional Scanner Tests Passed Successfully!")
