"""
Prometheus Metrics

Provides application metrics following the RED method (Rate, Errors, Duration).
Metrics are exposed via /metrics endpoint for Prometheus scraping.
"""

import time
from typing import Callable, Optional
from functools import wraps

try:
    from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Stub classes when prometheus_client is not installed
    class Counter:
        def __init__(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self
        def inc(self, *args, **kwargs): pass
    class Histogram:
        def __init__(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self
        def observe(self, *args, **kwargs): pass
        def time(self): return _NoopContext()
    class Gauge:
        def __init__(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self
        def set(self, *args, **kwargs): pass
        def inc(self, *args, **kwargs): pass
        def dec(self, *args, **kwargs): pass
    class CollectorRegistry:
        def __init__(self): pass
    class _NoopContext:
        def __enter__(self): return self
        def __exit__(self, *args): pass
    def generate_latest(registry): return b""
    CONTENT_TYPE_LATEST = "text/plain"

from core.observability.config import get_observability_config


# =============================================================================
# Metric Definitions
# =============================================================================

# API Metrics
API_REQUEST_COUNT = Counter(
    "quantai_api_requests_total",
    "Total API requests",
    ["route", "method", "status"]
)

API_REQUEST_LATENCY = Histogram(
    "quantai_api_request_duration_seconds",
    "API request duration in seconds",
    ["route", "method"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

API_ERRORS = Counter(
    "quantai_api_errors_total",
    "Total API errors",
    ["route", "error_code"]
)

# Cache Metrics
CACHE_OPERATIONS = Counter(
    "quantai_cache_operations_total",
    "Cache operations",
    ["operation", "status"]  # operation: get/set/delete, status: hit/miss/error
)

CACHE_LATENCY = Histogram(
    "quantai_cache_operation_duration_seconds",
    "Cache operation duration",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25)
)

CACHE_KEYS = Gauge(
    "quantai_cache_keys_count",
    "Number of keys in cache",
    ["prefix"]
)

# Database Metrics
DB_QUERY_LATENCY = Histogram(
    "quantai_db_query_duration_seconds",
    "Database query duration",
    ["operation"],  # select/insert/update/delete
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5)
)

DB_CONNECTIONS = Gauge(
    "quantai_db_connections_active",
    "Active database connections"
)

DB_SLOW_QUERIES = Counter(
    "quantai_db_slow_queries_total",
    "Slow database queries (>100ms)",
    ["operation"]
)

# Worker Metrics
WORKER_JOB_DURATION = Histogram(
    "quantai_worker_job_duration_seconds",
    "Background job duration",
    ["job_type"],
    buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0)
)

WORKER_JOB_FAILURES = Counter(
    "quantai_worker_job_failures_total",
    "Background job failures",
    ["job_type"]
)

WORKER_JOBS_IN_PROGRESS = Gauge(
    "quantai_worker_jobs_in_progress",
    "Number of jobs currently running",
    ["job_type"]
)

WORKER_LAST_SUCCESS = Gauge(
    "quantai_worker_last_success_timestamp",
    "Timestamp of last successful job",
    ["job_type"]
)

# Circuit Breaker Metrics
CIRCUIT_BREAKER_STATE = Gauge(
    "quantai_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half-open)",
    ["name"]
)

CIRCUIT_BREAKER_REJECTIONS = Counter(
    "quantai_circuit_breaker_rejections_total",
    "Requests rejected by circuit breaker",
    ["name"]
)

# External API Metrics
EXTERNAL_API_LATENCY = Histogram(
    "quantai_external_api_duration_seconds",
    "External API call duration",
    ["service"],  # upstox, gemini, yfinance
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0)
)

EXTERNAL_API_ERRORS = Counter(
    "quantai_external_api_errors_total",
    "External API errors",
    ["service", "error_type"]
)


# =============================================================================
# Metrics Registry
# =============================================================================

class MetricsRegistry:
    """
    Central registry for all application metrics.
    Provides helper methods for common instrumentation patterns.
    """
    
    def __init__(self):
        self._enabled = get_observability_config().metrics_enabled
    
    @property
    def enabled(self) -> bool:
        return self._enabled and PROMETHEUS_AVAILABLE
    
    def record_request(self, route: str, method: str, status: int, duration: float) -> None:
        """Record an API request."""
        if not self.enabled:
            return
        API_REQUEST_COUNT.labels(route=route, method=method, status=str(status)).inc()
        API_REQUEST_LATENCY.labels(route=route, method=method).observe(duration)
    
    def record_error(self, route: str, error_code: str) -> None:
        """Record an API error."""
        if not self.enabled:
            return
        API_ERRORS.labels(route=route, error_code=error_code).inc()
    
    def record_cache_operation(self, operation: str, status: str, duration: float) -> None:
        """Record a cache operation."""
        if not self.enabled:
            return
        CACHE_OPERATIONS.labels(operation=operation, status=status).inc()
        CACHE_LATENCY.labels(operation=operation).observe(duration)
    
    def record_db_query(self, operation: str, duration: float) -> None:
        """Record a database query."""
        if not self.enabled:
            return
        DB_QUERY_LATENCY.labels(operation=operation).observe(duration)
        config = get_observability_config()
        if duration * 1000 > config.slow_query_threshold_ms:
            DB_SLOW_QUERIES.labels(operation=operation).inc()
    
    def record_worker_job(self, job_type: str, duration: float, success: bool) -> None:
        """Record a background job execution."""
        if not self.enabled:
            return
        WORKER_JOB_DURATION.labels(job_type=job_type).observe(duration)
        if success:
            WORKER_LAST_SUCCESS.labels(job_type=job_type).set(time.time())
        else:
            WORKER_JOB_FAILURES.labels(job_type=job_type).inc()
    
    def set_circuit_state(self, name: str, state: str) -> None:
        """Update circuit breaker state."""
        if not self.enabled:
            return
        state_value = {"closed": 0, "open": 1, "half_open": 2}.get(state, 0)
        CIRCUIT_BREAKER_STATE.labels(name=name).set(state_value)
    
    def record_circuit_rejection(self, name: str) -> None:
        """Record a circuit breaker rejection."""
        if not self.enabled:
            return
        CIRCUIT_BREAKER_REJECTIONS.labels(name=name).inc()
    
    def record_external_api(self, service: str, duration: float, error_type: Optional[str] = None) -> None:
        """Record an external API call."""
        if not self.enabled:
            return
        EXTERNAL_API_LATENCY.labels(service=service).observe(duration)
        if error_type:
            EXTERNAL_API_ERRORS.labels(service=service, error_type=error_type).inc()
    
    def get_metrics_output(self) -> bytes:
        """Generate Prometheus metrics output."""
        if not PROMETHEUS_AVAILABLE:
            return b"# prometheus_client not installed\n"
        return generate_latest()
    
    def get_content_type(self) -> str:
        """Get Prometheus content type."""
        return CONTENT_TYPE_LATEST


# Singleton instance
_metrics: Optional[MetricsRegistry] = None


def get_metrics() -> MetricsRegistry:
    """Get the metrics registry singleton."""
    global _metrics
    if _metrics is None:
        _metrics = MetricsRegistry()
    return _metrics


# =============================================================================
# Decorators
# =============================================================================

def timed_operation(operation_type: str = "db", operation_name: str = "query"):
    """
    Decorator to time and record operations.
    
    Usage:
        @timed_operation("db", "select_users")
        async def get_users():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                duration = time.perf_counter() - start
                if operation_type == "db":
                    get_metrics().record_db_query(operation_name, duration)
                return result
            except Exception as e:
                duration = time.perf_counter() - start
                if operation_type == "db":
                    get_metrics().record_db_query(operation_name, duration)
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration = time.perf_counter() - start
                if operation_type == "db":
                    get_metrics().record_db_query(operation_name, duration)
                return result
            except Exception as e:
                duration = time.perf_counter() - start
                if operation_type == "db":
                    get_metrics().record_db_query(operation_name, duration)
                raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator
