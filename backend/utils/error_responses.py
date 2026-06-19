from typing import Any, List, Optional, Dict
from pydantic import BaseModel
from fastapi import Request, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

class ErrorDetail(BaseModel):
    loc: List[str]
    msg: str
    type: str

class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Optional[List[ErrorDetail]] = None

class StandardErrorEnvelope(BaseModel):
    success: bool = False
    error: ErrorResponse

def create_error_response(
    status_code: int,
    code: str,
    message: str,
    details: Optional[Any] = None,
    service: str = "quantai-backend"
) -> JSONResponse:
    """
    Creates a standardized JSON error response with the requested structured schema:
    {
        "success": false,
        "service": "...",
        "error_code": "...",
        "message": "...",
        "details": "..."
    }
    """
    details_str = ""
    if details:
        if isinstance(details, str):
            details_str = details
        else:
            import json
            try:
                details_str = json.dumps(details)
            except:
                details_str = str(details)

    content = {
        "success": False,
        "error": message,
        "error_code": code,
        "message": message,
        "details": details_str,
        "service": service
    }
    return JSONResponse(status_code=status_code, content=content)

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Custom handler for Pydantic validation errors.
    Converts raw Pydantic errors into a standardized readable format.
    """
    details = []
    for error in exc.errors():
        loc = error.get("loc", [])
        field_name = " -> ".join([str(x) for x in loc]) if loc else "unknown"
        
        details.append({
            "loc": loc,
            "msg": error.get("msg", "Invalid value"),
            "type": error.get("type", "value_error"),
            "field": field_name
        })

    return create_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="VALIDATION_ERROR",
        message="Request validation failed",
        details=details
    )

class APIError(Exception):
    """Base class for API errors."""
    def __init__(self, code: str, message: str, status_code: int = 400, details: Any = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details

async def http_exception_handler(request: Request, exc: HTTPException):
    """Handler for FastAPI HTTPExceptions."""
    return create_error_response(
        status_code=exc.status_code,
        code=f"HTTP_{exc.status_code}",
        message=exc.detail,
        details=None
    )

async def api_error_handler(request: Request, exc: APIError):
    """Handler for custom APIErrors."""
    return create_error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details
    )

async def generic_exception_handler(request: Request, exc: Exception):
    """Fallback handler for unhandled exceptions."""
    import logging
    import traceback
    logger = logging.getLogger(__name__)
    tb = traceback.format_exc()
    logger.error(f"Unhandled exception: {exc}\n{tb}")
    return create_error_response(
        status_code=500,
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred. Please contact support.",
        details=tb
    )
