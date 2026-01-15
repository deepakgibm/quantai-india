"""
Observability Configuration

Centralized configuration for all observability features.
All settings can be overridden via environment variables.
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ObservabilityConfig:
    """Configuration for observability features."""
    
    # Logging
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    log_format: str = field(default_factory=lambda: os.getenv("LOG_FORMAT", "json"))  # "json" or "text"
    log_include_timestamp: bool = True
    log_include_caller: bool = True
    
    # Metrics
    metrics_enabled: bool = field(default_factory=lambda: os.getenv("METRICS_ENABLED", "true").lower() == "true")
    metrics_prefix: str = "quantai"
    
    # Tracing
    tracing_enabled: bool = field(default_factory=lambda: os.getenv("TRACING_ENABLED", "true").lower() == "true")
    trace_sample_rate: float = field(default_factory=lambda: float(os.getenv("TRACE_SAMPLE_RATE", "0.1")))
    
    # Correlation
    correlation_header: str = "X-Correlation-ID"
    
    # Performance
    slow_query_threshold_ms: int = field(default_factory=lambda: int(os.getenv("SLOW_QUERY_THRESHOLD_MS", "100")))
    slow_request_threshold_ms: int = field(default_factory=lambda: int(os.getenv("SLOW_REQUEST_THRESHOLD_MS", "500")))
    
    # Alert thresholds (documentation only - for external alerting systems)
    alert_api_latency_p95_ms: int = 500
    alert_api_error_rate_pct: float = 5.0
    alert_cache_hit_rate_min_pct: float = 60.0
    alert_circuit_open_duration_s: int = 300
    alert_worker_failure_rate_pct: float = 10.0


# Singleton instance
_config: Optional[ObservabilityConfig] = None


def get_observability_config() -> ObservabilityConfig:
    """Get the observability configuration singleton."""
    global _config
    if _config is None:
        _config = ObservabilityConfig()
    return _config


def reset_config() -> None:
    """Reset configuration (for testing)."""
    global _config
    _config = None
