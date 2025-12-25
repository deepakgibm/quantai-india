"""
Machine Learning Models for AlphaPrime
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Index, UniqueConstraint
from database import Base
from datetime import datetime

class Nifty100Daily(Base):
    """
    Daily OHLCV data for Nifty 100 stocks (20-year history).
    Used for long-term trend analysis and ML model training.
    """
    __tablename__ = "nifty100_daily"
    __table_args__ = (
        Index('idx_nifty100_symbol_timestamp', 'symbol', 'timestamp'),
        UniqueConstraint('symbol', 'timestamp', name='uq_nifty100_symbol_timestamp'),
        {'extend_existing': True}
    )

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    
    source = Column(String(20), nullable=False, default="yfinance")  # yfinance or upstox
    created_at = Column(DateTime, default=datetime.utcnow)

    
    def __repr__(self):
        return f"<Nifty100Daily(symbol={self.symbol}, date={self.timestamp.date()}, close={self.close})>"

