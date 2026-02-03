import logging
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
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
    """Verify a plain password against a hashed password.
    
    Handles edge cases:
    - Empty or None passwords
    - Malformed bcrypt hashes
    - Password byte length limits (bcrypt max 72 bytes)
    """
    try:
        # Handle edge cases
        if not plain_password or not hashed_password:
            return False
        
        # Check if the hash looks like a valid bcrypt hash
        if not hashed_password.startswith('$2'):
            # Not a bcrypt hash - might be Firebase auth marker or corrupted
            if hashed_password == "firebase_auth_no_password":
                return False  # Firebase users should use Firebase auth
            # Try anyway, will likely fail
            return False
        
        # Truncate password to 72 bytes if needed (bcrypt limitation)
        # This prevents "password cannot be longer than 72 bytes" error
        password_bytes = plain_password.encode('utf-8')[:72]
        truncated_password = password_bytes.decode('utf-8', errors='ignore')
        
        return pwd_context.verify(truncated_password, hashed_password)
    except Exception as e:
        # Log but don't expose the error details
        import logging
        logging.getLogger(__name__).error(f"Password verification error: {type(e).__name__}")
        return False

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
            detail="Authentication token is missing. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials. Session may have expired.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        
        # Handle offline demo token for local testing/dev
        if token == "offline_demo_token":
            # Return a system/test user for demo mode
            result = await db.execute(select(User).limit(1))
            user = result.scalar_one_or_none()
            if user:
                return user
            # Fallback if no users in DB
            return User(id=1, email="demo@example.com", username="demo", full_name="Demo User")

        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            email: str = payload.get("sub")
            if email is None:
                raise credentials_exception
        except JWTError as e:
            logging.getLogger(__name__).warning(f"JWT Verification failed: {e} | Token: {token[:10]}...")
            raise credentials_exception
    except Exception as e:
        logging.getLogger(__name__).error(f"Auth error: {type(e).__name__}: {e}")
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
