import asyncio
import time
import logging
from enum import Enum
from functools import wraps
from typing import Callable, Any
try:
    from core.observability.metrics import get_metrics
except ImportError:
    get_metrics = None

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "CLOSED"      # Normal operation
    OPEN = "OPEN"          # Failing, reject requests immediately
    HALF_OPEN = "HALF_OPEN" # Testing if service is back

class CircuitBreakerOpenException(Exception):
    """Raised when the circuit breaker is open."""
    pass

class CircuitBreaker:
    """
    Implements the Circuit Breaker pattern to prevent cascading failures.
    
    States:
    - CLOSED: Requests pass through. If failures > threshold, switch to OPEN.
    - OPEN: Requests fail fast. After reset_timeout, switch to HALF_OPEN.
    - HALF_OPEN: Allow one request. If success -> CLOSED. If fail -> OPEN.
    """
    
    def __init__(self, 
                 name: str, 
                 failure_threshold: int = 5, 
                 recovery_timeout: float = 30.0,
                 expected_exceptions: tuple = (Exception,)):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exceptions = expected_exceptions
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute protected call."""
        
        # 1. State/Recovery Check
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    await self._transition(CircuitState.HALF_OPEN)
                else:
                    logger.warning(f"CircuitBreaker[{self.name}] is OPEN. fast-failing.")
                    if get_metrics:
                        get_metrics().record_circuit_rejection(self.name)
                    raise CircuitBreakerOpenException(f"Service {self.name} is currently unavailable.")

        # 2. Execute
        try:
            result = await func(*args, **kwargs)
            
            # If successful and was HALF_OPEN, reset
            if self.state == CircuitState.HALF_OPEN:
                async with self._lock:
                    await self._reset()
                    
            return result
            
        except self.expected_exceptions as e:
            async with self._lock:
                await self._record_failure(e)
            raise e
            
    async def _record_failure(self, exception: Exception):
        # Already locked by entry call if we use a consistent locking strategy
        # Simplified: Use the fact that these are internal and the caller should locked if needed, 
        # or better: use non-nested locks.
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        logger.warning(f"CircuitBreaker[{self.name}] failure {self.failure_count}/{self.failure_threshold}. Error: {str(exception)}")
        
        if self.state == CircuitState.HALF_OPEN or self.failure_count >= self.failure_threshold:
            await self._transition(CircuitState.OPEN)

    async def _transition(self, new_state: CircuitState):
        self.state = new_state
        logger.warning(f"CircuitBreaker[{self.name}] state changed to {self.state.value}")
        if get_metrics:
            get_metrics().set_circuit_state(self.name, self.state.value.lower())

    async def _reset(self):
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        logger.info(f"CircuitBreaker[{self.name}] recovered. Reset to CLOSED.")
            
def circuit_breaker(name: str, **cb_kwargs):
    """Decorator for easy generic usage."""
    cb = CircuitBreaker(name, **cb_kwargs)
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await cb.call(func, *args, **kwargs)
        return wrapper
    return decorator
