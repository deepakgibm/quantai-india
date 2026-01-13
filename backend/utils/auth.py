from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import settings
from models import User
from database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# Use auto_error=False to get 401 (not 403) for missing tokens
security = HTTPBearer(auto_error=False)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

async def verify_password_async(plain_password: str, hashed_password: str) -> bool:
    """Async version of verify_password to avoid blocking event loop."""
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, verify_password, plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    # Return 401 Unauthorized when token is missing (not 403)
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        with open("auth_debug.log", "a") as f: f.write(f"DEBUG AUTH: Analyzing token: {token[:10]}...{token[-10:]}\n")
        
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        
        with open("auth_debug.log", "a") as f: f.write(f"DEBUG AUTH: Decoded email: {email}\n")

        if email is None:
            with open("auth_debug.log", "a") as f: f.write("DEBUG AUTH: Email is None in payload\n")
            raise credentials_exception
    except JWTError as e:
        with open("auth_debug.log", "a") as f: f.write(f"DEBUG AUTH: JWT Error: {e}\n")
        raise credentials_exception
    
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user


# Optional security for endpoints that can work without authentication
optional_security = HTTPBearer(auto_error=False)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Optional authentication dependency.
    Returns the user if a valid token is provided, None otherwise.
    Use this for endpoints that should work without auth but can use user context if available.
    """
    if credentials is None:
        return None
    
    try:
        token = credentials.credentials
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
    except JWTError:
        return None
    
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    return user
