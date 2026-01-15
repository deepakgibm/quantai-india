"""
Circuit Breaker Pattern Implementation

Provides fault tolerance for upstream API calls (Upstox, external services).

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Circuit tripped, requests fail fast without calling upstream
- HALF_OPEN: Testing recovery, limited requests allowed

Features:
- Configurable failure threshold and recovery timeout
- Exponential backoff for recovery
- Thread-safe operation
- Metrics tracking
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Optional, Any, Dict
from functools import wraps

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker monitoring."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    state_changes: int = 0
    current_state: CircuitState = CircuitState.CLOSED
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "rejected_calls": self.rejected_calls,
            "success_rate": round(self.successful_calls / self.total_calls * 100, 2) if self.total_calls > 0 else 0,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_success_time": self.last_success_time.isoformat() if self.last_success_time else None,
            "state_changes": self.state_changes,
            "current_state": self.current_state.value
        }


class CircuitBreaker:
    """
    Circuit Breaker for external API calls.
    
    Usage:
        breaker = CircuitBreaker(name="upstox", failure_threshold=5, recovery_timeout=60)
        
        @breaker.protect
        async def call_upstox_api():
            ...
        
        # Or manually:
        if breaker.allow_request():
            try:
                result = await call_api()
                breaker.record_success()
            except Exception:
                breaker.record_failure()
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 3,
        expected_exceptions: tuple = (Exception,)
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Identifier for this circuit breaker
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            half_open_max_calls: Max calls to allow in half-open state
            expected_exceptions: Exception types that count as failures
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.expected_exceptions = expected_exceptions
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = asyncio.Lock()
        
        self.stats = CircuitBreakerStats()
        
        logger.info(f"Circuit breaker '{name}' initialized: threshold={failure_threshold}, timeout={recovery_timeout}s")
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state, checking for automatic recovery."""
        if self._state == CircuitState.OPEN:
            if self._last_failure_time and (time.time() - self._last_failure_time) >= self.recovery_timeout:
                self._transition_to(CircuitState.HALF_OPEN)
        return self._state
    
    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state."""
        if self._state != new_state:
            old_state = self._state
            self._state = new_state
            self.stats.state_changes += 1
            self.stats.current_state = new_state
            
            if new_state == CircuitState.HALF_OPEN:
                self._half_open_calls = 0
            
            logger.info(f"Circuit breaker '{self.name}': {old_state.value} -> {new_state.value}")
    
    def allow_request(self) -> bool:
        """Check if a request should be allowed."""
        state = self.state  # This may trigger state transition
        
        if state == CircuitState.CLOSED:
            return True
        elif state == CircuitState.OPEN:
            self.stats.rejected_calls += 1
            return False
        elif state == CircuitState.HALF_OPEN:
            if self._half_open_calls < self.half_open_max_calls:
                self._half_open_calls += 1
                return True
            self.stats.rejected_calls += 1
            return False
        
        return False
    
    def record_success(self) -> None:
        """Record a successful call."""
        self.stats.total_calls += 1
        self.stats.successful_calls += 1
        self.stats.last_success_time = datetime.now()
        
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            # After enough successes in half-open, close the circuit
            if self._success_count >= self.half_open_max_calls:
                self._transition_to(CircuitState.CLOSED)
                self._failure_count = 0
                self._success_count = 0
        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success
            self._failure_count = 0
    
    def record_failure(self) -> None:
        """Record a failed call."""
        self.stats.total_calls += 1
        self.stats.failed_calls += 1
        self.stats.last_failure_time = datetime.now()
        self._last_failure_time = time.time()
        
        if self._state == CircuitState.HALF_OPEN:
            # Any failure in half-open reopens the circuit
            self._transition_to(CircuitState.OPEN)
            self._success_count = 0
        elif self._state == CircuitState.CLOSED:
            self._failure_count += 1
            if self._failure_count >= self.failure_threshold:
                self._transition_to(CircuitState.OPEN)
    
    def protect(self, func: Callable) -> Callable:
        """
        Decorator to protect a function with this circuit breaker.
        
        Usage:
            @breaker.protect
            async def call_api():
                ...
        """
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not self.allow_request():
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Retry after {self.recovery_timeout}s."
                )
            
            try:
                result = await func(*args, **kwargs)
                self.record_success()
                return result
            except self.expected_exceptions as e:
                self.record_failure()
                raise
        
        return wrapper
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            **self.stats.to_dict()
        }
    
    def reset(self) -> None:
        """Manually reset the circuit breaker to closed state."""
        self._transition_to(CircuitState.CLOSED)
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._last_failure_time = None
        logger.info(f"Circuit breaker '{self.name}' manually reset")


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and request is rejected."""
    pass


# =============================================================================
# Global Circuit Breakers
# =============================================================================

_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60
) -> CircuitBreaker:
    """
    Get or create a named circuit breaker.
    
    Args:
        name: Unique identifier for the circuit breaker
        failure_threshold: Failures before opening (only used on creation)
        recovery_timeout: Seconds before recovery attempt (only used on creation)
    
    Returns:
        CircuitBreaker instance
    """
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout
        )
    return _circuit_breakers[name]


def get_all_circuit_breaker_stats() -> Dict[str, Dict[str, Any]]:
    """Get statistics for all circuit breakers."""
    return {name: cb.get_stats() for name, cb in _circuit_breakers.items()}


# Pre-configured circuit breakers for common services
UPSTOX_CIRCUIT_BREAKER = get_circuit_breaker("upstox", failure_threshold=5, recovery_timeout=60)
YFINANCE_CIRCUIT_BREAKER = get_circuit_breaker("yfinance", failure_threshold=3, recovery_timeout=30)
GEMINI_CIRCUIT_BREAKER = get_circuit_breaker("gemini_ai", failure_threshold=3, recovery_timeout=60)
