import logging
import httpx
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from services.upstox_client import get_upstox_client
from models import User

logger = logging.getLogger(__name__)

async def execute_broker_call(
    client_method: str,
    current_user: User,
    db: AsyncSession,
    *args,
    **kwargs
):
    """
    Execute a broker API call using UpstoxClient, with:
    - Centralized 401 session expiration handling (auto-disconnects in DB)
    - Detailed error logging (URL, status code, broker response)
    - Proper propagation of exceptions.
    """
    # Initialize Upstox client with the user's specific access token if connected
    user_token = getattr(current_user, "upstox_access_token", None) if getattr(current_user, "is_upstox_connected", False) else None
    client = get_upstox_client(user_token)
    
    try:
        # Bind the method to the client instance
        func = getattr(client, client_method)
        logger.info(f"[Broker API Call] Executing '{client_method}' for user: {current_user.email}")
        return await func(*args, **kwargs)
    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code
        response_text = e.response.text
        logger.error(
            f"[Broker API Error] Method: {client_method} | URL: {e.request.url} | "
            f"Status: {status_code} | Response: {response_text} | User: {current_user.email}"
        )
        if status_code == 401:
            logger.warning(f"Upstox token expired/unauthorized for user {current_user.email}. Disconnecting broker.")
            # Clear broker token and state in DB
            current_user.is_upstox_connected = False
            current_user.upstox_access_token = None
            try:
                await db.commit()
                logger.info(f"Successfully updated broker connection state for {current_user.email}")
            except Exception as commit_err:
                logger.error(f"Failed to commit database update for broker disconnect: {commit_err}")
                await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Upstox session expired or credentials invalid. Please reconnect your broker."
            )
        elif status_code == 403:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Upstox access forbidden. Please verify your broker API plan and permissions."
            )
        else:
            raise HTTPException(
                status_code=status_code,
                detail=f"Broker API Error: {response_text}"
            )
    except httpx.TimeoutException as e:
        logger.error(f"[Broker API Timeout] User: {current_user.email} | Method: {client_method} | Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Broker request timed out. Please check network status and retry."
        )
    except Exception as e:
        logger.error(f"[Broker API Unknown Error] User: {current_user.email} | Method: {client_method} | Error: {e}", exc_info=True)
        # If it is already an HTTPException, re-raise it
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Broker service error: {str(e)}"
        )
