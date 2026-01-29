import os
from dotenv import load_dotenv

load_dotenv()


def _validate_secret_key(key: str) -> str:
    """Validate SECRET_KEY for security requirements."""
    if not key:
        # In development, allow a warning instead of crash
        import warnings
        warnings.warn(
            "SECURITY WARNING: SECRET_KEY not set! Using insecure default. "
            "Set SECRET_KEY in .env for production.",
            RuntimeWarning
        )
        return "dev-only-insecure-key-do-not-use-in-production"
    
    if len(key) < 32:
        raise ValueError(
            "SECRET_KEY must be at least 32 characters for security. "
            "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
        )
    
    if "your-secret" in key.lower() or "change-in-production" in key.lower():
        raise ValueError(
            "SECRET_KEY appears to be a placeholder. Please set a real secret key."
        )
    return key


def _validate_upstox_token(token: str) -> str:
    """Validate Upstox Access Token presence and format."""
    if not token or "your-token" in token.lower():
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("⚠️ UPSTOX_ACCESS_TOKEN is not set or is a placeholder. Real-time data will be disabled.")
        return ""
    return token


class Settings:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:admin@localhost:5432/quantai")
    
    # Dragonfly/Redis Configuration
    DRAGONFLY_HOST = os.getenv("DRAGONFLY_HOST", "localhost")
    DRAGONFLY_PORT = os.getenv("DRAGONFLY_PORT", "6379")
    
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", f"redis://{DRAGONFLY_HOST}:{DRAGONFLY_PORT}/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", f"redis://{DRAGONFLY_HOST}:{DRAGONFLY_PORT}/0")
    
    # SECURITY: Validated SECRET_KEY - no unsafe defaults
    SECRET_KEY = _validate_secret_key(os.getenv("SECRET_KEY", ""))
    
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 1440
    UPSTOX_API_KEY = os.getenv("UPSTOX_API_KEY", "")
    UPSTOX_API_SECRET = os.getenv("UPSTOX_API_SECRET", "")
    UPSTOX_REDIRECT_URI = os.getenv("UPSTOX_REDIRECT_URI", "http://localhost:3000/callback")
    UPSTOX_ACCESS_TOKEN = _validate_upstox_token(os.getenv("UPSTOX_ACCESS_TOKEN", ""))
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    MAX_CAPITAL_PER_TRADE = 100000
    MAX_RISK_PERCENTAGE = 2.0
    
    # AlphaPrime Module Settings
    ALPHA_PRIME_ENABLED = os.getenv("ALPHA_PRIME_ENABLED", "true").lower() == "true"
    ALPHA_PRIME_DATA_DIR = os.getenv("ALPHA_PRIME_DATA_DIR", "./data/alpha_prime")
    ALPHA_PRIME_MODEL_DIR = os.getenv("ALPHA_PRIME_MODEL_DIR", "./models/alpha_prime")
    
    # ETL Configuration
    NIFTY_200_SYMBOLS_URL = "https://www.niftyindices.com/IndexConstituent/ind_nifty200list.csv"
    HISTORICAL_DATA_YEARS = int(os.getenv("HISTORICAL_DATA_YEARS", "5"))
    LIVE_DATA_INTERVAL_MINUTES = int(os.getenv("LIVE_DATA_INTERVAL_MINUTES", "5"))
    
    # Upstox API Rate Limiting
    UPSTOX_RATE_LIMIT_PER_MINUTE = int(os.getenv("UPSTOX_RATE_LIMIT_PER_MINUTE", "100"))
    UPSTOX_RATE_LIMIT_BURST = int(os.getenv("UPSTOX_RATE_LIMIT_BURST", "10"))
    
    # Standard Timeouts (in seconds)
    DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "10"))
    UPSTOX_TIMEOUT = int(os.getenv("UPSTOX_TIMEOUT", "30"))
    GEMINI_TIMEOUT = int(os.getenv("GEMINI_TIMEOUT", "60"))
    DB_TIMEOUT = int(os.getenv("DB_TIMEOUT", "10"))
    
    # Retry Configuration
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_BACKOFF_FACTOR = float(os.getenv("RETRY_BACKOFF_FACTOR", "0.5"))
    
    # Observability Settings
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    METRICS_ENABLED = os.getenv("METRICS_ENABLED", "true").lower() == "true"
    TRACING_ENABLED = os.getenv("TRACING_ENABLED", "true").lower() == "true"
    
    # ML Model Parameters
    ML_LOOKBACK_DAYS = int(os.getenv("ML_LOOKBACK_DAYS", "30"))
    ML_MIN_TRAINING_SAMPLES = int(os.getenv("ML_MIN_TRAINING_SAMPLES", "1000"))
    ML_RETRAIN_FREQUENCY_HOURS = int(os.getenv("ML_RETRAIN_FREQUENCY_HOURS", "24"))
    
    # Factor Calculation Windows
    RSI_PERIOD = int(os.getenv("RSI_PERIOD", "14"))
    MACD_FAST = int(os.getenv("MACD_FAST", "12"))
    MACD_SLOW = int(os.getenv("MACD_SLOW", "26"))
    MACD_SIGNAL = int(os.getenv("MACD_SIGNAL", "9"))
    ATR_PERIOD = int(os.getenv("ATR_PERIOD", "14"))
    BOLLINGER_PERIOD = int(os.getenv("BOLLINGER_PERIOD", "20"))
    BOLLINGER_STD = float(os.getenv("BOLLINGER_STD", "2.0"))
    VWAP_PERIOD = int(os.getenv("VWAP_PERIOD", "20"))
    VOLUME_SMA_PERIOD = int(os.getenv("VOLUME_SMA_PERIOD", "20"))

    # Nifty 100 Symbols (Top 100 by market cap)
    NIFTY_100_SYMBOLS = [
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "SBIN", "BHARTIARTL", "ITC", "KOTAKBANK",
        "LTIM", "LT", "AXISBANK", "HCLTECH", "BAJFINANCE", "ASIANPAINT", "MARUTI", "SUNPHARMA", "TITAN", "ULTRACEMCO",
        "WIPRO", "ONGC", "NTPC", "POWERGRID", "M&M", "JSWSTEEL", "TATASTEEL", "ADANIENT", "ADANIGREEN", "ADANIPORTS",
        "COALINDIA", "HDFCLIFE", "SBILIFE", "BAJAJFINSV", "GRASIM", "TECHM", "BRITANNIA", "HINDALCO", "EICHERMOT", "DIVISLAB",
        "DRREDDY", "CIPLA", "TATAMOTORS", "BPCL", "HEROMOTOCO", "APOLLOHOSP", "TATACONSUM", "UPL", "INDUSINDBK", "SBICARD",
        "BAJAJ-AUTO", "HAVELLS", "PIDILITIND", "SIEMENS", "IOC", "GAIL", "AMBUJACEM", "DABUR", "VEDL", "SHREECEM",
        "DLF", "BANKBARODA", "GODREJCP", "ICICIPRULI", "SRF", "MARICO", "BEL", "ICICIGI", "BERGEPAINT", "TRENT",
        "CHOLAFIN", "TORNTPHARM", "CANBK", "PIIND", "TIINDIA", "AUBANK", "NAUKRI", "INDIGO", "HAL", "JINDALSTEL",
        "VBL", "BOSCHLTD", "ABB", "PAGEIND", "COLPAL", "MUTHOOTFIN", "POLYCAB", "TVSMOTOR", "BALKRISIND", "PERSISTENT",
        "IRCTC", "ACC", "ASTRAL", "CUMMINSIND", "MPHASIS", "OBEROIRLTY", "ASHOKLEY", "ALKEM", "IDFCFIRSTB", "BHARATFORG"
    ]


    @property
    def SYNC_DATABASE_URL(self):
        # Convert async driver URLs to sync driver URLs
        return self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://").replace("sqlite+aiosqlite://", "sqlite://")

settings = Settings()
