"""
APF - Feature Builder
Extracts technical indicators and features from OHLCV data
"""

import logging
import numpy as np
import pandas as pd
from typing import List, Tuple

logger = logging.getLogger(__name__)


class FeatureBuilder:
    """
    Builds ML features from OHLCV candle data.
    Uses technical indicators optimized for short-term prediction.
    """
    
    # Feature window sizes
    RSI_PERIOD = 14
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    BB_PERIOD = 20
    ATR_PERIOD = 14
    LAG_PERIODS = [1, 2, 3, 5, 10]
    
    def __init__(self):
        self.feature_names: List[str] = []
    
    def build_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Build all features from OHLCV DataFrame.
        
        Args:
            df: DataFrame with columns [open, high, low, close, volume]
            
        Returns:
            DataFrame with feature columns added
        """
        if df is None or len(df) < 30:
            logger.warning("Insufficient data for feature building")
            return None
        
        result = df.copy()
        
        # Price-based features
        result['returns'] = result['close'].pct_change()
        result['log_returns'] = np.log(result['close'] / result['close'].shift(1))
        
        # RSI
        result['rsi'] = self._calculate_rsi(result['close'], self.RSI_PERIOD)
        
        # MACD
        macd, signal, hist = self._calculate_macd(result['close'])
        result['macd'] = macd
        result['macd_signal'] = signal
        result['macd_hist'] = hist
        
        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = self._calculate_bollinger(result['close'])
        result['bb_upper'] = bb_upper
        result['bb_middle'] = bb_middle
        result['bb_lower'] = bb_lower
        result['bb_width'] = (bb_upper - bb_lower) / bb_middle
        result['bb_position'] = (result['close'] - bb_lower) / (bb_upper - bb_lower)
        
        # ATR (Average True Range)
        result['atr'] = self._calculate_atr(result)
        result['atr_pct'] = result['atr'] / result['close']
        
        # Volume features
        result['volume_sma'] = result['volume'].rolling(20).mean()
        result['volume_ratio'] = result['volume'] / result['volume_sma']
        
        # Price momentum
        result['roc_5'] = result['close'].pct_change(5)
        result['roc_10'] = result['close'].pct_change(10)
        
        # Lag features (previous closes)
        for lag in self.LAG_PERIODS:
            result[f'close_lag_{lag}'] = result['close'].shift(lag)
            result[f'return_lag_{lag}'] = result['returns'].shift(lag)
        
        # Candlestick patterns (simplified)
        result['body_size'] = abs(result['close'] - result['open']) / result['open']
        result['upper_shadow'] = (result['high'] - result[['open', 'close']].max(axis=1)) / result['open']
        result['lower_shadow'] = (result[['open', 'close']].min(axis=1) - result['low']) / result['open']
        result['is_bullish'] = (result['close'] > result['open']).astype(int)
        
        # Target variable: next close (for training)
        result['target'] = result['close'].shift(-1)
        
        # Store feature names - exclude OHLCV, target, metadata, and non-numeric columns
        exclude_cols = {
            'open', 'high', 'low', 'close', 'volume', 'target', 'timestamp',
            'symbol', 'timeframe', 'feature_version', 'year', 'month',
            'instrument_key', 'instrument_id', 'company_name', 'exchange', 'series',
        }
        self.feature_names = [
            col for col in result.columns 
            if col not in exclude_cols and result[col].dtype in ('float64', 'float32', 'int64', 'int32', 'int8', 'bool')
        ]
        
        return result
    
    def get_feature_matrix(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """
        Get feature matrix X and target y for training.
        
        Returns:
            X: Feature matrix (n_samples, n_features)
            y: Target values
            timestamps: List of timestamp strings
        """
        features_df = self.build_features(df)
        if features_df is None:
            return None, None, []
        
        # Drop NaN rows
        features_df = features_df.dropna()
        
        if len(features_df) < 10:
            return None, None, []
        
        X = features_df[self.feature_names].values
        y = features_df['target'].values
        
        # Handle timestamps whether they are in a column or in the index
        if 'timestamp' in features_df.columns:
            ts = pd.to_datetime(features_df['timestamp'])
            timestamps = ts.dt.strftime('%Y-%m-%dT%H:%M:%S').tolist()
        elif hasattr(features_df.index, 'strftime'):
            timestamps = features_df.index.strftime('%Y-%m-%dT%H:%M:%S').tolist()
        else:
            timestamps = list(range(len(features_df)))
        
        return X, y, timestamps
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator."""
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_macd(self, prices: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD indicator."""
        ema_fast = prices.ewm(span=self.MACD_FAST, adjust=False).mean()
        ema_slow = prices.ewm(span=self.MACD_SLOW, adjust=False).mean()
        macd = ema_fast - ema_slow
        signal = macd.ewm(span=self.MACD_SIGNAL, adjust=False).mean()
        hist = macd - signal
        return macd, signal, hist
    
    def _calculate_bollinger(self, prices: pd.Series, period: int = 20, std_dev: float = 2.0
                            ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands."""
        middle = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return upper, middle, lower
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()
