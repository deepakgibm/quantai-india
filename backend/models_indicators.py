"""
Precomputed Indicators Model
Stores pre-calculated technical indicators to avoid on-demand computation.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Index, UniqueConstraint
from datetime import datetime
from database import Base


class PrecomputedIndicator(Base):
    """
    Stores precomputed technical indicators for each symbol/interval/timestamp.
    Updated by background ETL job, consumed by scanners for fast queries.
    """
    __tablename__ = "precomputed_indicators"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False)
    interval = Column(String(10), nullable=False, default="1d")  # 1min, 5min, 15min, 30min, 1d
    timestamp = Column(DateTime, nullable=False)
    
    # Price context (for reference, avoids join)
    close = Column(Float, nullable=True)
    volume = Column(Integer, nullable=True)
    
    # Momentum Indicators
    rsi_14 = Column(Float, nullable=True)          # RSI with 14-period
    roc_10 = Column(Float, nullable=True)          # Rate of Change 10-period
    roc_20 = Column(Float, nullable=True)          # Rate of Change 20-period
    macd = Column(Float, nullable=True)            # MACD line
    macd_signal = Column(Float, nullable=True)     # MACD signal line
    macd_histogram = Column(Float, nullable=True)  # MACD histogram
    
    # Volume Indicators
    mfi_14 = Column(Float, nullable=True)          # Money Flow Index 14-period
    vwap = Column(Float, nullable=True)            # Volume Weighted Average Price
    volume_sma_20 = Column(Float, nullable=True)   # 20-period SMA of volume
    volume_ratio = Column(Float, nullable=True)    # Current volume / SMA volume
    
    # Volatility Indicators
    atr_14 = Column(Float, nullable=True)          # Average True Range 14-period
    bollinger_upper = Column(Float, nullable=True) # Upper Bollinger Band (20, 2)
    bollinger_lower = Column(Float, nullable=True) # Lower Bollinger Band (20, 2)
    bollinger_mid = Column(Float, nullable=True)   # Middle Bollinger Band (SMA 20)
    bollinger_pct = Column(Float, nullable=True)   # %B indicator
    
    # Trend Indicators
    ema_9 = Column(Float, nullable=True)           # 9-period EMA
    ema_20 = Column(Float, nullable=True)          # 20-period EMA
    ema_50 = Column(Float, nullable=True)          # 50-period EMA
    sma_20 = Column(Float, nullable=True)          # 20-period SMA
    sma_50 = Column(Float, nullable=True)          # 50-period SMA
    trend_strength = Column(Float, nullable=True)  # ADX or custom trend score
    
    # Derived Scores (for scanner optimization)
    momentum_score = Column(Float, nullable=True)  # Composite momentum score (0-100)
    volatility_score = Column(Float, nullable=True) # Composite volatility score (0-100)
    
    # Metadata
    computed_at = Column(DateTime, default=datetime.utcnow)
    
    # Optimized indexes for scanner queries
    __table_args__ = (
        # Primary lookup: symbol + interval + time range
        Index('idx_indicators_symbol_interval_ts', 'symbol', 'interval', 'timestamp'),
        # Fast "latest" query per symbol
        Index('idx_indicators_symbol_ts_desc', 'symbol', 'timestamp'),
        # Score-based queries (find top momentum stocks)
        Index('idx_indicators_momentum_score', 'momentum_score'),
        # Uniqueness constraint
        UniqueConstraint('symbol', 'interval', 'timestamp', name='uq_indicator_symbol_interval_ts'),
        {'extend_existing': True}
    )
    
    def __repr__(self):
        return f"<PrecomputedIndicator(symbol={self.symbol}, interval={self.interval}, ts={self.timestamp})>"


class IndicatorComputeJob(Base):
    """
    Tracks indicator computation jobs for monitoring and debugging.
    """
    __tablename__ = "indicator_compute_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(100), nullable=False, unique=True)
    status = Column(String(20), nullable=False, default="pending")  # pending, running, completed, failed
    
    # Scope
    symbols_count = Column(Integer, nullable=True)
    interval = Column(String(10), nullable=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    
    # Progress
    symbols_processed = Column(Integer, default=0)
    rows_computed = Column(Integer, default=0)
    
    # Performance
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    # Error tracking
    error_message = Column(String(500), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_compute_job_status', 'status'),
        {'extend_existing': True}
    )
