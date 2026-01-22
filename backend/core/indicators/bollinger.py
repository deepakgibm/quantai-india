
import pandas as pd
from typing import Tuple

def bollinger_bands(close: pd.Series, period: int = 20, std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate Bollinger Bands.
    
    Args:
        close: Closing price series
        period: SMB period (default 20)
        std_dev: Standard deviation multiplier (default 2.0)
        
    Returns:
        Tuple[pd.Series, pd.Series, pd.Series]: (Middle Band, Upper Band, Lower Band)
    """
    middle = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    return middle, upper, lower
