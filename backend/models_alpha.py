"""
AlphaPrime Module - Database Models

Production-grade SQLAlchemy models for the Smart Beta Multi-Factor trading system.
Follows Udacity AI Trading curriculum principles with institutional engineering practices.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


print(f"Loading models_alpha: {__name__}")

class StockData(Base):
    """
    Time-series OHLCV data storage for Nifty 200 stocks.
    Optimized for range queries with composite index on (symbol, timestamp).
    """
    __tablename__ = "stock_data"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # OHLCV data
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    
    # Additional metadata
    interval = Column(String(10), nullable=False, default="1min")  # 1min, 5min, 1day
    source = Column(String(20), nullable=False, default="upstox")  # upstox, yfinance
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships removed - signals are now independent
    
    # Composite indexes for fast range queries
    # idx_symbol_timestamp: WHERE symbol='RELIANCE' AND timestamp BETWEEN X AND Y
    # idx_symbol_interval_ts: WHERE symbol='RELIANCE' AND interval='1min' AND timestamp BETWEEN X AND Y
    __table_args__ = (
        Index('idx_symbol_timestamp', 'symbol', 'timestamp'),
        Index('idx_symbol_interval_ts', 'symbol', 'interval', 'timestamp'),
        UniqueConstraint('symbol', 'timestamp', 'interval', name='uq_symbol_timestamp_interval'),
        {'extend_existing': True}
    )
    
    def __repr__(self):
        return f"<StockData(symbol={self.symbol}, timestamp={self.timestamp}, close={self.close})>"


class StockCandle(Base):
    """
    Unified OHLCV storage for multi-timeframe data.
    Supports 1m, 5m, 15m, 1h, 1d timeframes.
    """
    __tablename__ = "stock_candles"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    instrument_key = Column(String(50), nullable=True, index=True)  # Upstox instrument key
    timestamp = Column(DateTime, nullable=False, index=True)
    timeframe = Column(String(10), nullable=False, index=True)  # 1m, 5m, 15m, 1h, 1d
    
    # OHLCV data
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    
    source = Column(String(20), nullable=False, default="upstox")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_candle_symbol_tf_ts', 'symbol', 'timeframe', 'timestamp'),
        Index('idx_candle_instkey_tf_ts', 'instrument_key', 'timeframe', 'timestamp'),
        UniqueConstraint('symbol', 'timestamp', 'timeframe', name='uq_candle_symbol_ts_tf'),
        {'extend_existing': True}
    )
    
    def __repr__(self):
        return f"<StockCandle(symbol={self.symbol}, timeframe={self.timeframe}, timestamp={self.timestamp})>"


class TimeframeMapper:
    """
    Utility class to map UI timeframes to database timeframe values.
    """
    MAPPING = {
        '1m': '1minute',
        '5m': '5minute', 
        '15m': '15minute',
        '1h': '1hour',
        '1d': '1day',
        '1D': '1day',
        'day': '1day',
        '1minute': '1minute',
        '5minute': '5minute',
        '15minute': '15minute',
        '1hour': '1hour',
        '1day': '1day',
    }
    
    @classmethod
    def to_db(cls, ui_tf: str) -> str:
        """Convert UI timeframe to database timeframe"""
        return cls.MAPPING.get(ui_tf, ui_tf)
    
    @classmethod
    def from_db(cls, db_tf: str) -> str:
        """Convert database timeframe to UI timeframe"""
        reverse = {v: k for k, v in cls.MAPPING.items() if len(k) <= 3}
        return reverse.get(db_tf, db_tf)

class AlphaSignal(Base):
    """
    Storage for raw factor values and computed alpha signals.
    Each row represents a factor snapshot for a specific stock at a specific time.
    """
    __tablename__ = "alpha_signals"
    
    id = Column(Integer, primary_key=True, index=True)
    # stock_data_id removed - signals can exist independently
    timestamp = Column(DateTime, nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    
    # Momentum Factors
    rsi = Column(Float, nullable=True)  # Relative Strength Index
    macd = Column(Float, nullable=True)  # MACD line value
    macd_signal = Column(Float, nullable=True)  # MACD signal line
    macd_divergence = Column(Float, nullable=True)  # MACD - Signal (divergence)
    
    # Volatility Factors
    atr = Column(Float, nullable=True)  # Average True Range
    bollinger_upper = Column(Float, nullable=True)  # Upper Bollinger Band
    bollinger_lower = Column(Float, nullable=True)  # Lower Bollinger Band
    bollinger_position = Column(Float, nullable=True)  # (close - lower) / (upper - lower)
    
    # Volume Factors
    vwap = Column(Float, nullable=True)  # Volume Weighted Average Price
    volume_sma = Column(Float, nullable=True)  # SMA of volume
    vwap_ratio = Column(Float, nullable=True)  # Current price / VWAP
    volume_ratio = Column(Float, nullable=True)  # Current volume / SMA volume
    
    # Composite Alpha Score (from ML model)
    alpha_score = Column(Float, nullable=True)  # Weighted factor score from Random Forest
    alpha_rank = Column(Integer, nullable=True)  # Rank among all stocks (1 = strongest)
    
    # Metadata
    model_version = Column(String(20), nullable=True)  # e.g., "v1.0", "v1.1"
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships - keep trade_decisions but remove stock_data
    trade_decisions = relationship("TradeDecision", back_populates="alpha_signal", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_signal_symbol_timestamp', 'symbol', 'timestamp'),
        {'extend_existing': True}
    )
    
    def __repr__(self):
        return f"<AlphaSignal(symbol={self.symbol}, alpha_score={self.alpha_score}, timestamp={self.timestamp})>"


class TradeDecision(Base):
    """
    Log of trading decisions based on alpha signals.
    Tracks ML model confidence, action taken, and execution details.
    """
    __tablename__ = "trade_decisions"
    
    id = Column(Integer, primary_key=True, index=True)
    alpha_signal_id = Column(Integer, ForeignKey("alpha_signals.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Optional: which user triggered this
    
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Decision details
    action = Column(String(20), nullable=False)  # BUY, SELL, HOLD
    confidence = Column(Float, nullable=False)  # ML model confidence (0-1)
    quantity = Column(Integer, nullable=True)  # Shares to trade
    target_price = Column(Float, nullable=True)  # Suggested entry price
    stop_loss = Column(Float, nullable=True)  # Risk management level
    take_profit = Column(Float, nullable=True)  # Profit target
    
    # Execution tracking
    executed = Column(Boolean, default=False)
    execution_price = Column(Float, nullable=True)
    execution_timestamp = Column(DateTime, nullable=True)
    order_id = Column(String(50), nullable=True)  # Upstox order ID
    
    # Performance tracking (filled after exit)
    exit_price = Column(Float, nullable=True)
    exit_timestamp = Column(DateTime, nullable=True)
    pnl = Column(Float, nullable=True)  # Profit/Loss in rupees
    pnl_percent = Column(Float, nullable=True)  # Profit/Loss in percentage
    
    # Metadata
    strategy_version = Column(String(20), nullable=True)
    notes = Column(Text, nullable=True)  # Human-readable notes
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    alpha_signal = relationship("AlphaSignal", back_populates="trade_decisions")
    user = relationship("User")
    
    __table_args__ = (
        Index('idx_decision_symbol_timestamp', 'symbol', 'timestamp'),
        Index('idx_decision_executed', 'executed'),
        {'extend_existing': True}
    )
    
    def __repr__(self):
        return f"<TradeDecision(symbol={self.symbol}, action={self.action}, confidence={self.confidence:.2f})>"


class ETLLog(Base):
    """
    Audit trail for ETL pipeline operations.
    Tracks data ingestion jobs, errors, and data quality metrics.
    """
    __tablename__ = "etl_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Job identification
    job_type = Column(String(50), nullable=False)  # historical_load, live_ingest, backfill
    job_id = Column(String(100), nullable=True)  # Unique identifier for tracking
    
    # Data scope
    symbols = Column(JSON, nullable=True)  # List of symbols processed
    start_time = Column(DateTime, nullable=True)  # Data range start
    end_time = Column(DateTime, nullable=True)  # Data range end
    
    # Execution details
    status = Column(String(20), nullable=False)  # running, success, failed, partial
    records_fetched = Column(Integer, nullable=True)
    records_inserted = Column(Integer, nullable=True)
    records_updated = Column(Integer, nullable=True)
    records_skipped = Column(Integer, nullable=True)  # Duplicates
    
    # Performance metrics
    duration_seconds = Column(Float, nullable=True)
    api_calls = Column(Integer, nullable=True)
    rate_limit_hits = Column(Integer, nullable=True)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)  # Stack trace, failed symbols, etc.
    
    # Data quality metrics
    gaps_detected = Column(Integer, nullable=True)  # Missing data points
    outliers_detected = Column(Integer, nullable=True)  # Statistical outliers
    data_quality_score = Column(Float, nullable=True)  # 0-100
    
    # Metadata
    source = Column(String(20), nullable=False, default="upstox")
    triggered_by = Column(String(50), nullable=True)  # scheduler, manual, api
    
    __table_args__ = (
        Index('idx_etl_job_type_timestamp', 'job_type', 'timestamp'),
        Index('idx_etl_status', 'status'),
        {'extend_existing': True}
    )
    
    def __repr__(self):
        return f"<ETLLog(job_type={self.job_type}, status={self.status}, records={self.records_inserted})>"


class AlphaPrimeConfig(Base):
    """
    Configuration storage for AlphaPrime module.
    Allows dynamic parameter tuning without code changes.
    """
    __tablename__ = "alpha_prime_config"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    config_name = Column(String(50), nullable=False, unique=True)
    
    # Model parameters
    lookback_period = Column(Integer, default=30)  # Days for regime detection
    rebalance_frequency = Column(String(20), default="daily")  # daily, weekly, monthly
    
    # Factor weights (can be overridden by ML model)
    momentum_weight = Column(Float, default=0.33)
    volatility_weight = Column(Float, default=0.33)
    volume_weight = Column(Float, default=0.34)
    
    # Risk management
    max_position_size = Column(Float, default=0.05)  # 5% of capital per stock
    stop_loss_pct = Column(Float, default=0.02)  # 2% stop loss
    take_profit_pct = Column(Float, default=0.06)  # 6% take profit (3:1 ratio)
    
    # Execution parameters
    min_confidence = Column(Float, default=0.70)  # Minimum ML confidence to trade
    max_positions = Column(Integer, default=10)  # Maximum concurrent positions
    
    # Feature flags
    ml_enabled = Column(Boolean, default=True)
    auto_trade_enabled = Column(Boolean, default=False)
    paper_trade_mode = Column(Boolean, default=True)
    
    # Metadata
    is_active = Column(Boolean, default=True)
    version = Column(String(20), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<AlphaPrimeConfig(name={self.config_name}, version={self.version})>"
