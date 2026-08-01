import pytest
import httpx
import json
import os
import asyncio
from datetime import datetime
from unittest.mock import patch, MagicMock
from main import app
from services.price_manager.price_cache import get_price_cache
from services.instrument_resolver import resolve_instrument_info
from services.upstox_client import get_upstox_client
from utils.auth import get_current_user

@pytest.fixture
def client():
    try:
        transport = httpx.ASGITransport(app=app)
        return httpx.AsyncClient(transport=transport, base_url="http://test")
    except (AttributeError, TypeError):
        return httpx.AsyncClient(app=app, base_url="http://test")

@pytest.mark.asyncio
async def test_live_price_and_ohlc_validation(client):
    symbols = ["RELIANCE", "TCS", "INFY"]
    
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.email = "test@quantai.com"
    mock_user.is_upstox_connected = True
    
    upstox_client = get_upstox_client()
    has_token = upstox_client.access_token is not None and len(upstox_client.access_token) > 10
    
    if not has_token:
        pytest.skip("No valid UPSTOX_ACCESS_TOKEN found in environment; skipping live validation.")

    cache = get_price_cache()
    for s in symbols:
        cache.clear(s)

    report_results = []
    has_mismatch = False

    # Apply auth overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user

    # Open the client instance ONCE for all requests
    async with client as ac:
        
        async def validate_symbol(symbol):
            nonlocal has_mismatch
            info = resolve_instrument_info(symbol)
            if not info or not info.instrument_key:
                return
            
            # Execute both requests simultaneously
            async def fetch_backend():
                return await ac.get(f"/api/upstox/market-quote/{symbol}")
                
            async def fetch_upstox():
                return await upstox_client.get_live_quote(info.instrument_key, symbol)

            backend_res, upstox_data = await asyncio.gather(fetch_backend(), fetch_upstox())
            
            if backend_res.status_code != 200:
                raise AssertionError(f"Backend API failed for {symbol}: status {backend_res.status_code}")
            
            if not upstox_data:
                pytest.skip(f"Upstox live API returned empty quote for {symbol} (rate limits or offline); skipping.")

            backend_data = backend_res.json()
            symbol_key = f"NSE_EQ:{symbol.upper()}"
            
            if symbol_key not in backend_data.get("data", {}):
                raise AssertionError(f"Symbol key {symbol_key} missing in backend response: {backend_data}")

            b_quote = backend_data["data"][symbol_key]
            
            b_ltp = float(b_quote.get("last_price") or 0.0)
            b_close = float(b_quote.get("close_price") or 0.0)
            b_prev_close = float(b_quote.get("previous_close") or 0.0)
            b_vol = int(b_quote.get("volume") or 0)
            
            u_ltp = float(upstox_data.get("last_price") or 0.0)
            u_ohlc = upstox_data.get("ohlc", {})
            u_close = float(u_ohlc.get("close") or 0.0)
            u_prev_close = float(upstox_data.get("previous_close") or 0.0)
            u_vol = int(upstox_data.get("volume") or 0)
            
            ltp_diff = abs(b_ltp - u_ltp)
            ltp_pct_diff = (ltp_diff / u_ltp * 100) if u_ltp > 0 else 0
            
            # Strict tolerance check (LTP difference <= ₹0.01 OR percentage diff <= 0.01%)
            passed = ltp_diff <= 0.01 or ltp_pct_diff <= 0.01
            
            reason = None
            if not passed:
                has_mismatch = True
                reason = "LTP mismatch. Cache might be stale or timezone transformation error."
                
            report_results.append({
                "symbol": symbol,
                "backend": {
                    "ltp": b_ltp,
                    "close": b_close,
                    "previous_close": b_prev_close,
                    "volume": b_vol
                },
                "reference_upstox": {
                    "ltp": u_ltp,
                    "close": u_close,
                    "previous_close": u_prev_close,
                    "volume": u_vol
                },
                "metrics": {
                    "ltp_diff": round(ltp_diff, 4),
                    "ltp_pct_diff": round(ltp_pct_diff, 4)
                },
                "passed": passed,
                "possible_reason": reason
            })

        # Run validation for all symbols
        await asyncio.gather(*(validate_symbol(s) for s in symbols))

    # Clear dependency overrides
    app.dependency_overrides.clear()

    # Write report
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_validated": len(symbols),
            "passed": sum(1 for r in report_results if r["passed"]),
            "failed": sum(1 for r in report_results if not r["passed"])
        },
        "results": report_results
    }
    
    reports_dir = "tests/reports"
    os.makedirs(reports_dir, exist_ok=True)
    report_path = os.path.join(reports_dir, "live_price_validation_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    if has_mismatch:
        raise AssertionError(f"Live Price validation failed. Mismatch report written to {report_path}")
