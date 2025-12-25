from pydantic import BaseModel, EmailStr
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
    symbol: str
    order_type: str
    quantity: int
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
    name: str
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
    created_at: datetime
    
    class Config:
        from_attributes = True

# AI Schemas
class AIPromptRequest(BaseModel):
    prompt: str

class AIPromptResponse(BaseModel):
    response: str
    suggested_stocks: Optional[List[Dict[str, Any]]] = []
    strategy: Optional[Dict[str, Any]] = {}

class AICommandRequest(BaseModel):
    command: str

class AICommandResponse(BaseModel):
    action: str
    params: Dict[str, Any]
    message: str

# Market Data
class MarketData(BaseModel):
    symbol: str
    price: float
    change: float
    change_percent: float
    volume: int

# Dashboard Stats
class DashboardStats(BaseModel):
    total_pnl: float
    daily_pnl: float
    capital_used: float
    total_capital: float
    active_algorithms: int
    win_rate: float
    total_trades: int
