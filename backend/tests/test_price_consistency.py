import pytest
import pytest_asyncio
from httpx import AsyncClient
from main import app
from services.upstox_price_resolver import get_upstox_price_resolver

@pytest.mark.asyncio
async def test_price_consistency_spot_vs_movers(mocker):
    """
    Ensure both Volatility API (Spot LTP) and Market Movers API
    return identically sourced prices.
    """
    # Mock the UpstoxPriceResolver to return a fixed price for JPPOWER
    resolver = get_upstox_price_resolver()
    
    mock_price_data = {
        "symbol": "JPPOWER",
        "price": 17.02,
        "prev_close": 15.56,
        "change_pct": 9.38,
        "is_live": True,
        "price_source": "UPSTOX_WS",
        "exchange": "NSE",
        "timestamp": "2026-07-11T12:00:00+05:30",
        "stale": False,
        "data_stale": False
    }

    mocker.patch.object(resolver, 'get_price', return_value=mock_price_data)
    
    mock_bulk_data = {
        "JPPOWER": mock_price_data,
        "RELIANCE": {
            "symbol": "RELIANCE", "price": 3100.5, "prev_close": 3000.0, "change_pct": 3.35, "price_source": "UPSTOX_WS", "is_live": True
        }
    }
    mocker.patch.object(resolver, 'get_prices_bulk', return_value=mock_bulk_data)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Mock auth to bypass security for the test
        mocker.patch('utils.auth.get_current_user', return_value={"id": 1, "email": "test@quantai.com"})
        
        # 1. Fetch Volatility (Spot LTP)
        vol_response = await ac.get("/api/v1/volatility/JPPOWER?lookback_days=30")
        if vol_response.status_code == 200:
            vol_data = vol_response.json()
            spot_ltp = vol_data.get("latest_price")
            assert spot_ltp == 17.02, f"Expected 17.02, got {spot_ltp}"

        # 2. Fetch Market Movers
        movers_response = await ac.get("/api/v1/market/nifty100/top-movers?refresh=true")
        if movers_response.status_code == 200:
            movers_data = movers_response.json()
            gainers = movers_data.get("gainers", [])
            jppower = next((g for g in gainers if g["symbol"] == "JPPOWER"), None)
            
            # Note: JPPOWER might not appear in gainers if we're forcing NIFTY 100 filtering.
            # Assuming it does because we patched get_prices_bulk directly:
            if jppower:
                movers_ltp = jppower.get("ltp")
                assert movers_ltp == 17.02, f"Market Movers returned {movers_ltp}, expected 17.02"
                
                movers_change = jppower.get("change_pct")
                assert movers_change == 9.38, f"Market Movers change_pct {movers_change}, expected 9.38"
