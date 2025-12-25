"""
Risk Management Database Models
"""
from sqlalchemy import Boolean, Column, Integer, String, Float, DateTime, ForeignKey, Date, Text, JSON
from sqlalchemy.sql import func
from database import Base

# Import RiskConfig and Position from models.py to avoid duplicate table definitions
from models import RiskConfig, Position


class StopLossHistory(Base):
    """Stop-loss adjustment history"""
    __tablename__ = "stop_loss_history"
    
    id = Column(Integer, primary_key=True, index=True)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=False)
    
    stop_price = Column(Float, nullable=False)
    stop_type = Column(String(50))  # 'initial', 'trailing', 'time_based', 'volatility'
    highest_price = Column(Float)  # For trailing stops
    atr_value = Column(Float)  # ATR at time of adjustment
    reason = Column(Text)
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class PortfolioMetrics(Base):
    """Daily portfolio risk metrics snapshot"""
    __tablename__ = "portfolio_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Portfolio values
    total_value = Column(Float, nullable=False)
    cash = Column(Float, nullable=False)
    positions_value = Column(Float, nullable=False)
    
    # P&L
    daily_pnl = Column(Float)
    cumulative_pnl = Column(Float)
    
    # Risk metrics
    drawdown_percent = Column(Float)
    max_drawdown_percent = Column(Float)
    portfolio_heat = Column(Float)  # Total % at risk
    var_95 = Column(Float)  # Value at Risk (95% confidence)
    expected_shortfall = Column(Float)  # Conditional VaR
    
    # Performance metrics
    sharpe_ratio = Column(Float)
    sortino_ratio = Column(Float)
    win_rate = Column(Float)
    
    # Positions
    num_positions = Column(Integer, default=0)
    num_long = Column(Integer, default=0)
    num_short = Column(Integer, default=0)
    
    # Date
    date = Column(Date, nullable=False, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RiskEvent(Base):
    """Risk management events and alerts"""
    __tablename__ = "risk_events"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    event_type = Column(String(50), nullable=False)  # 'stop_loss', 'position_limit', 'drawdown_warning', etc.
    severity = Column(String(20), default='info')  # 'info', 'warning', 'critical'
    
    symbol = Column(String(20))
    description = Column(Text)
    action_taken = Column(Text)
    event_metadata = Column(JSON)  # Additional event data
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
