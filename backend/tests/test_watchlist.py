import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
from database import AsyncSessionLocal
from models import WatchlistItem, User
from schemas import WatchlistItemCreate
from services.watchlist_service import WatchlistService
from sqlalchemy import text

@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.mark.anyio
async def test_watchlist_complete_flow():
    """
    Test the complete watchlist management lifecycle:
    1. Addition with mock quote resolution.
    2. Batch quote updates and returns calculations.
    3. Performance and analytics calculations.
    4. Deletion and cleanup.
    """
    db = AsyncSessionLocal()
    
    # 1. Resolve/Create a valid user for foreign key constraint compliance
    res = await db.execute(text("SELECT id FROM users LIMIT 1"))
    row = res.fetchone()
    
    if row:
        user_id = row[0]
        created_user = False
    else:
        # Create a temp user
        await db.execute(text(
            "INSERT INTO users (email, username, hashed_password, full_name, is_active) "
            "VALUES ('test_watchlist@example.com', 'test_watchlist', 'hashed', 'Test Watchlist User', true)"
        ))
        await db.commit()
        res = await db.execute(text("SELECT id FROM users WHERE username = 'test_watchlist'"))
        user_id = res.fetchone()[0]
        created_user = True

    # Ensure clean state for this symbol before test
    test_symbol = "TCS"
    await db.execute(
        text("DELETE FROM watchlist WHERE user_id = :uid AND symbol = :sym"),
        {"uid": user_id, "sym": test_symbol}
    )
    await db.commit()

    try:
        # 2. Test addition with live quote fallback (mocked)
        mock_quote = {
            "last_price": 3200.0,
            "previous_close": 3150.0,
            "net_change": 50.0,
            "change_percent": 1.58,
            "volume": 100000
        }
        
        with patch('services.upstox_client.UpstoxClient.get_live_quote', new_callable=AsyncMock) as mock_get_quote:
            mock_get_quote.return_value = mock_quote
            
            item_in = WatchlistItemCreate(symbol=test_symbol, exchange="NSE")
            item = await WatchlistService.add_to_watchlist(db, user_id, item_in)
            
            assert item is not None
            assert item.symbol == test_symbol
            assert item.watchlist_price == 3200.0
            assert item.current_price == 3200.0

        # 3. Test get_watchlist and batch live quotes update
        async def mock_quotes_side_effect(keys):
            return {
                key: {
                    "last_price": 3520.0,  # 10% gain
                    "previous_close": 3200.0,
                    "net_change": 320.0,
                    "change_percent": 10.0,
                    "volume": 200000
                }
                for key in keys
            }
        
        with patch('services.upstox_client.UpstoxClient.get_live_quotes', new_callable=AsyncMock) as mock_batch_quotes:
            mock_batch_quotes.side_effect = mock_quotes_side_effect
            
            watchlist = await WatchlistService.get_watchlist(db, user_id)
            assert len(watchlist) > 0
            
            tcs_item = next(item for item in watchlist if item.symbol == test_symbol)
            assert tcs_item.current_price == 3520.0
            assert tcs_item.change_percent == 10.0
            assert tcs_item.change_amount == 320.0

        # 4. Test performance metrics calculation
        perf = await WatchlistService.get_watchlist_performance(db, user_id, virtual_investment=10000.0)
        assert perf["total_invested"] > 0
        assert perf["total_value"] > perf["total_invested"]
        assert perf["total_pnl"] > 0
        assert perf["pnl_percent"] == 10.0
        assert perf["accuracy_percent"] == 100.0

        # 5. Test remove from watchlist
        deleted = await WatchlistService.remove_from_watchlist(db, user_id, test_symbol)
        assert deleted is True
        
        watchlist_post = await WatchlistService.get_watchlist(db, user_id)
        assert not any(item.symbol == test_symbol for item in watchlist_post)

    finally:
        # Cleanup watchlist items just in case
        await db.execute(
            text("DELETE FROM watchlist WHERE user_id = :uid AND symbol = :sym"),
            {"uid": user_id, "sym": test_symbol}
        )
        # Cleanup temp user if we created one
        if created_user:
            await db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": user_id})
            
        await db.commit()
        await db.close()

@pytest.mark.anyio
async def test_historical_price_fallback_recovery():
    """
    Test fallback EOD close price recovery from Upstox historical daily candles.
    """
    import pandas as pd
    
    mock_df = pd.DataFrame([
        {"timestamp": datetime.utcnow() - timedelta(days=2), "close": 150.0},
        {"timestamp": datetime.utcnow() - timedelta(days=1), "close": 155.0},
        {"timestamp": datetime.utcnow(), "close": 157.0}
    ])
    
    with patch('services.upstox_client.UpstoxClient.get_historical_data', new_callable=AsyncMock) as mock_hist:
        mock_hist.return_value = mock_df
        
        price = await WatchlistService.get_historical_price_closest_to(
            "NSE_EQ|DUMMY", "DUMMY", datetime.utcnow()
        )
        
        assert price == 157.0
