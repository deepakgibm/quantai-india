import asyncio
import logging
import os
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add current directory to path
sys.path.append(os.getcwd())

async def debug_login():
    logger.info("Starting Auth Debugging...")
    
    import os
    from config import settings
    logger.info(f"ENV DATABASE_URL: {os.environ.get('DATABASE_URL')}")
    logger.info(f"SETTINGS DATABASE_URL: {settings.DATABASE_URL}")
    
    try:
        from services.auth_service import get_auth_service
        from schemas import UserLogin
        from database import AsyncSessionLocal
        
        auth_service = get_auth_service()
        logger.info("Auth Service initialized.")
        
        email = "dthat53@gmail.com"
        password = "admin1243"
        
        logger.info(f"Attempting login for {email}...")
        
        async with AsyncSessionLocal() as db:
            user_login = UserLogin(email=email, password=password)
            try:
                result = await auth_service.login(user_login, db)
                logger.info("Login SUCCESS!")
                logger.info(f"Result: {result}")
            except Exception as e:
                logger.error(f"Login FAILED with Exception: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()

    except ImportError as e:
        logger.error(f"Import Error: {e}")
    except Exception as e:
        logger.error(f"General Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_login())
