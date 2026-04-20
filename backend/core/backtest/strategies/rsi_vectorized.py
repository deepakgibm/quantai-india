import polars as pl
from .base_vectorized import BaseVectorizedStrategy

class RSIVectorizedStrategy(BaseVectorizedStrategy):
    """
    RSI Mean Reversion Strategy implemented with Polars vectorized operations.
    BUY when RSI < 30, EXIT when RSI > 70.
    """
    
    def __init__(self, rsi_period: int = 14, oversold: int = 30, overbought: int = 70):
        super().__init__(rsi_period=rsi_period, oversold=oversold, overbought=overbought)
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought

    def compute_indicators(self, df: pl.DataFrame) -> pl.DataFrame:
        """Vectorized RSI calculation."""
        period = self.rsi_period
        
        # Calculate diffs
        df = df.with_columns([
            pl.col("close").diff().alias("diff")
        ])
        
        # Gain and Loss
        df = df.with_columns([
            pl.when(pl.col("diff") > 0).then(pl.col("diff")).otherwise(0).alias("gain"),
            pl.when(pl.col("diff") < 0).then(pl.col("diff").abs()).otherwise(0).alias("loss")
        ])
        
        # Simple weighted moving average (simplified exponential for vectorized demo)
        # Using rolling_mean as a fast approximation
        df = df.with_columns([
            pl.col("gain").rolling_mean(window_size=period).alias("avg_gain"),
            pl.col("loss").rolling_mean(window_size=period).alias("avg_loss")
        ])
        
        df = df.with_columns([
            (pl.col("avg_gain") / pl.col("avg_loss")).alias("rs")
        ])
        
        df = df.with_columns([
            (100 - (100 / (1 + pl.col("rs")))).alias("rsi")
        ])
        
        return df.fill_null(0)

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        """Vectorized Signal generation."""
        # Entry: RSI < 30
        # Exit: RSI > 70
        # This implementation requires state tracking (if we are in or out)
        # For a truly vectorized version of "RSI cross", we can use cumulative logic:
        
        df = df.with_columns([
            pl.when(pl.col("rsi") < self.oversold).then(1)
              .when(pl.col("rsi") > self.overbought).then(0)
              .otherwise(None).alias("raw_signal")
        ])
        
        # Fill forward the entry/exit signal to represent position
        df = df.with_columns([
            pl.col("raw_signal").forward_fill().fill_null(0).alias("signal")
        ])
        
        return df
