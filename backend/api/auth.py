from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from database import get_db
from models import User
from schemas import UserCreate, UserLogin, Token, UserResponse, FirebaseLogin
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
        return await auth_service.login(user, db)
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
