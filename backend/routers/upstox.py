from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import requests

from database import get_db
from models import User
from schemas import UpstoxAuthResponse, UpstoxCallback, UpstoxTokenResponse
from utils.auth import get_current_user
from config import settings

router = APIRouter()

@router.get("/auth-url", response_model=UpstoxAuthResponse)
async def get_upstox_auth_url(current_user: User = Depends(get_current_user)):
    auth_url = f"https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id={settings.UPSTOX_API_KEY}&redirect_uri={settings.UPSTOX_REDIRECT_URI}"
    return {"auth_url": auth_url}

@router.post("/callback", response_model=UpstoxTokenResponse)
async def upstox_callback(
    callback: UpstoxCallback,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Exchange code for access token
    token_url = "https://api.upstox.com/v2/login/authorization/token"
    payload = {
        "code": callback.code,
        "client_id": settings.UPSTOX_API_KEY,
        "client_secret": settings.UPSTOX_API_SECRET,
        "redirect_uri": settings.UPSTOX_REDIRECT_URI,
        "grant_type": "authorization_code"
    }
    
    try:
        response = requests.post(token_url, data=payload)
        response.raise_for_status()
        token_data = response.json()
        
        # Save tokens to user
        current_user.upstox_access_token = token_data.get("access_token")
        current_user.is_upstox_connected = True
        await db.commit()
        
        return {
            "access_token": token_data.get("access_token"),
            "message": "Upstox connected successfully"
        }
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Upstox authentication failed: {str(e)}")

@router.get("/portfolio")
async def get_portfolio(current_user: User = Depends(get_current_user)):
    if not current_user.is_upstox_connected:
        # Return mock portfolio when not connected
        return {
            "status": "success",
            "data": [
                {"symbol": "RELIANCE", "quantity": 50, "avg_price": 2440.0, "ltp": 2456.0, "pnl": 800},
                {"symbol": "HDFCBANK", "quantity": 25, "avg_price": 1455.0, "ltp": 1450.0, "pnl": -125},
                {"symbol": "INFY", "quantity": 100, "avg_price": 1580.0, "ltp": 1585.0, "pnl": 500},
            ],
            "message": "Mock portfolio (Upstox not connected)"
        }
    
    headers = {
        "Authorization": f"Bearer {current_user.upstox_access_token}",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get("https://api.upstox.com/v2/portfolio/long-term-holdings", headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch portfolio: {str(e)}")

@router.get("/positions")
async def get_positions(current_user: User = Depends(get_current_user)):
    if not current_user.is_upstox_connected:
        raise HTTPException(status_code=400, detail="Upstox not connected")
    
    headers = {
        "Authorization": f"Bearer {current_user.upstox_access_token}",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get("https://api.upstox.com/v2/portfolio/short-term-positions", headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch positions: {str(e)}")

@router.get("/market-quote/{symbol}")
async def get_market_quote(symbol: str, current_user: User = Depends(get_current_user)):
    if not current_user.is_upstox_connected:
        raise HTTPException(status_code=400, detail="Upstox not connected")
    
    headers = {
        "Authorization": f"Bearer {current_user.upstox_access_token}",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(f"https://api.upstox.com/v2/market-quote/ltp?symbol={symbol}", headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch market quote: {str(e)}")
