"""
Scanner Snapshot Model
Stores pre-computed scan results for fast UI reads.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Index
from datetime import datetime
from database import Base


class ScannerSnapshot(Base):
    """
    Pre-computed scanner results.
    UI reads ONLY from this table - never runs strategies in request path.
    """
    __tablename__ = "scanner_snapshot"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(50), nullable=False, index=True)
    interval = Column(String(10), nullable=False, default="1d")
    
    # Price data
    ltp = Column(Float, nullable=False)
    prev_close = Column(Float, nullable=False)
    change_pct = Column(Float, nullable=False)
    
    # Pre-computed indicators (JSON blob)
    indicators = Column(JSON, nullable=True)
    
    # Active signals
    active_strategies = Column(JSON, nullable=True)  # List of strategy names with signals
    signal_types = Column(JSON, nullable=True)  # List of signal types (BUY/SELL)
    signal_strength = Column(Float, default=0.0)  # Aggregate confidence
    
    # Categorization
    momentum_bucket = Column(String(30), nullable=True)
    trend_direction = Column(String(10), nullable=True)  # BULLISH/BEARISH/NEUTRAL
    
    # Metadata
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_snapshot_symbol_interval', 'symbol', 'interval'),
        Index('idx_snapshot_updated', 'updated_at'),
        {'extend_existing': True}
    )
    
    def to_dict(self):
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "ltp": self.ltp,
            "prev_close": self.prev_close,
            "change_pct": round(self.change_pct, 2),
            "indicators": self.indicators or {},
            "active_strategies": self.active_strategies or [],
            "signal_types": self.signal_types or [],
            "signal_strength": self.signal_strength,
            "momentum_bucket": self.momentum_bucket,
            "trend_direction": self.trend_direction,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
