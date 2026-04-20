import os
from datetime import datetime, timedelta
from passlib.context import CryptContext
from cryptography.fernet import Fernet
import logging

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# You should define ENCRYPTION_KEY in your environment, e.g. using `Fernet.generate_key()`
# For safety, we fall back to a newly generated key per runtime if not set
# (which means tokens will be invalid on restart if no key is provided in .env!)
ENCRYPTION_KEY_ENV = os.getenv("TOKEN_ENCRYPTION_KEY")
if not ENCRYPTION_KEY_ENV:
    logger.warning("TOKEN_ENCRYPTION_KEY is not set in environment! Tokens encrypted this session will be lost on restart.")
    # We create a random temporary key
    _fernet = Fernet(Fernet.generate_key())
else:
    try:
        _fernet = Fernet(ENCRYPTION_KEY_ENV.encode('utf-8'))
    except Exception as e:
        logger.error(f"Failed to initialize Fernet with provided TOKEN_ENCRYPTION_KEY: {e}")
        _fernet = Fernet(Fernet.generate_key())

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def encrypt_token(token: str) -> str:
    """Encrypts a plaintext token into a Fernet-secured string."""
    if not token:
        return ""
    try:
        return _fernet.encrypt(token.encode('utf-8')).decode('utf-8')
    except Exception as e:
        logger.error(f"Error encrypting token: {e}")
        raise ValueError("Failed to encrypt token")

def decrypt_token(encrypted_token: str) -> str:
    """Decrypts a Fernet-secured token string back to plaintext."""
    if not encrypted_token:
        return ""
    try:
        return _fernet.decrypt(encrypted_token.encode('utf-8')).decode('utf-8')
    except Exception as e:
        logger.error(f"Error decrypting token: {e}")
        raise ValueError("Failed to decrypt token")
