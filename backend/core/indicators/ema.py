
import pandas as pd

def ema(series: pd.Series, period: int) -> pd.Series:
    """
    Calculate Exponential Moving Average (EMA).
    
    Args:
        series: Price series
        period: EMA period
        
    Returns:
        pd.Series: EMA values
    """
    return series.ewm(span=period, adjust=False).mean()
