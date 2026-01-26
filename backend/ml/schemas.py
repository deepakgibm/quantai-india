"""
APF - Adaptive Price Forecast Schemas
Pydantic models for API request/response
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class ForecastRequest(BaseModel):
    """Request model for price forecast."""
    symbol: str = Field(..., description="Stock symbol (e.g., RELIANCE)")
    timeframe: str = Field(default="5m", description="Candle timeframe: 5m, 15m, 1h, 1d")
    horizon: int = Field(default=10, ge=1, le=50, description="Number of future candles to predict")


class ForecastResponse(BaseModel):
    """Response model for price forecast."""
    symbol: str
    timeframe: str
    timestamps: List[str] = Field(description="ISO datetime strings")
    actual: List[Optional[float]] = Field(description="Historical actual prices")
    predicted: List[Optional[float]] = Field(description="Predicted prices (null for historical)")
    upper_band: List[Optional[float]] = Field(description="Upper confidence band")
    lower_band: List[Optional[float]] = Field(description="Lower confidence band")
    confidence: float = Field(ge=0, le=1, description="Model confidence score")
    model_version: str = Field(default="apf_v1")
    data_source: str = Field(description="LIVE, DELAYED, or DB")
    last_trained: Optional[str] = Field(default=None, description="Last model training timestamp")


class ForecastError(BaseModel):
    """Error response for forecast failures."""
    error: str
    detail: str
    symbol: str
    data_available: bool = False
