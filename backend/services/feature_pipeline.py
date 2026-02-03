import pandas as pd
import numpy as np
import logging
from typing import Optional
from core.scanner.indicator_utils import (
    rsi, macd, bollinger_bands, atr, adx, volume_ratio
)

logger = logging.getLogger(__name__)

class FeatureEngineeringPipeline:
    """
    Pure feature engineering pipeline that transforms OHLCV data into 
    standardized features for ML/DL models.
    
    Strictly follows:
    1. Log-returns for price movement.
    2. Scaled/Normalized indicators where possible.
    3. Multi-horizon labels (t+1, t+3, t+5).
    """
    
    def __init__(self, version: str = "v1"):
        self.version = version
        
    def build_features(self, ohlcv_df: pd.DataFrame) -> pd.DataFrame:
        """
        Takes a DataFrame with [timestamp, open, high, low, close, volume]
        Returns a DataFrame with enriched features and labels.
        """
        if ohlcv_df.empty or len(ohlcv_df) < 50:
            return pd.DataFrame()
            
        df = ohlcv_df.copy().sort_values('timestamp')
        
        # Price Features (Log Returns)
        df['log_return'] = np.log(df['close'] / df['close'].shift(1))
        df['volatility_20'] = df['log_return'].rolling(window=20).std()
        
        # Technical Indicators
        # Normalize indicators where possible
        df['rsi_14'] = rsi(df['close'], 14) / 100.0 # 0 to 1
        
        macd_line, signal_line, hist = macd(df['close'])
        # MACD needs normalization - use % of price
        df['macd_line'] = macd_line / df['close'] * 100
        df['macd_signal'] = signal_line / df['close'] * 100
        df['macd_hist'] = hist / df['close'] * 100
        
        bb_mid, bb_upper, bb_lower = bollinger_bands(df['close'])
        df['bb_pct_b'] = (df['close'] - bb_lower) / (bb_upper - bb_lower) # approx 0 to 1
        
        df['atr_14_pct'] = atr(df['high'], df['low'], df['close'], 14) / df['close'] * 100
        
        adx_val, plus_di, minus_di = adx(df['high'], df['low'], df['close'], 14)
        df['adx_14'] = adx_val / 100.0
        df['plus_di'] = plus_di / 100.0
        df['minus_di'] = minus_di / 100.0
        
        df['volume_ratio_20'] = volume_ratio(df['volume'], 20)
        
        # Labels (Future Returns) - To be used in training
        df['target_return_1'] = df['log_return'].shift(-1)
        df['target_return_3'] = np.log(df['close'].shift(-3) / df['close'])
        df['target_return_5'] = np.log(df['close'].shift(-5) / df['close'])
        
        # Quantile Bands (for the new backtesting requirement)
        df['rolling_q75'] = df['log_return'].rolling(window=50).quantile(0.75)
        df['rolling_q25'] = df['log_return'].rolling(window=50).quantile(0.25)
        
        # Cleanup
        df = df.dropna(subset=['log_return', 'rsi_14', 'bb_pct_b'])
        
        return df

# Singleton
_pipeline: Optional[FeatureEngineeringPipeline] = None

def get_feature_pipeline(version: str = "v1") -> FeatureEngineeringPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = FeatureEngineeringPipeline(version)
    return _pipeline
