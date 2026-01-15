"""
Structured Logging

Provides structured JSON logging with automatic context injection.
Includes correlation ID, route, user info, and timing data.
"""

import json
import logging
import sys
import time
from datetime import datetime
from typing import Any, Dict, Optional

from core.observability.correlation import get_correlation_id
from core.observability.config import get_observability_config


class StructuredFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    
    Output format:
    {
        "timestamp": "2024-01-14T12:00:00.000Z",
        "level": "INFO",
        "logger": "module.name",
        "message": "Log message",
        "correlation_id": "abc123",
        "extra": {...}
    }
    """
    
    # Fields that should never be logged (security)
    SENSITIVE_FIELDS = {
        "password", "token", "secret", "api_key", "authorization",
        "access_token", "refresh_token", "bearer", "credential"
    }
    
    def __init__(self, include_timestamp: bool = True, include_caller: bool = True):
        super().__init__()
        self.include_timestamp = include_timestamp
        self.include_caller = include_caller
    
    def _sanitize(self, data: Any) -> Any:
        """Remove sensitive fields from log data."""
        if isinstance(data, dict):
            return {
                k: "[REDACTED]" if k.lower() in self.SENSITIVE_FIELDS else self._sanitize(v)
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [self._sanitize(item) for item in data]
        return data
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {}
        
        # Timestamp
        if self.include_timestamp:
            log_entry["timestamp"] = datetime.utcnow().isoformat() + "Z"
        
        # Standard fields
        log_entry["level"] = record.levelname
        log_entry["logger"] = record.name
        log_entry["message"] = record.getMessage()
        
        # Correlation ID (auto-injected from context)
        correlation_id = get_correlation_id()
        if correlation_id:
            log_entry["correlation_id"] = correlation_id
        
        # Caller info
        if self.include_caller:
            log_entry["caller"] = {
                "file": record.filename,
                "line": record.lineno,
                "function": record.funcName
            }
        
        # Exception info
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Extra fields (from logger.info("msg", extra={...}))
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "exc_info", "exc_text", "thread", "threadName",
                "message", "taskName"
            }:
                extra_fields[key] = value
        
        if extra_fields:
            log_entry["extra"] = self._sanitize(extra_fields)
        
        return json.dumps(log_entry, default=str)


class TextFormatter(logging.Formatter):
    """
    Human-readable formatter for development.
    
    Output format:
    2024-01-14 12:00:00 [INFO] [abc123] module.name: Log message
    """
    
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        correlation_id = get_correlation_id() or "-"
        
        base = f"{timestamp} [{record.levelname}] [{correlation_id}] {record.name}: {record.getMessage()}"
        
        if record.exc_info:
            base += "\n" + self.formatException(record.exc_info)
        
        return base


class ContextLogger:
    """
    Logger wrapper that automatically includes context in all log calls.
    
    Usage:
        logger = get_logger(__name__)
        logger.info("Processing request", route="/api/scanner", symbol="RELIANCE")
    """
    
    def __init__(self, logger: logging.Logger):
        self._logger = logger
    
    def _log(self, level: int, msg: str, **kwargs) -> None:
        extra = kwargs if kwargs else {}
        self._logger.log(level, msg, extra=extra)
    
    def debug(self, msg: str, **kwargs) -> None:
        self._log(logging.DEBUG, msg, **kwargs)
    
    def info(self, msg: str, **kwargs) -> None:
        self._log(logging.INFO, msg, **kwargs)
    
    def warning(self, msg: str, **kwargs) -> None:
        self._log(logging.WARNING, msg, **kwargs)
    
    def error(self, msg: str, exc_info: bool = False, **kwargs) -> None:
        self._logger.error(msg, exc_info=exc_info, extra=kwargs)
    
    def critical(self, msg: str, exc_info: bool = False, **kwargs) -> None:
        self._logger.critical(msg, exc_info=exc_info, extra=kwargs)
    
    def exception(self, msg: str, **kwargs) -> None:
        self._logger.exception(msg, extra=kwargs)


# Logger cache
_loggers: Dict[str, ContextLogger] = {}


def configure_logging() -> None:
    """
    Configure the root logger with structured formatting.
    
    Should be called once at application startup.
    """
    config = get_observability_config()
    
    # Get/create root handler
    root = logging.getLogger()
    root.setLevel(getattr(logging, config.log_level.upper(), logging.INFO))
    
    # Remove existing handlers
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    
    # Create new handler
    handler = logging.StreamHandler(sys.stdout)
    
    if config.log_format == "json":
        handler.setFormatter(StructuredFormatter(
            include_timestamp=config.log_include_timestamp,
            include_caller=config.log_include_caller
        ))
    else:
        handler.setFormatter(TextFormatter())
    
    root.addHandler(handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> ContextLogger:
    """
    Get a context-aware logger.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        ContextLogger instance
    """
    if name not in _loggers:
        _loggers[name] = ContextLogger(logging.getLogger(name))
    return _loggers[name]


class LogTimer:
    """
    Context manager for timing operations with logging.
    
    Usage:
        with LogTimer(logger, "database_query", table="users"):
            result = db.query(...)
    """
    
    def __init__(self, logger: ContextLogger, operation: str, **context):
        self.logger = logger
        self.operation = operation
        self.context = context
        self.start_time: Optional[float] = None
    
    def __enter__(self) -> "LogTimer":
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.perf_counter() - self.start_time) * 1000
        
        if exc_type:
            self.logger.error(
                f"{self.operation} failed",
                duration_ms=round(duration_ms, 2),
                error=str(exc_val),
                **self.context
            )
        else:
            config = get_observability_config()
            level = "warning" if duration_ms > config.slow_request_threshold_ms else "info"
            getattr(self.logger, level)(
                f"{self.operation} completed",
                duration_ms=round(duration_ms, 2),
                **self.context
            )
        
        return False
