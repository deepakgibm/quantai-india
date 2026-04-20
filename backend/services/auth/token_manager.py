import logging
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select

from models import AuthToken, User
from core.security import encrypt_token, decrypt_token

logger = logging.getLogger(__name__)

class TokenManagerService:
    def __init__(self, db: Session):
        self.db = db

    def _get_system_user_id(self) -> Optional[int]:
        """Gets or creates a system-level user account to bind instance tokens to."""
        sys_user = self.db.execute(select(User).filter_by(username="system_bot")).scalar_one_or_none()
        if not sys_user:
            sys_user = User(
                email="system@quantai.local",
                username="system_bot",
                hashed_password="not-loginable",
                is_active=True
            )
            self.db.add(sys_user)
            self.db.commit()
            self.db.refresh(sys_user)
        return sys_user.id

    def set_analytics_token(self, plaintext_token: str, expires_in_days: int = 365) -> bool:
        """Stores the encrypted 1-year Analytics Token."""
        user_id = self._get_system_user_id()
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        # Check if one already exists
        existing = self.db.execute(
            select(AuthToken).filter_by(user_id=user_id, token_type="ANALYTICS")
        ).scalar_one_or_none()
        
        if existing:
            existing.encrypted_token = plaintext_token
            existing.expires_at = expires_at
            existing.health_status = "HEALTHY"
        else:
            new_token = AuthToken(
                user_id=user_id,
                token_type="ANALYTICS",
                encrypted_token=plaintext_token,
                expires_at=expires_at,
                health_status="HEALTHY"
            )
            self.db.add(new_token)
            
        try:
            self.db.commit()
            logger.info("Analytics Token successfully securely stored.")
            return True
        except Exception as e:
            logger.error(f"Failed to save analytics token: {e}")
            self.db.rollback()
            return False

    def get_analytics_token(self) -> Optional[str]:
        """Retrieves and decrypts the active Analytics Token."""
        user_id = self._get_system_user_id()
        token = self.db.execute(
            select(AuthToken).filter_by(user_id=user_id, token_type="ANALYTICS")
        ).scalar_one_or_none()
        
        if not token or not token.encrypted_token:
            return None
            
        if token.expires_at and token.expires_at < datetime.utcnow():
            logger.warning("Analytics Token has expired!")
            token.health_status = "EXPIRED"
            self.db.commit()
            return None
            
        return token.encrypted_token
        
    def check_token_health(self) -> dict:
        """Dashboard view of Token Health status."""
        user_id = self._get_system_user_id()
        token = self.db.execute(
            select(AuthToken).filter_by(user_id=user_id, token_type="ANALYTICS")
        ).scalar_one_or_none()
        
        if not token:
            return {"status": "MISSING", "days_remaining": 0}
            
        days_remaining = (token.expires_at - datetime.utcnow()).days if token.expires_at else 0
        status = "HEALTHY"
        if days_remaining < 30:
            status = "WARNING"
        if days_remaining <= 0:
            status = "EXPIRED"
            
        return {
            "status": status,
            "days_remaining": days_remaining,
            "expires_at": str(token.expires_at) if token.expires_at else None
        }

    def set_oauth_token(self, user_id: int, access_token: str, refresh_token: str, expires_in_seconds: int = 86400) -> bool:
        """Stores short-lived OAuth tokens for APIs not supported by Analytics token."""
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in_seconds)
        
        existing = self.db.execute(
            select(AuthToken).filter_by(user_id=user_id, token_type="OAUTH")
        ).scalar_one_or_none()
        
        # Store as a composite plaintext string, model handles the encryption
        payload = f"{access_token}::{refresh_token}"
        
        if existing:
            existing.encrypted_token = payload
            existing.expires_at = expires_at
            existing.health_status = "HEALTHY"
        else:
            new_token = AuthToken(
                user_id=user_id,
                token_type="OAUTH",
                encrypted_token=payload,
                expires_at=expires_at,
                health_status="HEALTHY"
            )
            self.db.add(new_token)
            
        try:
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to save oauth token: {e}")
            self.db.rollback()
            return False

    def get_oauth_token(self, user_id: int) -> Optional[dict]:
        """Retrieves and decrypts the OAuth Token for user ops (Order Placement)."""
        token_record = self.db.execute(
            select(AuthToken).filter_by(user_id=user_id, token_type="OAUTH")
        ).scalar_one_or_none()
        
        if not token_record or not token_record.encrypted_token:
            return None
            
        if token_record.expires_at and token_record.expires_at < datetime.utcnow():
            token_record.health_status = "EXPIRED"
            self.db.commit()
            return None
            
        try:
            acc, ref = token_record.encrypted_token.split("::")
            return {
                "access_token": acc,
                "refresh_token": ref
            }
        except:
            return None
