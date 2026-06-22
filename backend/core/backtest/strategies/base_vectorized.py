import polars as pl
from abc import ABC, abstractmethod

class BaseVectorizedStrategy(ABC):
    """
    Abstract base class for vectorized strategies using Polars.
    Vectorized strategies calculate all signals for the entire dataset at once.
    """
    
    def __init__(self, **params):
        self.params = params
        
    @abstractmethod
    def compute_indicators(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Calculate technical indicators using Polars expressions.
        Args:
            df: Polars DataFrame with ohlcv data
        Returns:
            DataFrame with added indicator columns
        """
        pass
        
    @abstractmethod
    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Generate entry/exit signals using Polars expressions.
        Adds a 'signal' column: 1 (BUY), -1 (SELL), 0 (NEUTRAL)
        Args:
            df: Polars DataFrame with indicators
        Returns:
            DataFrame with 'signal' column
        """
        pass
