"""
APF - Adaptive Price Forecast Schemas
Pydantic models for API request/response
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class ForecastRequest(BaseModel):
    """Request model for price forecast."""
    symbol: str = Field(..., description="Stock symbol (e.g., RELIANCE)")
    timeframe: str = Field(default="5m", description="Candle timeframe: 5m, 15m, 1h, 1d")
    horizon: int = Field(default=10, ge=1, le=50, description="Number of future candles to predict")


class ForecastResponse(BaseModel):
    """Response model for price forecast."""
    symbol: str
    timeframe: str
    horizon: Optional[int] = Field(default=None, description="Number of candles predicted")
    timestamps: List[str] = Field(default_factory=list, description="ISO datetime strings")
    actual: List[Optional[float]] = Field(default_factory=list, description="Historical actual prices")
    predicted: List[Optional[float]] = Field(default_factory=list, description="Predicted prices (null for historical)")
    upper_band: List[Optional[float]] = Field(default_factory=list, description="Upper confidence band")
    lower_band: List[Optional[float]] = Field(default_factory=list, description="Lower confidence band")
    confidence: float = Field(default=0.0, ge=0, le=1, description="Model confidence score")
    model_version: str = Field(default="apf_v1")
    data_source: str = Field(default="UNAVAILABLE", description="LIVE, DELAYED, or DB")
    last_trained: Optional[str] = Field(default=None, description="Last model training timestamp")
    status: Optional[str] = Field(default="success", description="Response status: success, no_data, error")
    message: Optional[str] = Field(default=None, description="Error or status message")


class ForecastError(BaseModel):
    """Error response for forecast failures."""
    error: str
    detail: str
    symbol: str
    data_available: bool = False


# ============================================================================
# Algorithm Registry Schemas
# ============================================================================

class AlgorithmInfo(BaseModel):
    """Algorithm metadata for API response."""
    id: str = Field(..., description="Unique algorithm identifier")
    name: str = Field(..., description="Display name")
    version: str = Field(..., description="Version string")
    type: str = Field(..., description="Type: ensemble, ml, dl, statistical")
    is_pro: bool = Field(default=False, description="Whether this model requires PRO subscription")
    recommended: bool = Field(default=False, description="Is this the default/recommended algorithm")
    supports_confidence_bands: bool = Field(default=True)
    supported_timeframes: List[str] = Field(default_factory=lambda: ["1m", "5m", "15m", "30m", "1h", "1d"])
    max_horizon: int = Field(default=50)
    description: str = Field(default="")
    features_used: List[str] = Field(default_factory=list, description="Features used by this algorithm")
    estimated_latency_ms: int = Field(default=500, description="Estimated prediction latency in ms")
    training_status: str = Field(default="READY", description="READY, EXPIRED, or UNTRAINED")
    last_trained: Optional[str] = Field(default=None)


class AlgorithmListResponse(BaseModel):
    """Response for GET /algorithms endpoint."""
    algorithms: List[AlgorithmInfo]
    count: int


class ForecastRunRequest(BaseModel):
    """Request model for POST /forecast/run."""
    symbol: str = Field(..., min_length=1, description="Stock symbol (e.g., RELIANCE)")
    exchange: str = Field(default="NSE", description="Stock exchange")
    timeframe: str = Field(default="5m", description="Candle timeframe")
    horizon: int = Field(default=10, ge=5, le=50, description="Prediction horizon (candles)")
    algorithm_id: str = Field(..., description="Algorithm to use")
    confidence_level: float = Field(default=0.95, ge=0.5, le=0.99, description="Confidence interval level")
    include_confidence_bands: bool = Field(default=True)


class ForecastMetrics(BaseModel):
    """Metrics from forecast run."""
    confidence_score: float = Field(ge=0, le=1, description="Model confidence 0-1")
    predicted_move_pct: float = Field(description="Predicted price change percentage")
    volatility_label: str = Field(description="Low, Medium, or High")
    model_latency_ms: int = Field(description="Actual prediction latency in ms")


class ForecastCandle(BaseModel):
    """Single candle in forecast output."""
    timestamp: str
    close: float
    upper: Optional[float] = None
    lower: Optional[float] = None
    is_forecast: bool = False


class AlgorithmMetadata(BaseModel):
    """Algorithm info in response."""
    id: str
    name: str
    version: str


class ForecastRunResponse(BaseModel):
    """Response model for POST /forecast/run."""
    request_id: str = Field(..., description="Unique request identifier")
    symbol: str
    exchange: str
    timeframe: str
    horizon: int
    algorithm: AlgorithmMetadata
    generated_at: str = Field(description="ISO timestamp of generation")
    candles_input: List[Dict[str, Any]] = Field(description="Historical OHLCV candles used")
    forecast: List[ForecastCandle] = Field(description="Predicted candles")
    confidence_bands: Optional[Dict[str, List[float]]] = Field(default=None, description="Upper/lower band arrays")
    metrics: ForecastMetrics
    warnings: List[str] = Field(default_factory=list)
    error: Optional[str] = Field(default=None)
