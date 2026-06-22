import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timedelta
from database import AsyncSessionLocal
from schemas import WatchlistItemCreate
from services.watchlist_service import WatchlistService
from sqlalchemy import text

@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture(autouse=True)
async def cleanup_db_engines():
    yield
    from database import engine, read_engine
    await engine.dispose()
    await read_engine.dispose()


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
    
    # 1. Create a dedicated temp user for this test to ensure clean state
    email_unique = f"test_wl_{int(datetime.utcnow().timestamp())}@example.com"
    username_unique = f"test_wl_{int(datetime.utcnow().timestamp())}"
    await db.execute(text(
        "INSERT INTO users (email, username, hashed_password, full_name, is_active) "
        "VALUES (:email, :username, 'hashed', 'Test Watchlist User', true)"
    ), {"email": email_unique, "username": username_unique})
    await db.commit()
    res = await db.execute(text("SELECT id FROM users WHERE username = :username"), {"username": username_unique})
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
        
        with patch('services.upstox_price_resolver.UpstoxPriceResolver.get_price', new_callable=AsyncMock) as mock_get_price:
            mock_get_price.return_value = {
                "symbol": test_symbol,
                "price": 3200.0,
                "prev_close": 3150.0,
                "change_pct": 1.58,
                "is_live": True,
                "price_source": "WS",
                "exchange": "NSE",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            item_in = WatchlistItemCreate(symbol=test_symbol, exchange="NSE")
            item = await WatchlistService.add_to_watchlist(db, user_id, item_in)
            
            assert item is not None
            assert item.symbol == test_symbol
            assert item.watchlist_price == 3200.0
            assert item.current_price == 3200.0

        # 3. Test get_watchlist and batch live quotes update
        async def mock_resolver_bulk_side_effect(symbols):
            return {
                sym: {
                    "symbol": sym,
                    "price": 3520.0,  # 10% gain
                    "prev_close": 3200.0,
                    "change_pct": 10.0,
                    "is_live": True,
                    "price_source": "WS",
                    "exchange": "NSE",
                    "timestamp": datetime.utcnow().isoformat()
                }
                for sym in symbols
            }
        
        with patch('services.upstox_price_resolver.UpstoxPriceResolver.get_prices_bulk', new_callable=AsyncMock) as mock_bulk_prices:
            mock_bulk_prices.side_effect = mock_resolver_bulk_side_effect
            
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
    Test fallback EOD close price recovery from local database daily candles.
    """
    db = AsyncSessionLocal()
    
    # Ensure clean state for test dummy symbol
    test_symbol = "DUMMY"
    await db.execute(text("DELETE FROM stock_candle WHERE instrument_id IN (SELECT instrument_id FROM instrument_master WHERE symbol = :sym)"), {"sym": test_symbol})
    await db.execute(text("DELETE FROM instrument_master WHERE symbol = :sym"), {"sym": test_symbol})
    await db.commit()
    
    instrument_id = None
    try:
        # 1. Insert test instrument master
        await db.execute(text(
            "INSERT INTO instrument_master (instrument_key, symbol, series, exchange, company_name, sector, isin_code, is_active) "
            "VALUES ('NSE_EQ|DUMMY', 'DUMMY', 'EQ', 'NSE', 'Dummy Company', 'Others', 'INE000000000', true)"
        ))
        await db.commit()
        
        # Get instrument_id
        res = await db.execute(text("SELECT instrument_id FROM instrument_master WHERE symbol = 'DUMMY'"))
        instrument_id = res.fetchone()[0]
        
        # 2. Insert EOD stock candles (timeframe = 1440)
        target_ts = datetime.utcnow()
        await db.execute(text(
            "INSERT INTO stock_candle (instrument_id, timeframe, candle_ts, open, high, low, close, volume) "
            "VALUES (:iid, 1440, :ts, 150.0, 160.0, 140.0, 157.0, 100000)"
        ), {"iid": instrument_id, "ts": target_ts - timedelta(days=1)})
        await db.commit()
        
        # 3. Call method
        price = await WatchlistService.get_historical_price_closest_to(
            "NSE_EQ|DUMMY", "DUMMY", target_ts, db
        )
        
        assert price == 157.0
        
    finally:
        # Cleanup
        if instrument_id is not None:
            await db.execute(text("DELETE FROM stock_candle WHERE instrument_id = :iid"), {"iid": instrument_id})
            await db.execute(text("DELETE FROM instrument_master WHERE instrument_id = :iid"), {"iid": instrument_id})
            await db.commit()
        await db.close()
