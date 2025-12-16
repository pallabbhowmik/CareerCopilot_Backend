"""
Observability Middleware

Request tracing, structured logging, and performance monitoring.
"""
from typing import Callable, Dict, Any, Optional
from datetime import datetime
import uuid
import time
import json
import logging
import sys
from contextvars import ContextVar

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


# Context variable for request ID propagation
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


# =============================================================================
# STRUCTURED LOGGING
# =============================================================================

class StructuredLogger:
    """
    JSON-structured logger for production observability.
    
    All logs include:
    - Timestamp
    - Level
    - Request ID
    - Service name
    - Structured context
    """
    
    def __init__(self, service_name: str = "careercopilot-api"):
        self.service_name = service_name
        self.logger = logging.getLogger(service_name)
        
        # Configure JSON handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def _build_log_record(
        self,
        level: str,
        message: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Build structured log record"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "service": self.service_name,
            "request_id": request_id_var.get() or None,
            "message": message,
            **kwargs
        }
    
    def info(self, message: str, **kwargs):
        record = self._build_log_record("INFO", message, **kwargs)
        self.logger.info(json.dumps(record))
    
    def warning(self, message: str, **kwargs):
        record = self._build_log_record("WARNING", message, **kwargs)
        self.logger.warning(json.dumps(record))
    
    def error(self, message: str, **kwargs):
        record = self._build_log_record("ERROR", message, **kwargs)
        self.logger.error(json.dumps(record))
    
    def debug(self, message: str, **kwargs):
        record = self._build_log_record("DEBUG", message, **kwargs)
        self.logger.debug(json.dumps(record))


class StructuredFormatter(logging.Formatter):
    """Custom formatter that passes through pre-formatted JSON"""
    
    def format(self, record: logging.LogRecord) -> str:
        return record.getMessage()


# Global logger instance
logger = StructuredLogger()


# =============================================================================
# REQUEST TRACING
# =============================================================================

class RequestTracingMiddleware(BaseHTTPMiddleware):
    """
    Assigns unique request IDs and traces requests through the system.
    
    Features:
    - Unique request ID generation
    - Request/response logging
    - Distributed tracing support
    - User context propagation
    """
    
    def __init__(self, app, log_bodies: bool = False):
        super().__init__(app)
        self.log_bodies = log_bodies
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Set context variable for propagation
        request_id_var.set(request_id)
        
        # Store on request state
        request.state.request_id = request_id
        
        # Extract user info if available
        user_id = getattr(request.state, "user_id", None)
        
        # Log request start
        logger.info(
            "Request started",
            request_id=request_id,
            method=request.method,
            path=str(request.url.path),
            query=str(request.url.query) if request.url.query else None,
            user_id=user_id,
            client_ip=self._get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )
        
        # Process request
        start_time = time.perf_counter()
        
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            # Log request completion
            logger.info(
                "Request completed",
                request_id=request_id,
                method=request.method,
                path=str(request.url.path),
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
                user_id=user_id
            )
            
            # Add tracing headers to response
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
            
            return response
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            logger.error(
                "Request failed",
                request_id=request_id,
                method=request.method,
                path=str(request.url.path),
                duration_ms=round(duration_ms, 2),
                error_type=type(e).__name__,
                error_message=str(e),
                user_id=user_id
            )
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"


# =============================================================================
# STRUCTURED LOGGING MIDDLEWARE
# =============================================================================

class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """
    Ensures all log output is structured JSON.
    
    Captures and formats:
    - Application logs
    - Framework logs
    - Error traces
    """
    
    def __init__(self, app, log_level: str = "INFO"):
        super().__init__(app)
        
        # Configure root logger
        logging.basicConfig(
            level=getattr(logging, log_level),
            format="%(message)s",
            handlers=[logging.StreamHandler(sys.stdout)]
        )
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        return await call_next(request)


# =============================================================================
# PERFORMANCE MONITORING
# =============================================================================

class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Monitors request performance and resource usage.
    
    Features:
    - Request duration tracking
    - Slow request detection
    - Memory usage monitoring
    - Database query counting (via hooks)
    """
    
    SLOW_REQUEST_THRESHOLD_MS = 1000  # 1 second
    
    def __init__(
        self,
        app,
        slow_threshold_ms: int = 1000,
        enable_memory_tracking: bool = False
    ):
        super().__init__(app)
        self.slow_threshold_ms = slow_threshold_ms
        self.enable_memory_tracking = enable_memory_tracking
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()
        
        # Track memory if enabled
        start_memory = None
        if self.enable_memory_tracking:
            try:
                import psutil
                process = psutil.Process()
                start_memory = process.memory_info().rss
            except ImportError:
                pass
        
        # Initialize metrics
        request.state.metrics = {
            "start_time": start_time,
            "db_query_count": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        try:
            response = await call_next(request)
            
            # Calculate metrics
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            # Check for slow request
            if duration_ms > self.slow_threshold_ms:
                logger.warning(
                    "Slow request detected",
                    request_id=getattr(request.state, "request_id", None),
                    path=str(request.url.path),
                    method=request.method,
                    duration_ms=round(duration_ms, 2),
                    threshold_ms=self.slow_threshold_ms,
                    db_queries=request.state.metrics.get("db_query_count", 0)
                )
            
            # Add performance headers
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
            
            if self.enable_memory_tracking and start_memory:
                try:
                    import psutil
                    process = psutil.Process()
                    end_memory = process.memory_info().rss
                    memory_delta = end_memory - start_memory
                    response.headers["X-Memory-Delta"] = str(memory_delta)
                except ImportError:
                    pass
            
            return response
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            logger.error(
                "Request error with performance data",
                request_id=getattr(request.state, "request_id", None),
                path=str(request.url.path),
                duration_ms=round(duration_ms, 2),
                error=str(e)
            )
            raise


# =============================================================================
# METRICS HELPER
# =============================================================================

class MetricsCollector:
    """
    Collects and aggregates metrics for monitoring.
    
    In production, this would integrate with Prometheus, DataDog, etc.
    """
    
    def __init__(self):
        self.request_count = 0
        self.error_count = 0
        self.total_duration_ms = 0
        self.slow_requests = 0
        self.endpoint_stats: Dict[str, Dict[str, Any]] = {}
    
    def record_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        duration_ms: float
    ):
        """Record a request for metrics"""
        self.request_count += 1
        self.total_duration_ms += duration_ms
        
        if status_code >= 400:
            self.error_count += 1
        
        if duration_ms > PerformanceMonitoringMiddleware.SLOW_REQUEST_THRESHOLD_MS:
            self.slow_requests += 1
        
        # Per-endpoint stats
        key = f"{method}:{endpoint}"
        if key not in self.endpoint_stats:
            self.endpoint_stats[key] = {
                "count": 0,
                "total_ms": 0,
                "errors": 0
            }
        
        self.endpoint_stats[key]["count"] += 1
        self.endpoint_stats[key]["total_ms"] += duration_ms
        if status_code >= 400:
            self.endpoint_stats[key]["errors"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current metrics"""
        avg_duration = (
            self.total_duration_ms / self.request_count
            if self.request_count > 0 else 0
        )
        
        return {
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate": self.error_count / self.request_count if self.request_count > 0 else 0,
            "avg_duration_ms": round(avg_duration, 2),
            "slow_requests": self.slow_requests,
            "endpoints": self.endpoint_stats
        }


# Global metrics collector
metrics = MetricsCollector()
