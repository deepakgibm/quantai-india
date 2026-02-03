from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    # Deprecated fields, moving to BrokerCredentials but keeping for backward compat if needed
    is_upstox_connected = Column(Boolean, default=False)
    upstox_access_token = Column(String, nullable=True)
    upstox_refresh_token = Column(String, nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    subscription_level = Column(String, default="FREE") # FREE, PRO, ELITE
    created_at = Column(DateTime, default=datetime.utcnow)
    
    orders = relationship("Order", back_populates="user")
    algorithms = relationship("Algorithm", back_populates="user")
    settings = relationship("UserSettings", back_populates="user", uselist=False)
    broker_credentials = relationship("BrokerCredentials", back_populates="user")
    positions = relationship("Position", back_populates="user")
    holdings = relationship("Holding", back_populates="user")
    risk_config = relationship("RiskConfig", back_populates="user", uselist=False)
    scanner_presets = relationship("ScannerPreset", back_populates="user")

class ScannerPreset(Base):
    __tablename__ = "scanner_presets"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    indices = Column(JSON) # List of strings
    timeframe = Column(String)
    strategies = Column(JSON) # List of strings
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="scanner_presets")

class BrokerCredentials(Base):
    __tablename__ = "broker_credentials"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    broker = Column(String) # upstox, zerodha
    api_key = Column(String)
    api_secret = Column(String)
    access_token = Column(String)
    refresh_token = Column(String)
    is_active = Column(Boolean, default=True)
    user = relationship("User", back_populates="broker_credentials")

class Position(Base):
    __tablename__ = "positions"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    symbol = Column(String)
    quantity = Column(Integer)
    avg_price = Column(Float)
    product = Column(String) # I/D
    pnl = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="positions")

class Holding(Base):
    __tablename__ = "holdings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    symbol = Column(String)
    quantity = Column(Integer)
    avg_price = Column(Float)
    current_price = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="holdings")

class BacktestResult(Base):
    __tablename__ = "backtest_results"
    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String, unique=True, index=True)
    strategy_name = Column(String)
    symbol = Column(String, index=True)
    timeframe = Column(String)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    initial_capital = Column(Float)
    final_capital = Column(Float)
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)
    total_trades = Column(Integer)
    win_rate = Column(Float)
    metrics = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class RiskConfig(Base):
    __tablename__ = "risk_config"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    max_daily_loss = Column(Float)
    max_position_size = Column(Float)
    max_open_positions = Column(Integer)
    user = relationship("User", back_populates="risk_config")

class Algorithm(Base):
    __tablename__ = "algorithms"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    description = Column(String)
    is_active = Column(Boolean, default=False)
    performance = Column(Float, default=0.0)
    config = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="algorithms")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    symbol = Column(String)
    order_type = Column(String)
    quantity = Column(Integer)
    price = Column(Float)
    status = Column(String)
    order_id = Column(String, unique=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="orders")

class UserSettings(Base):
    __tablename__ = "user_settings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    max_capital = Column(Float, default=1000000)
    max_risk_per_trade = Column(Float, default=2.0)
    auto_trade = Column(Boolean, default=False)
    notifications = Column(Boolean, default=True)
    user = relationship("User", back_populates="settings")




class DailyTopGainersSnapshot(Base):
    """
    Stores official post-market top gainers/losers snapshot.
    
    Populated by ETL at 15:40 IST using Upstox REST API.
    Immutable per trading day - source of truth for after-hours display.
    """
    __tablename__ = "daily_top_gainers_snapshot"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    trade_date = Column(DateTime, nullable=False, index=True)
    symbol = Column(String, nullable=False)
    company_name = Column(String, nullable=True)
    close_price = Column(Float, nullable=False)
    prev_close = Column(Float, nullable=False)
    change = Column(Float, nullable=False)
    change_percent = Column(Float, nullable=False)
    volume = Column(Integer, nullable=True)
    rank = Column(Integer, nullable=False)  # 1-10 for gainers, -1 to -10 for losers
    category = Column(String, default="GAINER")  # GAINER or LOSER
    data_source = Column(String, default="UPSTOX")
    created_at = Column(DateTime, default=datetime.utcnow)
