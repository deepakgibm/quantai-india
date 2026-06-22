import logging
from typing import Dict, Optional
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session
from models import BrokerCredentials
from core.security import encrypt_token, decrypt_token

logger = logging.getLogger(__name__)

class CredentialService:
    """
    Service to securely manage, encrypt, and rotate API credentials
    and broker tokens at rest.
    """

    @staticmethod
    def encrypt(data: str) -> str:
        """Encrypt plain text data."""
        return encrypt_token(data)

    @staticmethod
    def decrypt(encrypted_data: str) -> str:
        """Decrypt encrypted data."""
        return decrypt_token(encrypted_data)

    @staticmethod
    def get_broker_credentials(db: Session, user_id: int, broker: str = "upstox") -> Optional[Dict[str, str]]:
        """Retrieve decrypted broker credentials for a user."""
        creds = db.query(BrokerCredentials).filter(
            BrokerCredentials.user_id == user_id,
            BrokerCredentials.broker == broker,
            BrokerCredentials.is_active == True
        ).first()

        if not creds:
            return None

        # Transparently decrypted by the EncryptedString TypeDecorator in database.py
        return {
            "api_key": creds.api_key,
            "api_secret": creds.api_secret,
            "access_token": creds.access_token,
            "refresh_token": creds.refresh_token
        }

    @staticmethod
    def rotate_encryption_key(db: Session, old_key: str, new_key: str):
        """
        Rotates the encryption key for all stored credentials in the database.
        Reads with old_key, encrypts with new_key, and updates the DB.
        """
        try:
            old_fernet = Fernet(old_key.encode('utf-8'))
            new_fernet = Fernet(new_key.encode('utf-8'))
        except Exception as e:
            logger.error(f"Failed to initialize Fernet with rotation keys: {e}")
            raise ValueError("Invalid key format for rotation")

        from sqlalchemy import text
        
        # We run a raw SQL query to get the raw encrypted strings from the database
        # to avoid TypeDecorator automatic decryption/encryption using the system key.
        rows = db.execute(text("SELECT id, api_key, api_secret, access_token, refresh_token FROM broker_credentials")).fetchall()
        
        for row in rows:
            row_id, enc_key, enc_secret, enc_access, enc_refresh = row
            
            # Decrypt with old key, encrypt with new key
            dec_key = old_fernet.decrypt(enc_key.encode('utf-8')).decode('utf-8') if enc_key else None
            dec_secret = old_fernet.decrypt(enc_secret.encode('utf-8')).decode('utf-8') if enc_secret else None
            dec_access = old_fernet.decrypt(enc_access.encode('utf-8')).decode('utf-8') if enc_access else None
            dec_refresh = old_fernet.decrypt(enc_refresh.encode('utf-8')).decode('utf-8') if enc_refresh else None
            
            rot_key = new_fernet.encrypt(dec_key.encode('utf-8')).decode('utf-8') if dec_key else None
            rot_secret = new_fernet.encrypt(dec_secret.encode('utf-8')).decode('utf-8') if dec_secret else None
            rot_access = new_fernet.encrypt(dec_access.encode('utf-8')).decode('utf-8') if dec_access else None
            rot_refresh = new_fernet.encrypt(dec_refresh.encode('utf-8')).decode('utf-8') if dec_refresh else None
            
            db.execute(
                text("""
                    UPDATE broker_credentials 
                    SET api_key = :key, api_secret = :secret, access_token = :access, refresh_token = :refresh
                    WHERE id = :id
                """),
                {"key": rot_key, "secret": rot_secret, "access": rot_access, "refresh": rot_refresh, "id": row_id}
            )
            
        db.commit()
        logger.info(f"Successfully rotated encryption keys for {len(rows)} broker credential records.")
