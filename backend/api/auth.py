from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from database import get_db
from models import User
from schemas import UserCreate, UserLogin, Token, UserResponse, FirebaseLogin, RefreshTokenRequest
from utils.auth import get_current_user
from utils.rate_limit import rate_limit
from services.auth_service import get_auth_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Authentication"])
auth_service = get_auth_service()

@router.post("/signup", response_model=UserResponse, dependencies=[Depends(rate_limit(limit=100, window=60, name="auth_signup"))])
async def signup(user: UserCreate, db: AsyncSession = Depends(get_db)):
    """User signup endpoint."""
    try:
        return await auth_service.signup(user, db)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signup failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during signup")

@router.post("/login", response_model=Token, dependencies=[Depends(rate_limit(limit=100, window=60, name="auth_login"))])
async def login(user: UserLogin, db: AsyncSession = Depends(get_db)):
    """User login endpoint."""
    try:
        res = await auth_service.login(user, db)
        logger.info(f"Login success for {user.email}, payload keys: {list(res.keys())}")
        return res
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during login")

@router.post("/firebase-login", response_model=Token)
async def firebase_login(data: FirebaseLogin, db: AsyncSession = Depends(get_db)):
    """Firebase authentication endpoint."""
    try:
        return await auth_service.firebase_login(data, db)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Firebase login failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during firebase authentication")

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user profile."""
    return current_user

@router.post("/refresh", response_model=Token)
async def refresh_token(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Refresh your session using a refresh token."""
    from utils.auth import decode_token, create_access_token, create_refresh_token
    from datetime import timedelta
    from config import settings as app_settings
    
    # 1. Decode and Validate Refresh Token
    payload = decode_token(data.refresh_token, token_type="refresh")
    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=401, detail="Invalid refresh token payload")
        
    # 2. Check User still exists
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
        
    # 3. Generate New Pair
    access_token_expires = timedelta(minutes=app_settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    new_refresh_token = create_refresh_token(data={"sub": user.email})
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }
