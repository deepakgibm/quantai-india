from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, ForeignKey
from database import Base
from datetime import datetime

class InstitutionalPattern(Base):
    __tablename__ = "institutional_patterns"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), index=True, nullable=False)
    pattern_type = Column(String(50), nullable=False)  # 'VCP', 'CUP_AND_HANDLE', 'DOUBLE_BOTTOM', 'FLAT_BASE'
    confidence_score = Column(Float, default=0.0)
    breakout_pivot = Column(Float, nullable=True)
    breakout_status = Column(String(50), default="Pending")  # 'Pending', 'Confirmed', 'Failed'
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class VcpScore(Base):
    __tablename__ = "vcp_scores"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), index=True, unique=True, nullable=False)
    current_price = Column(Float, nullable=False)
    distance_from_52w_high = Column(Float, nullable=False)
    vcp_score = Column(Float, nullable=False)  # 0-100
    num_contractions = Column(Integer, default=0)
    latest_contraction_pct = Column(Float, default=0.0)
    volume_dry_up_pct = Column(Float, default=0.0)
    atr_contraction_pct = Column(Float, default=0.0)
    breakout_pivot = Column(Float, nullable=True)
    breakout_ready = Column(Boolean, default=False)
    category = Column(String(50), default="Ignore")  # Elite, Excellent, Good, Watchlist, Ignore
    trend_quality = Column(Float, default=0.0)
    volume_dry_up = Column(Float, default=0.0)
    volatility_compression = Column(Float, default=0.0)
    proximity_to_pivot = Column(Float, default=0.0)
    relative_strength = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TrendTemplateScore(Base):
    __tablename__ = "trend_template_scores"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), index=True, unique=True, nullable=False)
    trend_template_score = Column(Float, nullable=False)  # 0-7 or 0-100
    price_above_sma50 = Column(Boolean, default=False)
    price_above_sma150 = Column(Boolean, default=False)
    price_above_sma200 = Column(Boolean, default=False)
    sma50_above_sma150 = Column(Boolean, default=False)
    sma150_above_sma200 = Column(Boolean, default=False)
    price_above_52w_low_by_30pct = Column(Boolean, default=False)
    price_within_25pct_of_52w_high = Column(Boolean, default=False)
    sma50 = Column(Float, nullable=True)
    sma150 = Column(Float, nullable=True)
    sma200 = Column(Float, nullable=True)
    distance_to_52w_high = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class RelativeStrengthRanking(Base):
    __tablename__ = "relative_strength_rankings"
    
    id = Column(Integer, primary_key=True, index=True)
    rank = Column(Integer, index=True)
    symbol = Column(String(20), index=True, unique=True, nullable=False)
    rs_score = Column(Float, nullable=False)
    return_6m = Column(Float, default=0.0)
    return_3m = Column(Float, default=0.0)
    return_1m = Column(Float, default=0.0)
    sector_rank = Column(Integer, nullable=True)
    industry_rank = Column(Integer, nullable=True)
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    market_cap = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class BreakoutCandidate(Base):
    __tablename__ = "breakout_candidates"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), index=True, unique=True, nullable=False)
    breakout_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    breakout_pct = Column(Float, default=0.0)
    volume_surge_pct = Column(Float, default=0.0)
    confirmation_status = Column(String(50), default="Pending")  # "Confirmed", "Pending"
    breakout_type = Column(String(50), nullable=True)  # "Resistance", "Volume", "Range"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DarvasBox(Base):
    __tablename__ = "darvas_boxes"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), index=True, unique=True, nullable=False)
    box_top = Column(Float, nullable=False)
    box_bottom = Column(Float, nullable=False)
    days_inside_box = Column(Integer, default=0)
    breakout_status = Column(String(50), default="Inside")  # "Inside Box", "Bullish Breakout", "Bearish Breakdown"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PatternHistory(Base):
    __tablename__ = "pattern_history"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), index=True, nullable=False)
    pattern_type = Column(String(50), nullable=False)
    detection_date = Column(DateTime, default=datetime.utcnow)
    details = Column(JSON, nullable=True)
    confidence_score = Column(Float, default=0.0)
    status = Column(String(50), default="Active")  # "Active", "Triggered", "Failed"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
