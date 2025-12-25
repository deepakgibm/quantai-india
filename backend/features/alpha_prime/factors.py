"""
AlphaPrime Factor Calculations

Vectorized implementations of technical indicators using pandas/numpy.
All calculations follow Udacity AI Trading curriculum best practices.

Factors:
- Momentum: RSI, MACD Divergence
- Volatility: ATR, Bollinger Bands
- Volume: VWAP, Volume Ratio
"""

import numpy as np
import pandas as pd
from typing import Optional
from config import settings


class FactorEngine:
    """Vectorized technical factor calculations"""
    
    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = None) -> pd.Series:
        """
        Calculate Relative Strength Index
        
        Args:
            prices: Close prices
            period: Lookback period (default from config)
            
        Returns:
            RSI values (0-100)
        """
        period = period or settings.RSI_PERIOD
        
        # Calculate price changes
        delta = prices.diff()
        
        # Separate gains and losses
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)
        
        # Calculate exponential moving averages
        avg_gain = gains.ewm(span=period, adjust=False).mean()
        avg_loss = losses.ewm(span=period, adjust=False).mean()
        
        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def calculate_macd(
        prices: pd.Series,
        fast: int = None,
        slow: int = None,
        signal: int = None
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate MACD (Moving Average Convergence Divergence)
        
        Returns:
            (macd_line, signal_line, divergence)
        """
        fast = fast or settings.MACD_FAST
        slow = slow or settings.MACD_SLOW
        signal = signal or settings.MACD_SIGNAL
        
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        divergence = macd_line - signal_line
        
        return macd_line, signal_line, divergence
    
    @staticmethod
    def calculate_atr(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = None
    ) -> pd.Series:
        """
        Calculate Average True Range (volatility measure)
        """
        period = period or settings.ATR_PERIOD
        
        # True Range components
        hl = high - low
        hc = abs(high - close.shift(1))
        lc = abs(low - close.shift(1))
        
        # True Range is the maximum of the three
        tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        
        # ATR is the exponential moving average of TR
        atr = tr.ewm(span=period, adjust=False).mean()
        
        return atr
    
    @staticmethod
    def calculate_bollinger_bands(
        prices: pd.Series,
        period: int = None,
        std_dev: float = None
    ) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
        """
        Calculate Bollinger Bands
        
        Returns:
            (middle_band, upper_band, lower_band, position)
            position = (price - lower) / (upper - lower)
        """
        period = period or settings.BOLLINGER_PERIOD
        std_dev = std_dev or settings.BOLLINGER_STD
        
        middle_band = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        
        upper_band = middle_band + (std * std_dev)
        lower_band = middle_band - (std * std_dev)
        
        # Position: 0 = at lower band, 1 = at upper band
        position = (prices - lower_band) / (upper_band - lower_band)
        position = position.clip(0, 1)  # Clamp to [0, 1]
        
        return middle_band, upper_band, lower_band, position
    
    @staticmethod
    def calculate_vwap(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series,
        period: int = None
    ) -> pd.Series:
        """
        Calculate Volume Weighted Average Price
        """
        period = period or settings.VWAP_PERIOD
        
        # Typical price
        typical_price = (high + low + close) / 3
        
        # VWAP = sum(typical_price * volume) / sum(volume)
        vwap = (typical_price * volume).rolling(window=period).sum() / volume.rolling(window=period).sum()
        
        return vwap
    
    @staticmethod
    def calculate_volume_ratio(
        volume: pd.Series,
        period: int = None
    ) -> pd.Series:
        """
        Calculate volume ratio (current volume / average volume)
        """
        period = period or settings.VOLUME_SMA_PERIOD
        
        avg_volume = volume.rolling(window=period).mean()
        ratio = volume / avg_volume
        
        return ratio
    
    @staticmethod
    def calculate_all_factors(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all factors for a DataFrame of OHLCV data
        
        Args:
            df: DataFrame with columns [symbol, timestamp, open, high, low, close, volume]
            
        Returns:
            DataFrame with all factor columns added
        """
        # Group by symbol to calculate factors per stock
        results = []
        
        for symbol, group in df.groupby('symbol'):
            group = group.sort_values('timestamp').copy()
            
            # Momentum factors
            group['rsi'] = FactorEngine.calculate_rsi(group['close'])
            macd, signal, divergence = FactorEngine.calculate_macd(group['close'])
            group['macd'] = macd
            group['macd_signal'] = signal
            group['macd_divergence'] = divergence
            
            # Volatility factors
            group['atr'] = FactorEngine.calculate_atr(
                group['high'],
                group['low'],
                group['close']
            )
            bb_mid, bb_upper, bb_lower, bb_pos = FactorEngine.calculate_bollinger_bands(group['close'])
            group['bollinger_upper'] = bb_upper
            group['bollinger_lower'] = bb_lower
            group['bollinger_position'] = bb_pos
            
            # Volume factors
            group['vwap'] = FactorEngine.calculate_vwap(
                group['high'],
                group['low'],
                group['close'],
                group['volume']
            )
            group['vwap_ratio'] = group['close'] / group['vwap']
            
            group['volume_sma'] = group['volume'].rolling(window=settings.VOLUME_SMA_PERIOD).mean()
            group['volume_ratio'] = FactorEngine.calculate_volume_ratio(group['volume'])
            
            results.append(group)
        
        return pd.concat(results, ignore_index=True)
    
    @staticmethod
    def normalize_factors(df: pd.DataFrame) -> pd.DataFrame:
        """
        Z-score normalization of factor values for ML input
        
        Normalizes: RSI, MACD divergence, ATR, Bollinger position, VWAP ratio, Volume ratio
        """
        factor_cols = [
            'rsi', 'macd_divergence', 'atr', 'bollinger_position',
            'vwap_ratio', 'volume_ratio'
        ]
        
        for col in factor_cols:
            if col in df.columns:
                mean = df[col].mean()
                std = df[col].std()
                df[f'{col}_norm'] = (df[col] - mean) / (std + 1e-8)  # Avoid division by zero
        
        return df


def test_factors():
    """Test factor calculations with sample data"""
    # Generate sample OHLCV data
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=100, freq='1min')
    
    sample_data = pd.DataFrame({
        'symbol': ['TEST'] * 100,
        'timestamp': dates,
        'open': 100 + np.random.randn(100).cumsum(),
        'high': 100 + np.random.randn(100).cumsum() + 1,
        'low': 100 + np.random.randn(100).cumsum() - 1,
        'close': 100 + np.random.randn(100).cumsum(),
        'volume': np.random.randint(1000, 10000, 100)
    })
    
    # Calculate factors
    result = FactorEngine.calculate_all_factors(sample_data)
    
    print("Factor Calculation Test:")
    print(f"Input rows: {len(sample_data)}")
    print(f"Output rows: {len(result)}")
    print(f"\nCalculated factors:")
    print(result[['symbol', 'timestamp', 'rsi', 'macd_divergence', 'atr', 'vwap_ratio']].tail())
    
    return result


if __name__ == "__main__":
    test_factors()
