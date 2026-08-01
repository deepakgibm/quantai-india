from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
import logging
from database import get_db
from models import User
from schemas import UpstoxAuthResponse, UpstoxCallback, UpstoxTokenResponse
from utils.auth import get_current_user
from config import settings

logger = logging.getLogger(__name__)

from utils.rate_limit import rate_limit

from services.upstox_client import get_upstox_client_dependency, UpstoxClient

router = APIRouter(
    tags=["Upstox Integrations"],
    dependencies=[Depends(rate_limit(60, 60, "upstox"))]
)

@router.get("/status")
async def get_upstox_status(client: UpstoxClient = Depends(get_upstox_client_dependency)):
    """
    Get Upstox connection status.
    Returns connection state without requiring authentication.
    """
    try:
        # Check if client has access token
        has_token = hasattr(client, 'access_token') and client.access_token is not None
        
        return {
            "status": "success",
            "upstox": {
                "connected": has_token,
                "api_available": True,
                "service": "operational"
            },
            "message": "Upstox is connected" if has_token else "Upstox not connected"
        }
    except Exception as e:
        return {
            "status": "error",
            "upstox": {
                "connected": False,
                "api_available": False,
                "service": "unavailable"
            },
            "message": f"Upstox service error: {str(e)}"
        }

@router.get("/auth-url", response_model=UpstoxAuthResponse)
async def get_upstox_auth_url(current_user: User = Depends(get_current_user)):
    auth_url = f"https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id={settings.UPSTOX_API_KEY}&redirect_uri={settings.UPSTOX_REDIRECT_URI}"
    return {"auth_url": auth_url}


@router.get("/connect-url")
async def get_upstox_connect_url():
    """Get Upstox connection URL - public endpoint for initiating OAuth."""
    auth_url = f"https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id={settings.UPSTOX_API_KEY}&redirect_uri={settings.UPSTOX_REDIRECT_URI}"
    return {"auth_url": auth_url, "message": "Use this URL to connect to Upstox"}


@router.get("/user-profile")
async def get_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile with upstox status"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "username": current_user.username,
        "upstox_connected": current_user.is_upstox_connected,
        "upstox_id": getattr(current_user, "upstox_id", None)
    }

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
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(token_url, data=payload)
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
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=400, detail=f"Upstox auth failed: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Upstox authentication failed: {str(e)}")

@router.get("/portfolio")
async def get_portfolio(current_user: User = Depends(get_current_user)):
    if not current_user.is_upstox_connected:
        return {
            "status": "not_connected",
            "message": "Upstox broker is not connected. Please login via /api/upstox/auth-url.",
            "data": None
        }
    
    from services.upstox_client import UpstoxClient
    client = UpstoxClient(access_token=current_user.upstox_access_token)
    try:
        response = await client._make_request("GET", "/portfolio/long-term-holdings")
        return response
    except httpx.HTTPStatusError as e:
        return {
            "status": "error",
            "message": f"Failed to fetch portfolio: {e.response.text}",
            "data": None
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to fetch portfolio: {str(e)}",
            "data": None
        }
    finally:
        await client.aclose()

@router.get("/positions")
async def get_positions(current_user: User = Depends(get_current_user)):
    if not current_user.is_upstox_connected:
        return {
            "status": "not_connected",
            "message": "Upstox broker is not connected. Please login via /api/upstox/auth-url.",
            "data": None
        }
    
    from services.upstox_client import UpstoxClient
    client = UpstoxClient(access_token=current_user.upstox_access_token)
    try:
        response = await client._make_request("GET", "/portfolio/short-term-positions")
        return response
    except httpx.HTTPStatusError as e:
        return {
            "status": "error",
            "message": f"Failed to fetch positions: {e.response.text}",
            "data": None
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to fetch positions: {str(e)}",
            "data": None
        }
    finally:
        await client.aclose()

@router.get("/market-quote/{symbol}")
async def get_market_quote(symbol: str, current_user: User = Depends(get_current_user)):
    try:
        from services.price_manager import get_price_service
        price_svc = get_price_service()
        price_data = await price_svc.get_price(symbol)
        
        # Format response to match the expected Upstox structure for client compatibility
        return {
            "status": "success",
            "data": {
                f"NSE_EQ:{symbol.upper()}": {
                    "last_price": price_data.get("ltp", 0.0),
                    "close_price": price_data.get("previous_close", 0.0),
                    "previous_close": price_data.get("previous_close", 0.0),
                    "volume": price_data.get("volume", 0),
                    "timestamp": price_data.get("timestamp"),
                    "price_source": price_data.get("source")
                }
            }
        }
    except Exception as e:
        logger.error(f"Failed to resolve market quote for {symbol}: {e}")
        return {
            "status": "error",
            "symbol": symbol,
            "message": f"Failed to fetch market quote: {str(e)}",
            "data": None
        }
