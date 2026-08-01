from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import pandas as pd
from datetime import datetime

@pytest.fixture
def anyio_backend():
    return 'asyncio'

@pytest.mark.anyio
async def test_smc_service_upstox_fallback():
    # 1. Mock database session
    mock_db = AsyncMock()
    
    # Mock InstrumentMaster lookup
    mock_instrument = MagicMock()
    mock_instrument.instrument_id = 1
    mock_instrument.instrument_key = "NSE_EQ|RELIANCE"
    
    mock_res_inst = MagicMock()
    mock_res_inst.scalars.return_value.first.return_value = mock_instrument
    mock_res_candles = MagicMock()
    mock_res_candles.scalars.return_value.all.return_value = []
    
    exec_count = 0
    async def db_execute_side_effect(q):
        nonlocal exec_count
        exec_count += 1
        if exec_count % 2 == 1:
            return mock_res_inst
        else:
            return mock_res_candles
            
    mock_db.execute.side_effect = db_execute_side_effect

    # Mock UpstoxClient get_historical_data
    mock_df = pd.DataFrame([
        {
            "symbol": "RELIANCE",
            "timestamp": datetime(2026, 6, 1) + pd.Timedelta(days=i),
            "open": 2400.0 + i * 5,
            "high": 2450.0 + i * 5,
            "low": 2380.0 + i * 5,
            "close": 2420.0 + i * 5,
            "volume": 100000
        }
        for i in range(50)
    ])
    
    with patch("services.upstox_client.UpstoxClient.get_historical_data", new_callable=AsyncMock) as mock_get_hist:
        mock_get_hist.return_value = mock_df
        
        from services.saas.smc_service import SMCService
        result = await SMCService.detect_smc_patterns(mock_db, "RELIANCE")
        
        assert result["symbol"] == "RELIANCE"
        # Since it successfully fetched candles from Upstox, it should run calculations
        assert isinstance(result["fair_value_gaps"], list)
        assert isinstance(result["order_blocks"], list)
        
        # Test timeframe parameter passing
        result_15m = await SMCService.detect_smc_patterns(mock_db, "RELIANCE", "15m")
        assert result_15m["symbol"] == "RELIANCE"
        assert result_15m["timeframe"] == "15M"
        
        mock_get_hist.assert_called()


@pytest.mark.anyio
async def test_pattern_recognition_upstox_fallback():
    # 1. Mock database session
    mock_db = AsyncMock()
    
    # Mock InstrumentMaster lookup
    mock_instrument = MagicMock()
    mock_instrument.instrument_id = 1
    mock_instrument.instrument_key = "NSE_EQ|RELIANCE"
    
    # Mock return values for DB executes
    mock_execute_results = []
    
    # First query is InstrumentMaster: return our mock instrument
    mock_res_inst = MagicMock()
    mock_res_inst.scalars.return_value.first.return_value = mock_instrument
    mock_execute_results.append(mock_res_inst)
    
    # Second query is StockCandle: return empty list (simulating unseeded DB)
    mock_res_candles = MagicMock()
    mock_res_candles.scalars.return_value.all.return_value = []
    mock_execute_results.append(mock_res_candles)
    
    mock_db.execute.side_effect = mock_execute_results

    # Mock UpstoxClient get_historical_data
    mock_df = pd.DataFrame([
        {
            "symbol": "RELIANCE",
            "timestamp": datetime(2026, 6, 1) + pd.Timedelta(days=i),
            "open": 2400.0 + i * 5,
            "high": 2450.0 + i * 5,
            "low": 2380.0 + i * 5,
            "close": 2420.0 + i * 5,
            "volume": 100000
        }
        for i in range(60)
    ])
    
    with patch("services.upstox_client.UpstoxClient.get_historical_data", new_callable=AsyncMock) as mock_get_hist:
        mock_get_hist.return_value = mock_df
        
        from services.saas.pattern_recognition_service import PatternRecognitionService
        result = await PatternRecognitionService.detect_patterns(mock_db, "RELIANCE")
        
        assert result["symbol"] == "RELIANCE"
        assert isinstance(result["candlestick_patterns"], list)
        mock_get_hist.assert_called_once()


@pytest.mark.anyio
async def test_services_empty_fallbacks():
    # 1. Mock database session returning empty
    mock_db = AsyncMock()
    mock_res_inst = MagicMock()
    mock_res_inst.scalars.return_value.first.return_value = None
    mock_db.execute.return_value = mock_res_inst
    
    from services.saas.smc_service import SMCService
    smc_result = await SMCService.detect_smc_patterns(mock_db, "RELIANCE")
    assert smc_result["fair_value_gaps"] == []
    assert smc_result["order_blocks"] == []
    
    from services.saas.pattern_recognition_service import PatternRecognitionService
    pattern_result = await PatternRecognitionService.detect_patterns(mock_db, "RELIANCE")
    assert pattern_result["candlestick_patterns"] == []
    assert pattern_result["harmonic_patterns"] == []
    assert pattern_result["chart_patterns"] == []
