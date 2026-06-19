import pytest

SYMBOLS = ["TCS", "INFY", "RELIANCE", "SBIN", "HDFCBANK", "ICICIBANK"]

@pytest.mark.parametrize("symbol", SYMBOLS)
def test_option_flow_chart_daily(api_client, symbol):
    """Verify daily chart endpoint fetches 30+ candles and computes indicators for symbol."""
    r = api_client.get(f"/api/option-flow/{symbol}/chart?interval=1d&lookback_days=90", auth=True)
    assert r.status_code == 200
    data = r.json()
    
    assert data["success"] is True
    chart_data = data["data"]
    assert chart_data["symbol"] == symbol
    assert chart_data["interval"] == "1d"
    
    candles = chart_data["candles"]
    assert len(candles) >= 30, f"Expected 30+ candles for {symbol}, got {len(candles)}"
    
    # Verify indicator presence
    for c in candles:
        assert "open" in c
        assert "high" in c
        assert "low" in c
        assert "close" in c
        assert "volume" in c
        assert "ema_20" in c
        assert "ema_50" in c
        assert "vwap" in c
        
    assert "support_zones" in chart_data
    assert "resistance_zones" in chart_data
    assert "volume_profile" in chart_data
    assert chart_data["available_history_days"] >= 0
    assert chart_data["candle_count"] == len(candles)
    assert "from_date" in chart_data
    assert "to_date" in chart_data

@pytest.mark.parametrize("symbol", SYMBOLS)
def test_option_flow_chart_intraday(api_client, symbol):
    """Verify intraday chart endpoint fetches 5-minute candles and computes indicators for symbol."""
    r = api_client.get(f"/api/option-flow/{symbol}/chart?interval=5m&lookback_days=90", auth=True)
    assert r.status_code == 200
    data = r.json()
    
    assert data["success"] is True
    chart_data = data["data"]
    assert chart_data["symbol"] == symbol
    assert chart_data["interval"] == "5m"
    
    candles = chart_data["candles"]
    assert len(candles) >= 30, f"Expected 30+ candles for {symbol}, got {len(candles)}"
    assert chart_data["available_history_days"] >= 0
    assert chart_data["candle_count"] == len(candles)
    assert "from_date" in chart_data
    assert "to_date" in chart_data
    
    c = candles[0]
    assert "open" in c
    assert "ema_20" in c
    assert "ema_50" in c
    assert "vwap" in c

def test_option_flow_chart_15m(api_client):
    """Verify 15-minute chart endpoint fetches candles and computes indicators."""
    r = api_client.get("/api/option-flow/RELIANCE/chart?interval=15m&lookback_days=45", auth=True)
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    chart_data = data["data"]
    assert chart_data["interval"] == "15m"
    candles = chart_data["candles"]
    assert len(candles) >= 10
    c = candles[0]
    assert "open" in c
    assert "ema_20" in c

def test_option_flow_chart_30m(api_client):
    """Verify 30-minute chart endpoint fetches candles and computes indicators."""
    r = api_client.get("/api/option-flow/RELIANCE/chart?interval=30m&lookback_days=45", auth=True)
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    chart_data = data["data"]
    assert chart_data["interval"] == "30m"
    candles = chart_data["candles"]
    assert len(candles) >= 5
    c = candles[0]
    assert "open" in c
    assert "ema_20" in c
