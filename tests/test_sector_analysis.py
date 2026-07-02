import pytest
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from database import AsyncSessionLocal
from api.sector_analysis import get_sector_analysis

class MockUser:
    id = 1
    email = "test@example.com"
    is_active = True

import asyncio

@pytest.mark.asyncio
async def test_sector_analysis_calculations():
    async with AsyncSessionLocal() as session:
        res = await get_sector_analysis(current_user=MockUser(), db=session)
        
    # Structure validations
    assert res["status"] == "success"
    assert "summary" in res
    assert "sectors" in res
    assert "stocks" in res
    
    # Summary validations
    summary = res["summary"]
    assert "total_sectors" in summary
    assert "best_sector_1m" in summary
    assert "worst_sector_1m" in summary
    assert "strongest_momentum_sector" in summary
    assert "highest_participation_sector" in summary
    assert "most_attractive_valuation_sector" in summary
    
    # Sectors validations
    if len(res["sectors"]) > 0:
        first_sec = res["sectors"][0]
        assert "sector" in first_sec
        assert "stock_count" in first_sec
        assert "avg_return_1d" in first_sec
        assert "avg_return_1m" in first_sec
        assert "avg_rsi" in first_sec
        assert "avg_pe" in first_sec
        assert "pct_above_20_dma" in first_sec
        assert "pct_above_50_dma" in first_sec
        assert "pct_above_200_dma" in first_sec
        assert "market_cap_contribution" in first_sec
        assert "trend" in first_sec
        assert "valuation_rating" in first_sec
        assert "gainers" in first_sec
        assert "losers" in first_sec
        
        # Stock list validation
        assert len(res["stocks"]) > 0
        first_stock = res["stocks"][0]
        assert "symbol" in first_stock
        assert "price" in first_stock
        assert "rsi" in first_stock
        assert "pe_ratio" in first_stock
        assert "pb_ratio" in first_stock
        assert "above_50_dma" in first_stock
        assert "rating" in first_stock
        
        print(f"\nSector Analysis Test PASSED. Total Sectors: {len(res['sectors'])}. Total Stocks: {len(res['stocks'])}")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
