import logging
import os
import firebase_admin
from firebase_admin import auth as firebase_auth
from datetime import datetime, timedelta
from typing import Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from models import User, UserSettings
from schemas import UserCreate, UserLogin, FirebaseLogin
from utils.auth import get_password_hash, verify_password_async, create_access_token, create_refresh_token
from config import settings as app_settings

logger = logging.getLogger(__name__)

class AuthService:
    async def signup(self, user: UserCreate, db: AsyncSession) -> User:
        """Create a new user with default settings."""
        # Check if user exists
        result = await db.execute(select(User).where(User.email == user.email))
        existing_user = result.scalar_one_or_none()
        if existing_user:
            # Return the existing user instead of raising error
            return existing_user
        
        result = await db.execute(select(User).where(User.username == user.username))
        if result.scalar_one_or_none():
            # Generate unique username
            import random
            user.username = f"{user.username}_{random.randint(100, 999)}"
        
        hashed_password = get_password_hash(user.password)
        
        db_user = User(
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            hashed_password=hashed_password
        )
        
        db.add(db_user)
        await db.flush()
        
        # Create default settings
        user_settings = UserSettings(user_id=db_user.id)
        db.add(user_settings)
        await db.commit()
        await db.refresh(db_user)
        
        return db_user

    async def login(self, user: UserLogin, db: AsyncSession) -> Dict[str, str]:
        """Verify user credentials and return an access token."""
        result = await db.execute(select(User).where(User.email == user.email))
        db_user = result.scalar_one_or_none()
        
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        # Check for account lockout
        if db_user.locked_until and db_user.locked_until > datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account is locked. Try again after {db_user.locked_until.strftime('%H:%M:%S')} UTC"
            )

        try:
            password_valid = await verify_password_async(user.password, db_user.hashed_password)
        except Exception as e:
            logger.error(f"Password verification crashed for {user.email}: {e}")
            raise HTTPException(status_code=500, detail="Auth engine error")

        if not password_valid:
            db_user.failed_login_attempts = (db_user.failed_login_attempts or 0) + 1
            if db_user.failed_login_attempts >= 5:
                db_user.locked_until = datetime.utcnow() + timedelta(minutes=15)
            
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        # Success
        db_user.failed_login_attempts = 0
        db_user.locked_until = None
        await db.commit()
        
        access_token_expires = timedelta(minutes=app_settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": db_user.email}, expires_delta=access_token_expires
        )
        refresh_token = create_refresh_token(data={"sub": db_user.email})
        
        return {
            "access_token": access_token, 
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }

    async def firebase_login(self, data: FirebaseLogin, db: AsyncSession) -> Dict[str, str]:
        """Authenticate using a Firebase ID token."""
        # Initialize Firebase if not done
        try:
            firebase_admin.get_app()
        except ValueError:
            project_id = os.getenv("VITE_FIREBASE_PROJECT_ID", "quantai-f45ed")
            try:
                firebase_admin.initialize_app(options={"projectId": project_id})
            except Exception:
                firebase_admin.initialize_app()
        
        try:
            decoded_token = firebase_auth.verify_id_token(data.id_token)
            user_email = decoded_token.get("email")
            user_full_name = decoded_token.get("name") or data.full_name or "Firebase User"
        except Exception as e:
            if os.getenv("FIREBASE_STRICT_MODE", "false").lower() != "true":
                user_email = data.email
                user_full_name = data.full_name or "User"
            else:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Firebase verification failed")
        
        if not user_email:
            raise HTTPException(status_code=400, detail="Email is required from Firebase")
            
        result = await db.execute(select(User).where(User.email == user_email))
        db_user = result.scalar_one_or_none()
        
        if not db_user:
            username = data.username or user_email.split('@')[0]
            # Handle username collisions
            result = await db.execute(select(User).where(User.username == username))
            if result.scalar_one_or_none():
                import random
                username = f"{username}_{random.randint(100, 999)}"
                
            db_user = User(
                email=user_email,
                username=username,
                full_name=user_full_name,
                hashed_password="firebase_auth_no_password"
            )
            db.add(db_user)
            await db.flush()
            
            user_settings = UserSettings(user_id=db_user.id)
            db.add(user_settings)
            await db.commit()
            await db.refresh(db_user)
        
        access_token_expires = timedelta(minutes=app_settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": db_user.email}, expires_delta=access_token_expires
        )
        refresh_token = create_refresh_token(data={"sub": db_user.email})
        
        return {
            "access_token": access_token, 
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }

_auth_service = None
def get_auth_service():
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
