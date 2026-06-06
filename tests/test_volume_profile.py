import pytest
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

import pandas as pd
import numpy as np
import asyncio
from sqlalchemy import text
from database import AsyncSessionLocal
from api.volume_profile import calculate_volume_profile, get_volume_profile

class MockUser:
    id = 1
    email = "test@example.com"
    is_active = True

def test_volume_profile_calculations():
    # 1. Test calculation engine with synthetic D-shape (balanced) profile
    # Synthesize price data around 100
    dates = pd.date_range(start="2026-01-01", periods=100)
    data = []
    for i in range(100):
        # Balanced bell curve distribution around 100
        # We can construct price ranges that expand and then contract
        dev = abs(i - 50)
        low = 100.0 - (10 - dev * 0.1)
        high = 100.0 + (10 - dev * 0.1)
        close = 100.0 + (i % 2 - 0.5)
        open_val = 100.0 - (i % 2 - 0.5)
        # Higher volume in the middle (near 100)
        volume = max(1000, 10000 - dev * 180)
        data.append({
            "date": dates[i].date(),
            "open": open_val,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume
        })
    df = pd.DataFrame(data)
    
    profile = calculate_volume_profile(df, num_bins=50)
    
    assert "poc" in profile
    assert "vah" in profile
    assert "val" in profile
    assert "hvn" in profile
    assert "lvn" in profile
    assert "shape" in profile
    assert "histogram" in profile
    
    # Valuations should be sound
    assert profile["poc"] > 0
    assert profile["vah"] >= profile["poc"]
    assert profile["val"] <= profile["poc"]
    assert len(profile["histogram"]) == 50
    assert profile["shape"] in ["D Shape", "P Shape", "B Shape", "Double Distribution", "Trend Day"]

def test_live_volume_profile_endpoint():
    async def run_test():
        async with AsyncSessionLocal() as session:
            # Query RELIANCE, TCS, or any available stock symbol
            symbol_query = "SELECT symbol FROM instrument_master WHERE is_active = TRUE LIMIT 1"
            res = await session.execute(text(symbol_query))
            row = res.fetchone()
            if not row:
                print("No active symbols in DB. Skipping API endpoint test.")
                return
            
            symbol = row[0]
            print(f"Testing Volume Profile API for symbol: {symbol}")
            
            # Call API helper
            api_res = await get_volume_profile(symbol=symbol, lookback=90, current_user=MockUser(), db=session)
            
            assert api_res["status"] == "success"
            assert api_res["symbol"] == symbol.upper()
            assert "poc" in api_res
            assert "vah" in api_res
            assert "val" in api_res
            assert "hvn" in api_res
            assert "lvn" in api_res
            assert "shape" in api_res
            assert "action" in api_res
            assert "verdict" in api_res
            assert "confidence" in api_res
            assert "risk_score" in api_res
            assert "institutional_bias" in api_res
            assert "summary" in api_res
            assert "factors" in api_res
            assert "histogram" in api_res
            assert "price_history" in api_res
            assert "timeframes" in api_res
            assert "risk_management" in api_res
            assert "sector_integration" in api_res
            
            # Check structure within inner items
            risk = api_res["risk_management"]
            assert "entry_zone" in risk
            assert "stop_loss" in risk
            assert "target_1" in risk
            assert "target_2" in risk
            assert "risk_reward_ratio" in risk
            
            tfs = api_res["timeframes"]
            assert "daily" in tfs
            assert "weekly" in tfs
            assert "monthly" in tfs
            
            sec = api_res["sector_integration"]
            assert "sector_name" in sec
            assert "sector_score" in sec
            assert "sector_rank" in sec
            assert "relative_strength_rank" in sec
            
            print(f"Volume Profile API verification succeeded. Shape: {api_res['shape']}, Action: {api_res['action']}, Verdict: {api_res['verdict']}")
            
    asyncio.run(run_test())

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
