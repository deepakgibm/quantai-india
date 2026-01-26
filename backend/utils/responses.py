"""
Standardized API Response Models
================================
Provides consistent response structure across all API endpoints.
"""

from pydantic import BaseModel, Field
from typing import TypeVar, Generic, Optional, Any, List
from datetime import datetime

T = TypeVar('T')


class ErrorDetail(BaseModel):
    """Structured error information."""
    code: str = Field(..., description="Error code for client handling")
    message: str = Field(..., description="Human-readable error message")
    field: Optional[str] = Field(None, description="Field that caused the error")
    details: Optional[Any] = Field(None, description="Additional error context")


class PaginationMeta(BaseModel):
    """Pagination metadata for list responses."""
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)
    total: int = Field(0, ge=0)
    total_pages: int = Field(0, ge=0)
    
    @classmethod
    def create(cls, total: int, page: int = 1, per_page: int = 20) -> "PaginationMeta":
        total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0
        return cls(page=page, per_page=per_page, total=total, total_pages=total_pages)


class ApiResponse(BaseModel, Generic[T]):
    """
    Standard API response wrapper.
    
    Usage:
        return ApiResponse(data=result)
        return ApiResponse.error("NOT_FOUND", "Resource not found", status_code=404)
    """
    success: bool = True
    data: Optional[T] = None
    error: Optional[ErrorDetail] = None
    meta: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None
    
    @classmethod
    def ok(cls, data: T, meta: Optional[dict] = None, request_id: Optional[str] = None) -> "ApiResponse[T]":
        """Create a successful response."""
        return cls(success=True, data=data, meta=meta, request_id=request_id)
    
    @classmethod
    def error(
        cls, 
        code: str, 
        message: str, 
        field: Optional[str] = None,
        details: Optional[Any] = None,
        request_id: Optional[str] = None
    ) -> "ApiResponse":
        """Create an error response."""
        return cls(
            success=False,
            error=ErrorDetail(code=code, message=message, field=field, details=details),
            request_id=request_id
        )
    
    @classmethod
    def paginated(
        cls, 
        items: List[T], 
        total: int, 
        page: int = 1, 
        per_page: int = 20,
        request_id: Optional[str] = None
    ) -> "ApiResponse[List[T]]":
        """Create a paginated list response."""
        return cls(
            success=True,
            data=items,
            meta={"pagination": PaginationMeta.create(total, page, per_page).model_dump()},
            request_id=request_id
        )


# Common error codes
class ErrorCodes:
    """Standard error codes for API responses."""
    # Client errors (4xx)
    BAD_REQUEST = "BAD_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    
    # Server errors (5xx)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    GATEWAY_TIMEOUT = "GATEWAY_TIMEOUT"
    EXTERNAL_API_ERROR = "EXTERNAL_API_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"


# Helper functions for FastAPI endpoints
def success_response(data: Any, meta: Optional[dict] = None) -> dict:
    """Quick helper for successful responses."""
    return ApiResponse.ok(data=data, meta=meta).model_dump()


def error_response(code: str, message: str, details: Any = None) -> dict:
    """Quick helper for error responses."""
    return ApiResponse.error(code=code, message=message, details=details).model_dump()
