import logging
from celery_app import celery_app
from database import SessionLocal
from services.auth.token_manager import TokenManagerService

logger = logging.getLogger(__name__)

@celery_app.task(name="monitor_analytics_token_health")
def monitor_analytics_token_health():
    """
    Periodic task (e.g. daily) to monitor the 1-year Analytics Token.
    Triggers alerts to Observability Stack (e.g., Loki/Sentry) 
    if the token is expiring in < 30 days.
    """
    logger.info("Running Token Expiry Monitor")
    
    db = SessionLocal()
    try:
        manager = TokenManagerService(db)
        health = manager.check_token_health()
        
        status = health.get("status")
        days = health.get("days_remaining")
        
        if status == "MISSING":
            logger.critical("ALERT: No Analytics Token found in Database. Market Data Worker will fail.")
        elif status == "EXPIRED":
            logger.critical("ALERT: Analytics Token is EXPIRED! Live market connectivity is down.")
        elif status == "WARNING" or days < 30:
            logger.error(f"WARNING: Analytics Token expires in {days} days. Please generate and update a new 1-year token.")
        else:
            logger.info(f"Analytics Token Healthy. Expires in {days} days.")
            
        return health
    except Exception as e:
        logger.error(f"Token Monitor encountered an error: {e}")
        raise
    finally:
        db.close()
