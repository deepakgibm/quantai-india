from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from database import get_db
from models import User, UserSettings
from schemas import UserCreate, UserLogin, Token, UserResponse, FirebaseLogin
from utils.auth import get_password_hash, verify_password, verify_password_async, create_access_token, get_current_user
from utils.rate_limit import rate_limit
import firebase_admin
from firebase_admin import auth as firebase_auth, credentials
from config import settings as app_settings

router = APIRouter()

@router.post("/signup", response_model=UserResponse, dependencies=[Depends(rate_limit(limit=100, window=60, name="auth_signup"))])
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

@router.post("/login", response_model=Token, dependencies=[Depends(rate_limit(limit=100, window=60, name="auth_login"))])
async def login(user: UserLogin, db: AsyncSession = Depends(get_db)):
    import logging
    import traceback
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Login attempt for {user.email}")
        result = await db.execute(select(User).where(User.email == user.email))
        db_user = result.scalar_one_or_none()
        
        if not db_user:
            logger.warning(f"Login failed: User not found {user.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        # Check for account lockout
        if db_user.locked_until and db_user.locked_until > datetime.utcnow():
            logger.warning(f"Login attempt on locked account: {user.email}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account is locked. Try again after {db_user.locked_until.strftime('%H:%M:%S')} UTC"
            )

        # Use async password verification to avoid blocking
        try:
            password_valid = await verify_password_async(user.password, db_user.hashed_password)
        except Exception as e:
            logger.error(f"Password verification CRASHED for {user.email}: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Auth engine error: {str(e)[:100]}")

        if not password_valid:
            # Increment failed attempts
            db_user.failed_login_attempts = (db_user.failed_login_attempts or 0) + 1
            if db_user.failed_login_attempts >= 5:
                db_user.locked_until = datetime.utcnow() + timedelta(minutes=15)
                logger.error(f"Account LOCKED for {user.email} after {db_user.failed_login_attempts} failed attempts")
            
            await db.commit()
            
            logger.warning(f"Login failed: Incorrect password for {user.email} (Attempt {db_user.failed_login_attempts}/5)")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        # Successful login - Reset attempts
        db_user.failed_login_attempts = 0
        db_user.locked_until = None
        await db.commit()
        
        access_token_expires = timedelta(minutes=app_settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": db_user.email}, expires_delta=access_token_expires
        )
        
        logger.info(f"Login successful for {user.email}")
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected login error for {user.email}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

@router.post("/firebase-login", response_model=Token)
async def firebase_login(data: FirebaseLogin, db: AsyncSession = Depends(get_db)):
    import logging
    import os
    logger = logging.getLogger(__name__)
    
    # Initialize Firebase if not done
    try:
        firebase_admin.get_app()
    except ValueError:
        # Try to initialize with project ID from environment
        project_id = os.getenv("VITE_FIREBASE_PROJECT_ID", "quantai-f45ed")
        try:
            # Try credential-less initialization (works in GCP or with GOOGLE_APPLICATION_CREDENTIALS)
            firebase_admin.initialize_app(options={"projectId": project_id})
            logger.info(f"Firebase Admin initialized with project: {project_id}")
        except Exception as init_err:
            logger.error(f"Firebase Admin init failed: {init_err}")
            # Create app without credentials for development
            firebase_admin.initialize_app()
    
    # Production: Verify the id_token with Firebase
    try:
        decoded_token = firebase_auth.verify_id_token(data.id_token)
        user_email = decoded_token.get("email")
        user_full_name = decoded_token.get("name") or data.full_name or "Firebase User"
        logger.info(f"Firebase token verified for: {user_email}")
    except Exception as e:
        logger.warning(f"Firebase token verification failed: {e}")
        
        # Development fallback: Trust the email from the request if token verification fails
        # This should be disabled in production by setting FIREBASE_STRICT_MODE=true
        if os.getenv("FIREBASE_STRICT_MODE", "false").lower() != "true":
            user_email = data.email
            user_full_name = data.full_name or "User"
            logger.warning(f"DEV MODE: Using email from request: {user_email}")
            
            if not user_email:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Email required when Firebase verification fails"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Firebase token verification failed"
            )
    
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
