
import pandas as pd
import numpy as np
import pytest
from backend.core.indicators import rsi, macd, ema, bollinger_bands

def test_ema():
    data = pd.Series([10, 11, 12, 13, 14, 15, 16, 17, 18, 19])
    result = ema(data, period=5)
    assert len(result) == 10
    assert result.iloc[-1] > result.iloc[0]

def test_rsi():
    # rising prices -> high RSI
    data = pd.Series(np.linspace(10, 20, 20)) 
    result = rsi(data, period=14)
    # RSI requires period+1 to start having values? 
    # Pandas implementation might handle it.
    # checking last value
    assert result.iloc[-1] > 70  # Should be high

def test_bollinger():
    data = pd.Series([100] * 20) # Flat
    middle, upper, lower = bollinger_bands(data, period=20, std_dev=2)
    assert middle.iloc[-1] == 100
    assert upper.iloc[-1] == 100 # std dev is 0
    assert lower.iloc[-1] == 100

def test_macd():
    data = pd.Series(np.linspace(10, 20, 50))
    m_line, s_line, hist = macd(data)
    assert len(m_line) == 50
    assert len(s_line) == 50
