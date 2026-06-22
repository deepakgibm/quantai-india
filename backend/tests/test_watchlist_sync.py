import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from services.watchlist_service import WatchlistService
from services.upstox_client import UpstoxClient
from models import WatchlistItem
from datetime import datetime

@pytest.mark.asyncio
async def test_get_watchlist_upstox_timeout_fallback():
    # Setup mock items
    mock_item = WatchlistItem(
        id=1, user_id=1, symbol="RELIANCE", company_name="Reliance",
        added_at=datetime.utcnow(), watchlist_price=2500.0, current_price=2550.0,
        change_percent=2.0, change_amount=50.0
    )
    
    mock_db = AsyncMock()
    
    # Mock Repository
    with patch('repositories.watchlist_repository.WatchlistRepository.get_all_by_user', new_callable=AsyncMock) as mock_get_all:
        with patch('repositories.watchlist_repository.WatchlistRepository.get_instrument_keys_map', new_callable=AsyncMock) as mock_get_keys:
            mock_get_all.return_value = [mock_item]
            mock_get_keys.return_value = {"RELIANCE": "NSE_EQ|INE002A01018"}
            
            # Mock UpstoxPriceResolver to throw timeout
            with patch('services.upstox_price_resolver.UpstoxPriceResolver.get_prices_bulk', new_callable=AsyncMock) as mock_bulk_prices:
                mock_bulk_prices.side_effect = Exception("Connection Timeout")
                
                # Should NOT raise an exception, but return the mock_item with old prices
                items = await WatchlistService.get_watchlist(mock_db, 1)
                
                assert len(items) == 1
                assert items[0].symbol == "RELIANCE"
                # Assert it swallowed the exception gracefully
                assert mock_bulk_prices.call_count == 1

@pytest.mark.asyncio
async def test_upstox_client_401_token_refresh_attempt():
    # Test that HTTP 401 triggers token refresh
    client = UpstoxClient(access_token="expired_token")
    
    # Create a mock response
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    
    with patch.object(client, 'refresh_access_token', new_callable=AsyncMock) as mock_refresh:
        mock_refresh.return_value = False # Simulate refresh failure
        
        with patch('httpx.AsyncClient.request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = httpx.HTTPStatusError("Unauthorized", request=MagicMock(), response=mock_response)
            
            with pytest.raises(httpx.HTTPStatusError):
                await client._make_request("GET", "/test")
                
            # It should have attempted to refresh token once
            assert mock_refresh.call_count == 1
