from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: str

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class FirebaseLogin(BaseModel):
    id_token: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    username: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(UserBase):
    id: int
    is_active: bool = True
    is_upstox_connected: bool = False
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Upstox Schemas
class UpstoxAuthResponse(BaseModel):
    auth_url: str

class UpstoxCallback(BaseModel):
    code: str

class UpstoxTokenResponse(BaseModel):
    access_token: str
    message: str

# Order Schemas
class OrderCreate(BaseModel):
    symbol: str = Field(..., min_length=1, description="Stock Symbol")
    order_type: str
    quantity: int = Field(..., gt=0)
    price: Optional[float] = None

class OrderResponse(BaseModel):
    id: int
    symbol: str
    order_type: str
    quantity: int
    price: Optional[float]
    status: str
    timestamp: datetime
    
    class Config:
        from_attributes = True

# Algorithm Schemas
class AlgorithmCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: str
    config: Dict[str, Any]

class AlgorithmUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None

class AlgorithmResponse(BaseModel):
    id: int
    name: str
    description: str
    is_active: bool
    performance: float
    config: Dict[str, Any]
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# AI Schemas
class AIPromptRequest(BaseModel):
    prompt: str = Field(..., min_length=5)

class AIPromptResponse(BaseModel):
    status: str
    suggested_stocks: List[Dict[str, Any]]

class AICommandRequest(BaseModel):
    command: str = Field(..., min_length=1)

class AICommandResponse(BaseModel):
    action: str
    params: Dict[str, Any]
    message: str

# Scanner Schemas
class ScannerStock(BaseModel):
    symbol: str
    name: str
    score: Optional[int] = 0
    strength: Optional[int] = 0
    current_price: Optional[float] = 0.0
    entry_price: Optional[float] = None
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    change_pct: Optional[float] = 0.0
    volume_ratio: Optional[float] = 0.0
    reason: Optional[str] = ""
    indicators: Optional[Dict[str, Any]] = {}
    breakout_type: Optional[str] = None
    trend: Optional[str] = None
    action: Optional[str] = None

class ScannerResponse(BaseModel):
    status: str
    count: int
    stocks: List[ScannerStock]
    scan_type: str
    description: str
    buy_signals: Optional[List[ScannerStock]] = []
    sell_signals: Optional[List[ScannerStock]] = []
    error_code: Optional[str] = None
    message: Optional[str] = None

class MarketAnalysisResponse(BaseModel):
    status: str
    analysis: str
    sentiment: str
    trend: str
    top_sectors: List[str]
    stocks_to_watch: List[str]
    timestamp: str
    retry_after_seconds: Optional[int] = None

# Market Data
class MarketData(BaseModel):
    symbol: str
    price: float
    change: float
    change_percent: float
    volume: int

class InstrumentResponse(BaseModel):
    symbol: str
    name: str
    exchange: str

class InstrumentsListResponse(BaseModel):
    status: str
    instruments: List[InstrumentResponse]
    count: int

class TopMover(BaseModel):
    symbol: str
    price: float
    change: float

class GainersLosersResponse(BaseModel):
    ticker: str
    change: float
    color: str
    price: float

class MarketIndex(BaseModel):
    name: str
    value: float
    change: float
    percent: float
    source: str
    stale: Optional[bool] = False
    timestamp: Optional[str] = None

# Dashboard Stats
class DashboardStats(BaseModel):
    total_pnl: float
    daily_pnl: float
    capital_used: float
    total_capital: float
    active_algorithms: int
    win_rate: float
    total_trades: int
