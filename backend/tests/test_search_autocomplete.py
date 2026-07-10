"""
Unit and Integration Tests for backend Search Autocomplete.
"""
import sys
import os
import pytest
import httpx

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import app
from database import AsyncSessionLocal

@pytest.mark.asyncio
async def test_search_autocomplete_all():
    """Verify in-memory preloading and API suggestions in a single test case to prevent event loop teardown conflicts."""
    
    # 1. Verify in-memory loading directly
    from api.search import ensure_stocks_loaded
    async with AsyncSessionLocal() as session:
        stocks = await ensure_stocks_loaded(session)
        assert isinstance(stocks, list)
        assert len(stocks) > 0
        
        # Verify schema
        sample = stocks[0]
        assert "symbol" in sample
        assert "company_name" in sample
        assert "sector" in sample
        assert "exchange" in sample
        assert "index" in sample

    # 2. Verify API endpoint via AsyncClient
    try:
        transport = httpx.ASGITransport(app=app)
        client = httpx.AsyncClient(transport=transport, base_url="http://test")
    except (AttributeError, TypeError):
        client = httpx.AsyncClient(app=app, base_url="http://test")
        
    async with client:
        # Login to get token
        login_resp = await client.post(
            "/api/auth/login",
            json={"email": "test@quantai.com", "password": "test123"}
        )
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Search for 'TATA'
        resp = await client.get("/api/search/stocks?q=tata", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert "count" in data
        assert data["count"] > 0
        
        # Verify fields
        res = data["results"][0]
        assert "symbol" in res
        assert "company_name" in res
        assert "sector" in res
        
        # Search for 'TCS' (Exact symbol match first)
        resp_tcs = await client.get("/api/search/stocks?q=tcs", headers=headers)
        assert resp_tcs.status_code == 200
        assert resp_tcs.json()["results"][0]["symbol"] == "TCS"
