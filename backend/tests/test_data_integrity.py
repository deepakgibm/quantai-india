import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

from core.exceptions import DataUnavailableError
from services.explainable_ai import get_explainable_ai_report

def test_explainable_ai_fails_on_empty_data():
    """
    Ensure the Explainable AI report raises a DataUnavailableError
    when data is insufficient instead of falling back to random/mock data generation.
    """
    symbol = "TEST_MISSING"

    # Mock indicator service to return empty DataFrame
    with patch("services.explainable_ai.get_indicator_service") as mock_get_indicator:
        mock_service = MagicMock()
        # Return an empty DataFrame to simulate no data in DB
        mock_service.get_ohlcv_data.return_value = pd.DataFrame()
        mock_get_indicator.return_value = mock_service

        # Expect DataUnavailableError when trying to compute AI report
        with pytest.raises(DataUnavailableError) as exc_info:
            get_explainable_ai_report(symbol)

        # Validate the exception context
        assert exc_info.value.symbol == symbol
        assert exc_info.value.required_candles == 30
        assert exc_info.value.available_candles == 0
        assert "Insufficient historical data" in exc_info.value.message

def test_explainable_ai_fails_on_insufficient_data():
    """
    Ensure it fails when there's some data, but less than the minimum required.
    """
    symbol = "TEST_INSUFFICIENT"
    
    # Return a DataFrame with only 5 candles
    small_df = pd.DataFrame({
        "timestamp": pd.date_range("2023-01-01", periods=5),
        "open": [100]*5, "high": [105]*5, "low": [95]*5, "close": [102]*5, "volume": [1000]*5
    })
    
    with patch("services.explainable_ai.get_indicator_service") as mock_get_indicator:
        mock_service = MagicMock()
        mock_service.get_ohlcv_data.return_value = small_df
        mock_get_indicator.return_value = mock_service

        with pytest.raises(DataUnavailableError) as exc_info:
            get_explainable_ai_report(symbol)

        assert exc_info.value.available_candles == 5
