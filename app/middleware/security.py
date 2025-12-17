"""
Security Middleware

Rate limiting, input sanitization, and security headers.
"""
from typing import Callable, Dict, Any, Optional, List
from datetime import datetime, timedelta
import re
import json
import hashlib
import html
from collections import defaultdict

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


# =============================================================================
# RATE LIMITING
# =============================================================================

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Token bucket rate limiting middleware.
    
    Configurable limits per endpoint pattern.
    Supports user-specific and IP-based limits.
    """
    
    def __init__(
        self,
        app,
        default_rate: int = 100,  # Requests per minute
        default_burst: int = 20,  # Burst allowance
        endpoint_limits: Optional[Dict[str, Dict[str, int]]] = None,
        exempt_paths: Optional[List[str]] = None
    ):
        super().__init__(app)
        self.default_rate = default_rate
        self.default_burst = default_burst
        self.endpoint_limits = endpoint_limits or {}
        self.exempt_paths = exempt_paths or ["/health", "/docs", "/openapi.json"]
        
        # In-memory bucket storage (use Redis in production)
        self.buckets: Dict[str, Dict[str, Any]] = defaultdict(dict)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for exempt paths
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)
        
        # Get identifier (user_id from auth or IP)
        identifier = self._get_identifier(request)
        
        # Get limits for this endpoint
        rate, burst = self._get_limits(request.url.path)
        
        # Check rate limit
        allowed, remaining, reset_at = self._check_rate_limit(identifier, rate, burst)
        
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests. Please slow down.",
                    "retry_after_seconds": int((reset_at - datetime.utcnow()).total_seconds()),
                    "limit": rate,
                    "remaining": 0
                },
                headers={
                    "Retry-After": str(int((reset_at - datetime.utcnow()).total_seconds())),
                    "X-RateLimit-Limit": str(rate),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": reset_at.isoformat()
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(rate)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = reset_at.isoformat()
        
        return response
    
    def _get_identifier(self, request: Request) -> str:
        """Get unique identifier for rate limiting"""
        # Try to get user_id from auth state
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"
        
        # Fall back to IP
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"
        
        return f"ip:{ip}"
    
    def _get_limits(self, path: str) -> tuple:
        """Get rate limits for a specific path"""
        for pattern, limits in self.endpoint_limits.items():
            if re.match(pattern, path):
                return limits.get("rate", self.default_rate), limits.get("burst", self.default_burst)
        return self.default_rate, self.default_burst
    
    def _check_rate_limit(
        self,
        identifier: str,
        rate: int,
        burst: int
    ) -> tuple:
        """
        Token bucket rate limit check.
        
        Returns: (allowed: bool, remaining: int, reset_at: datetime)
        """
        now = datetime.utcnow()
        bucket = self.buckets[identifier]
        
        # Initialize bucket if needed
        if "tokens" not in bucket:
            bucket["tokens"] = burst
            bucket["last_update"] = now
        
        # Refill tokens based on time passed
        time_passed = (now - bucket["last_update"]).total_seconds()
        tokens_to_add = (time_passed / 60) * rate  # tokens per minute
        bucket["tokens"] = min(burst, bucket["tokens"] + tokens_to_add)
        bucket["last_update"] = now
        
        # Check if we can allow the request
        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            remaining = int(bucket["tokens"])
            reset_at = now + timedelta(minutes=1)
            return True, remaining, reset_at
        else:
            reset_at = now + timedelta(seconds=(1 - bucket["tokens"]) * 60 / rate)
            return False, 0, reset_at


# =============================================================================
# INPUT SANITIZATION
# =============================================================================

class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """
    Sanitizes user input to prevent injection attacks.
    
    - HTML escaping
    - SQL injection prevention
    - XSS prevention
    - Size limits
    """
    
    MAX_BODY_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_STRING_LENGTH = 100000  # 100k chars
    
    # Patterns that indicate potential attacks
    SUSPICIOUS_PATTERNS = [
        r"<script[^>]*>",  # Script tags
        r"javascript:",  # JavaScript protocol
        r"on\w+\s*=",  # Event handlers
        r"union\s+select",  # SQL injection
        r";\s*drop\s+",  # SQL injection
        r"\$\{.*\}",  # Template injection
        r"{{.*}}",  # Template injection
    ]
    
    def __init__(self, app, strict_mode: bool = False):
        super().__init__(app)
        self.strict_mode = strict_mode
        self.patterns = [re.compile(p, re.IGNORECASE) for p in self.SUSPICIOUS_PATTERNS]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.MAX_BODY_SIZE:
            return JSONResponse(
                status_code=413,
                content={"error": "payload_too_large", "message": "Request body too large"}
            )
        
        # For POST/PUT/PATCH, sanitize body
        # Skip multipart/form-data (file uploads) as reading the body would consume the stream
        # and binary data shouldn't be sanitized as text
        content_type = request.headers.get("content-type", "")
        if request.method in ["POST", "PUT", "PATCH"] and not content_type.startswith("multipart/form-data"):
            try:
                body = await request.body()
                if body:
                    sanitized = self._sanitize_body(body)
                    if sanitized is None:
                        return JSONResponse(
                            status_code=400,
                            content={"error": "invalid_input", "message": "Request contains invalid characters"}
                        )
                    
                    # Store sanitized body for later use
                    request.state.sanitized_body = sanitized
            except Exception:
                pass
        
        return await call_next(request)
    
    def _sanitize_body(self, body: bytes) -> Optional[bytes]:
        """Sanitize request body"""
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError:
            return None
        
        # Check for suspicious patterns
        for pattern in self.patterns:
            if pattern.search(text):
                if self.strict_mode:
                    return None
                # In non-strict mode, just log and continue
        
        # Try to parse as JSON and sanitize
        try:
            data = json.loads(text)
            sanitized_data = self._sanitize_value(data)
            return json.dumps(sanitized_data).encode("utf-8")
        except json.JSONDecodeError:
            # Not JSON, just do basic sanitization
            sanitized_text = self._sanitize_string(text)
            return sanitized_text.encode("utf-8")
    
    def _sanitize_value(self, value: Any) -> Any:
        """Recursively sanitize a value"""
        if isinstance(value, str):
            return self._sanitize_string(value)
        elif isinstance(value, dict):
            return {k: self._sanitize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._sanitize_value(v) for v in value]
        else:
            return value
    
    def _sanitize_string(self, s: str) -> str:
        """Sanitize a string value"""
        if len(s) > self.MAX_STRING_LENGTH:
            s = s[:self.MAX_STRING_LENGTH]
        
        # HTML escape
        s = html.escape(s)
        
        # Remove null bytes
        s = s.replace("\x00", "")
        
        return s


# =============================================================================
# SECURITY HEADERS
# =============================================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to all responses.
    
    Implements OWASP security header recommendations.
    """
    
    def __init__(
        self,
        app,
        content_security_policy: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None
    ):
        super().__init__(app)
        
        # Default CSP - restrictive for API
        self.csp = content_security_policy or "default-src 'self'; frame-ancestors 'none'"
        self.extra_headers = extra_headers or {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Standard security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = self.csp
        
        # Strict Transport Security (for HTTPS)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Permissions Policy (formerly Feature-Policy)
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Add any extra headers
        for header, value in self.extra_headers.items():
            response.headers[header] = value
        
        return response


# =============================================================================
# CORS HELPER (for reference - actual CORS handled by FastAPI)
# =============================================================================

CORS_CONFIG = {
    "allow_origins": [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://careercopilot.ai",
        "https://www.careercopilot.ai"
    ],
    "allow_credentials": True,
    "allow_methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    "allow_headers": ["*"],
    "expose_headers": [
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
        "X-Request-ID"
    ]
}
