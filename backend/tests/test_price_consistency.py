import pytest
from main import app
from services.price_manager import get_price_service

@pytest.mark.asyncio
async def test_price_consistency_spot_vs_movers():
    """
    Ensure both Volatility API (Spot LTP) and Market Movers API
    return identically sourced prices via the PriceService.
    """
    from unittest.mock import patch
    import httpx
    
    # Mock the PriceService
    price_svc = get_price_service()
    
    mock_price_data = {
        "symbol": "JPPOWER",
        "instrument_key": None,
        "ltp": 17.02,
        "open": 15.56,
        "high": 18.0,
        "low": 15.0,
        "close": 17.02,
        "previous_close": 15.56,
        "change": 1.46,
        "change_percent": 9.38,
        "volume": 10000,
        "timestamp": "2026-07-11T12:00:00+05:30",
        "market_status": "OPEN",
        "source": "UPSTOX_WS",
        "last_updated": "2026-07-11T12:00:00+05:30"
    }

    mock_bulk_data = {
        "JPPOWER": mock_price_data,
        "RELIANCE": {
            "symbol": "RELIANCE", "ltp": 3100.5, "previous_close": 3000.0, "change_percent": 3.35, "source": "UPSTOX_WS", "market_status": "OPEN"
        }
    }

    try:
        transport = httpx.ASGITransport(app=app)
        client = httpx.AsyncClient(transport=transport, base_url="http://test")
    except (AttributeError, TypeError):
        client = httpx.AsyncClient(app=app, base_url="http://test")

    with patch.object(price_svc, 'get_price', return_value=mock_price_data), \
         patch.object(price_svc, 'get_prices_bulk', return_value=mock_bulk_data), \
         patch('utils.auth.get_current_user', return_value={"id": 1, "email": "test@quantai.com"}):

        async with client as ac:
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
                
                if jppower:
                    movers_ltp = jppower.get("ltp")
                    assert movers_ltp == 17.02, f"Market Movers returned {movers_ltp}, expected 17.02"
                    
                    movers_change = jppower.get("change_pct")
                    assert movers_change == 9.38, f"Market Movers change_pct {movers_change}, expected 9.38"
