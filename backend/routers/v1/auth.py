from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict

from database import get_db
from models import User
from schemas import UserCreate, UserLogin, Token, UserResponse, FirebaseLogin
from utils.auth import get_current_user
from services.auth_service import get_auth_service

router = APIRouter(prefix="/auth", tags=["Authentication (v1)"])
auth_service = get_auth_service()

@router.post("/signup", response_model=UserResponse)
async def signup(user: UserCreate, db: AsyncSession = Depends(get_db)):
    try:
        return await auth_service.signup(user, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login", response_model=Token)
async def login(user: UserLogin, db: AsyncSession = Depends(get_db)):
    try:
        return await auth_service.login(user, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/firebase-login", response_model=Token)
async def firebase_login(data: FirebaseLogin, db: AsyncSession = Depends(get_db)):
    try:
        return await auth_service.firebase_login(data, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
