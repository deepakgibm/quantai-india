"""
FastAPI Middleware for Observability

Provides request-level instrumentation for correlation IDs, logging, and metrics.
"""

import time
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from core.observability.correlation import (
    set_correlation_id,
    generate_correlation_id,
)
from core.observability.logging import get_logger
from core.observability.metrics import get_metrics
from core.observability.config import get_observability_config


logger = get_logger(__name__)


class CorrelationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to generate and propagate correlation IDs.
    
    - Checks for incoming X-Correlation-ID header
    - Generates new ID if not present
    - Adds correlation ID to response headers
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        config = get_observability_config()
        
        # Get or generate correlation ID
        correlation_id = request.headers.get(config.correlation_header)
        if not correlation_id:
            correlation_id = generate_correlation_id()
        
        # Set in context for the request lifecycle
        set_correlation_id(correlation_id)
        
        # Process request
        response = await call_next(request)
        
        # Add to response headers
        response.headers[config.correlation_header] = correlation_id
        
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log request start/end with timing.
    
    Logs include:
    - Route, method, status code
    - Duration in milliseconds
    - Correlation ID (auto-injected by logger)
    """
    
    # Routes to skip logging (health checks, metrics)
    SKIP_ROUTES = {"/health", "/ready", "/metrics", "/"}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip logging for health checks
        if request.url.path in self.SKIP_ROUTES:
            return await call_next(request)
        
        start_time = time.perf_counter()
        
        # Log request start
        logger.info(
            "request_started",
            route=request.url.path,
            method=request.method,
            query=str(request.query_params) if request.query_params else None
        )
        
        # Process request
        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            # Log request completion
            config = get_observability_config()
            log_level = "warning" if duration_ms > config.slow_request_threshold_ms else "info"
            
            getattr(logger, log_level)(
                "request_completed",
                route=request.url.path,
                method=request.method,
                status=response.status_code,
                duration_ms=round(duration_ms, 2)
            )
            
            return response
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "request_failed",
                route=request.url.path,
                method=request.method,
                error=str(e),
                duration_ms=round(duration_ms, 2),
                exc_info=True
            )
            raise


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect Prometheus metrics.
    
    Collects:
    - Request count by route, method, status
    - Request latency histogram
    - Error counts
    """
    
    # Routes to skip metrics (avoid polluting metrics with health checks)
    SKIP_ROUTES = {"/health", "/ready", "/metrics"}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip metrics for internal endpoints
        if request.url.path in self.SKIP_ROUTES:
            return await call_next(request)
        
        metrics = get_metrics()
        start_time = time.perf_counter()
        
        try:
            response = await call_next(request)
            duration = time.perf_counter() - start_time
            
            # Record successful request
            metrics.record_request(
                route=self._normalize_route(request.url.path),
                method=request.method,
                status=response.status_code,
                duration=duration
            )
            
            # Record errors (4xx, 5xx)
            if response.status_code >= 400:
                metrics.record_error(
                    route=self._normalize_route(request.url.path),
                    error_code=f"HTTP_{response.status_code}"
                )
            
            return response
            
        except Exception as e:
            duration = time.perf_counter() - start_time
            
            # Record failed request
            metrics.record_request(
                route=self._normalize_route(request.url.path),
                method=request.method,
                status=500,
                duration=duration
            )
            metrics.record_error(
                route=self._normalize_route(request.url.path),
                error_code="INTERNAL_ERROR"
            )
            
            raise
    
    def _normalize_route(self, path: str) -> str:
        """
        Normalize route path to reduce cardinality.
        
        Replaces dynamic segments with placeholders:
        /api/scanner/RELIANCE -> /api/scanner/{symbol}
        """
        parts = path.strip("/").split("/")
        normalized = []
        
        for i, part in enumerate(parts):
            # Detect likely dynamic segments (UUIDs, stock symbols, IDs)
            if self._is_dynamic_segment(part):
                normalized.append("{id}")
            else:
                normalized.append(part)
        
        return "/" + "/".join(normalized)
    
    def _is_dynamic_segment(self, segment: str) -> bool:
        """Check if a path segment is likely dynamic."""
        # All uppercase = likely stock symbol
        if segment.isupper() and len(segment) <= 20:
            return True
        # Contains only digits = likely ID
        if segment.isdigit():
            return True
        # UUID pattern
        if len(segment) == 36 and segment.count("-") == 4:
            return True
        # Hex string (like correlation ID)
        if len(segment) >= 16 and all(c in "0123456789abcdef" for c in segment.lower()):
            return True
        return False


def setup_observability_middleware(app) -> None:
    """
    Configure all observability middleware on a FastAPI app.
    
    Order matters: Correlation -> Logging -> Metrics
    """
    # Add in reverse order (last added = first executed)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(CorrelationMiddleware)
