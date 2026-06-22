import pytest
from unittest.mock import MagicMock, patch
from services.bot.bot_orchestrator import BotOrchestrator, BotRunResult
from services.derivatives_service import DerivativesService
from database import SessionLocal
from models_bot import BotRun, BotSignalRecord

@pytest.mark.anyio
async def test_bot_persistence_logic():
    """Test that bot run results are correctly persisted to the database."""
    orchestrator = BotOrchestrator()
    run_id = "test_persist_123"
    
    # Mock run data in orchestrator memory
    orchestrator._runs[run_id] = {
        "started_at": "2026-05-02T10:00:00",
        "step": "COMPLETED",
    }
    
    # Create a mock result
    result = BotRunResult(
        run_id=run_id,
        market_trend={"trend": "BULLISH", "last_close": 22000, "ema_50": 21500, "ema_200": 21000, "momentum": 2.5},
        buy_signals=[{
            "symbol": "RELIANCE", "signal_type": "BUY", "conviction": "STRONG", 
            "pcr_value": 1.2, "pcr_source": "upstox", "current_price": 2500.0,
            "correlation": 0.85, "price_change_pct": 1.5
        }],
        sell_signals=[],
        summary={"total_stocks_analyzed": 500, "buy_count": 1, "sell_count": 0, "data_sources": {"pcr": "upstox"}},
        completed_at="2026-05-02T10:05:00"
    )
    
    # Run persistence
    await orchestrator._persist_run(run_id, result, triggered_by="manual")
    
    # Verify in DB
    db = SessionLocal()
    try:
        db_run = db.query(BotRun).filter(BotRun.run_id == run_id).first()
        assert db_run is not None
        assert db_run.status == "COMPLETED"
        assert db_run.buy_count == 1
        assert db_run.triggered_by == "manual"
        
        db_signal = db.query(BotSignalRecord).filter(BotSignalRecord.run_id == run_id).first()
        assert db_signal is not None
        assert db_signal.symbol == "RELIANCE"
        assert db_signal.pcr_source == "upstox"
        
        # Test fallback loading
        loaded_result = orchestrator.get_result(run_id)
        assert loaded_result is not None
        assert loaded_result.run_id == run_id
        assert len(loaded_result.buy_signals) == 1
        
    finally:
        # Cleanup
        db.query(BotSignalRecord).filter(BotSignalRecord.run_id == run_id).delete()
        db.query(BotRun).filter(BotRun.run_id == run_id).delete()
        db.commit()
        db.close()

@pytest.mark.anyio
async def test_pcr_source_tracking():
    """Test that DerivativesService correctly tracks upstox vs simulated source."""
    service = DerivativesService()
    
    # Test case 1: Stock with derivatives (should try dragonfly cache first)
    mock_cache = MagicMock()
    mock_cache.get.return_value = [
        {"strike_price": 100, "call_options": {"market_data": {"oi": 1000}}, "put_options": {"market_data": {"oi": 1100}}}
    ]
    with patch('services.dragonfly_client.get_cache', return_value=mock_cache):
        data = await service.get_derivatives_data("RELIANCE", 1.0)
        assert data.data_source == "upstox"
        assert data.pcr == 1.1
        
    # Test case 2: Stock without derivatives (should be N/A)
    data = await service.get_derivatives_data("NON_EXISTENT", 1.0)
    assert data.has_derivatives is False
    
    # Test case 3: API failure (should fallback to simulated)
    mock_cache_fail = MagicMock()
    mock_cache_fail.get.side_effect = Exception("Cache down")
    with patch('services.dragonfly_client.get_cache', return_value=mock_cache_fail):
        data = await service.get_derivatives_data("RELIANCE", 1.0)
        assert data.data_source == "simulated"
        assert data.pcr is not None

@pytest.mark.anyio
async def test_alert_formatting():
    """Test Telegram alert message formatting."""
    from services.bot.alert_service import AlertService
    
    service = AlertService()
    # Mocking disabled to test formatting
    service.enabled = True
    
    signals = [
        {"symbol": "RELIANCE", "signal_type": "BUY", "conviction": "STRONG", "current_price": 2500, "price_change_pct": 1.5, "correlation": 0.8},
        {"symbol": "TCS", "signal_type": "SELL", "conviction": "STRONG", "current_price": 3500, "price_change_pct": -2.0, "correlation": 0.75},
        {"symbol": "INFY", "signal_type": "BUY", "conviction": "MODERATE", "current_price": 1500, "price_change_pct": 0.5, "correlation": 0.6},
    ]
    
    market_trend = {"trend": "BULLISH", "last_close": 22000, "momentum": 1.2}
    
    msg = service._format_message([s for s in signals if s["conviction"] == "STRONG"], market_trend, "test_run")
    
    assert "QuantAI Signal Bot" in msg
    assert "RELIANCE" in msg
    assert "TCS" in msg
    assert "INFY" not in msg  # Moderate conviction excluded
    assert "BULLISH" in msg
