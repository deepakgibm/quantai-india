"""
Correlation ID Management

Provides request-scoped correlation IDs for distributed tracing and log correlation.
Uses contextvars for async-safe propagation across the request lifecycle.
"""

import uuid
from contextvars import ContextVar
from typing import Optional


# Context variable for async-safe correlation ID storage
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def generate_correlation_id() -> str:
    """
    Generate a new correlation ID.
    
    Format: 8-char hex for brevity while maintaining uniqueness.
    """
    return uuid.uuid4().hex[:16]


def get_correlation_id() -> Optional[str]:
    """
    Get the current correlation ID from context.
    
    Returns None if no correlation ID has been set for this context.
    """
    return correlation_id_var.get()


def set_correlation_id(correlation_id: str) -> str:
    """
    Set the correlation ID for the current context.
    
    Args:
        correlation_id: The correlation ID to set
        
    Returns:
        The correlation ID that was set
    """
    correlation_id_var.set(correlation_id)
    return correlation_id


def get_or_create_correlation_id() -> str:
    """
    Get existing correlation ID or create a new one.
    
    Returns:
        Existing or newly created correlation ID
    """
    existing = get_correlation_id()
    if existing:
        return existing
    
    new_id = generate_correlation_id()
    set_correlation_id(new_id)
    return new_id


class CorrelationContext:
    """
    Context manager for correlation ID scope.
    
    Usage:
        with CorrelationContext("abc123"):
            # All code here has access to correlation ID
            log.info("Processing request")
    """
    
    def __init__(self, correlation_id: Optional[str] = None):
        self.correlation_id = correlation_id or generate_correlation_id()
        self._token = None
    
    def __enter__(self) -> str:
        self._token = correlation_id_var.set(self.correlation_id)
        return self.correlation_id
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._token:
            correlation_id_var.reset(self._token)
        return False
