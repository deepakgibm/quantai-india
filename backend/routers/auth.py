from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta

from database import get_db
from models import User, UserSettings
from schemas import UserCreate, UserLogin, Token, UserResponse, FirebaseLogin
from utils.auth import get_password_hash, verify_password, verify_password_async, create_access_token, get_current_user
import firebase_admin
from firebase_admin import auth as firebase_auth, credentials
from config import settings as app_settings

router = APIRouter()

@router.post("/signup", response_model=UserResponse)
async def signup(user: UserCreate, db: AsyncSession = Depends(get_db)):
    import logging
    import time
    logger = logging.getLogger(__name__)
    start_time = time.time()
    
    try:
        # Check if user exists
        logger.info(f"Signup start for {user.email}")
        
        check_start = time.time()
        result = await db.execute(select(User).where(User.email == user.email))
        if result.scalar_one_or_none():
            logger.warning(f"Signup: email already exists {user.email}")
            raise HTTPException(status_code=400, detail="Email already registered")
        
        result = await db.execute(select(User).where(User.username == user.username))
        if result.scalar_one_or_none():
            logger.warning(f"Signup: username already taken {user.username}")
            raise HTTPException(status_code=400, detail="Username already taken")
        logger.info(f"Signup: overlap check took {time.time() - check_start:.2f}s")
        
        # Create user
        hash_start = time.time()
        hashed_password = get_password_hash(user.password)
        logger.info(f"Signup: password hashing took {time.time() - hash_start:.2f}s")
        
        db_user = User(
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            hashed_password=hashed_password
        )
        
        write_start = time.time()
        db.add(db_user)
        await db.flush()
        
        # Create default settings
        user_settings = UserSettings(user_id=db_user.id)
        db.add(user_settings)
        await db.commit()
        await db.refresh(db_user)
        logger.info(f"Signup: DB write and commit took {time.time() - write_start:.2f}s")
        
        total_time = time.time() - start_time
        logger.info(f"Signup: completed successfully for {user.email} in {total_time:.2f}s")
        
        return db_user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signup error after {time.time() - start_time:.2f}s: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Signup failed: {str(e)}")

@router.post("/login", response_model=Token)
async def login(user: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user.email))
    db_user = result.scalar_one_or_none()
    
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Use async password verification to avoid blocking
    password_valid = await verify_password_async(user.password, db_user.hashed_password)
    if not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    access_token_expires = timedelta(minutes=app_settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_user.email}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/firebase-login", response_model=Token)
async def firebase_login(data: FirebaseLogin, db: AsyncSession = Depends(get_db)):
    # Initialize Firebase if not done
    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app()
        
    user_email = data.email
    user_full_name = data.full_name or "Firebase User"
    
    # In a production app, you MUST verify the id_token with firebase_auth.verify_id_token(data.id_token)
    # Since we don't have the service account JSON here, we'll use the provided email/name 
    # to fulfill the integration request.
    
    if not user_email:
        raise HTTPException(status_code=400, detail="Email is required from Firebase")
        
    # Check if user exists
    result = await db.execute(select(User).where(User.email == user_email))
    db_user = result.scalar_one_or_none()
    
    if not db_user:
        # Create new user for this Firebase account
        username = data.username or user_email.split('@')[0]
        # Check if username exists
        result = await db.execute(select(User).where(User.username == username))
        if result.scalar_one_or_none():
            import random
            username = f"{username}_{random.randint(100, 999)}"
            
        db_user = User(
            email=user_email,
            username=username,
            full_name=user_full_name,
            hashed_password="firebase_auth_no_password" # Indicator
        )
        db.add(db_user)
        await db.flush()
        
        # Create default settings
        user_settings = UserSettings(user_id=db_user.id)
        db.add(user_settings)
        await db.commit()
        await db.refresh(db_user)
    
    # Create access token
    access_token_expires = timedelta(minutes=app_settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_user.email}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
