"""
FastAPI Middleware for Observability

Provides request-level instrumentation for correlation IDs, logging, and metrics.
Refactored to pure ASGI middleware to avoid Starlette BaseHTTPMiddleware concurrency bugs.
"""

import time
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Scope, Receive, Send

from core.observability.correlation import (
    set_correlation_id,
    generate_correlation_id,
)
from core.observability.logging import get_logger
from core.observability.metrics import get_metrics
from core.observability.config import get_observability_config


logger = get_logger(__name__)


class CorrelationMiddleware:
    """
    ASGI Middleware to generate and propagate correlation IDs.
    """
    def __init__(self, app: ASGIApp):
        self.app = app
        
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
            
        config = get_observability_config()
        headers = Headers(scope=scope)
        
        # Get or generate correlation ID
        correlation_id = headers.get(config.correlation_header)
        if not correlation_id:
            correlation_id = generate_correlation_id()
            
        # Set in context for the request lifecycle
        set_correlation_id(correlation_id)
        
        # Modify response headers to include correlation ID on startup
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers_list = list(message.get("headers", []))
                headers_list.append((
                    config.correlation_header.encode('latin1'),
                    correlation_id.encode('latin1')
                ))
                message["headers"] = headers_list
            await send(message)
            
        await self.app(scope, receive, send_wrapper)


class RequestLoggingMiddleware:
    """
    ASGI Middleware to log request start/end with timing.
    """
    SKIP_ROUTES = {"/health", "/ready", "/metrics", "/"}
    
    def __init__(self, app: ASGIApp):
        self.app = app
        
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
            
        path = scope.get("path", "")
        method = scope.get("method", "")
        
        if path in self.SKIP_ROUTES:
            await self.app(scope, receive, send)
            return
            
        start_time = time.perf_counter()
        
        # Log request start
        logger.info(
            "request_started",
            route=path,
            method=method,
            query=scope.get("query_string", b"").decode("utf-8")
        )
        
        status_code = [500]
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_code[0] = message.get("status", 500)
            await send(message)
            
        try:
            await self.app(scope, receive, send_wrapper)
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            # Log request completion
            config = get_observability_config()
            log_level = "warning" if duration_ms > config.slow_request_threshold_ms else "info"
            
            getattr(logger, log_level)(
                "request_completed",
                route=path,
                method=method,
                status=status_code[0],
                duration_ms=round(duration_ms, 2)
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "request_failed",
                route=path,
                method=method,
                error=str(e),
                duration_ms=round(duration_ms, 2),
                exc_info=True
            )
            raise


class MetricsMiddleware:
    """
    ASGI Middleware to collect Prometheus metrics.
    """
    SKIP_ROUTES = {"/health", "/ready", "/metrics"}
    
    def __init__(self, app: ASGIApp):
        self.app = app
        
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
            
        path = scope.get("path", "")
        method = scope.get("method", "")
        
        if path in self.SKIP_ROUTES:
            await self.app(scope, receive, send)
            return
            
        metrics = get_metrics()
        start_time = time.perf_counter()
        status_code = [500]
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_code[0] = message.get("status", 500)
            await send(message)
            
        try:
            await self.app(scope, receive, send_wrapper)
            duration = time.perf_counter() - start_time
            
            # Record successful request
            metrics.record_request(
                route=self._normalize_route(path),
                method=method,
                status=status_code[0],
                duration=duration
            )
            
            # Record errors (4xx, 5xx)
            if status_code[0] >= 400:
                metrics.record_error(
                    route=self._normalize_route(path),
                    error_code=f"HTTP_{status_code[0]}"
                )
        except Exception:
            duration = time.perf_counter() - start_time
            
            # Record failed request
            metrics.record_request(
                route=self._normalize_route(path),
                method=method,
                status=500,
                duration=duration
            )
            metrics.record_error(
                route=self._normalize_route(path),
                error_code="INTERNAL_ERROR"
            )
            raise
            
    def _normalize_route(self, path: str) -> str:
        """
        Normalize route path to reduce cardinality.
        """
        parts = path.strip("/").split("/")
        normalized = []
        
        for part in parts:
            # Detect likely dynamic segments (UUIDs, stock symbols, IDs)
            if self._is_dynamic_segment(part):
                normalized.append("{id}")
            else:
                normalized.append(part)
                
        return "/" + "/".join(normalized)
        
    def _is_dynamic_segment(self, segment: str) -> bool:
        """Check if a path segment is likely dynamic."""
        if segment.isupper() and len(segment) <= 20:
            return True
        if segment.isdigit():
            return True
        if len(segment) == 36 and segment.count("-") == 4:
            return True
        if len(segment) >= 16 and all(c in "0123456789abcdef" for c in segment.lower()):
            return True
        return False


def setup_observability_middleware(app) -> None:
    """
    Configure all observability middleware on a FastAPI app.
    
    Order matters: Correlation -> Logging -> Metrics (last added = first executed)
    """
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(CorrelationMiddleware)
