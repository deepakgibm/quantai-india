"""
AI Model Registry - Database Models
Tracks trained ML models, their versions, and performance metrics.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Boolean, Index, UniqueConstraint
from database import Base
from datetime import datetime

class AIModelRegistry(Base):
    """
    Registry for all trained AI models.
    Allows the system to discover which models are ready for specific symbols/timeframes.
    """
    __tablename__ = "ai_model_registry"
    
    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(String(50), nullable=False, index=True)  # e.g., 'xgboost_fast', 'adaptive_ensemble_v2'
    version = Column(String(20), nullable=False)  # e.g., '1.0.2'
    
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False, index=True)
    
    status = Column(String(20), default="READY")  # READY, EXPIRED, FAILED, TRAINING
    is_pro = Column(Boolean, default=False)  # Whether this model requires PRO subscription
    
    artifact_path = Column(String(255), nullable=True)  # Path to saved model weights
    
    # Performance metrics
    mse = Column(Float, nullable=True)
    mae = Column(Float, nullable=True)
    r2_score = Column(Float, nullable=True)
    custom_metrics = Column(JSON, nullable=True)  # Additional metrics like quantile loss
    
    trained_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('model_id', 'symbol', 'timeframe', name='uq_model_symbol_tf'),
        Index('idx_model_lookup', 'model_id', 'symbol', 'timeframe'),
        Index('idx_model_status', 'status'),
        {'extend_existing': True}
    )
    
    def __repr__(self):
        return f"<AIModelRegistry(model={self.model_id}, symbol={self.symbol}, status={self.status})>"
