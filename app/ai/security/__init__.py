"""
AI Security Layer

Comprehensive security for AI operations:
- Prompt injection detection and prevention
- Input sanitization
- Output validation
- Rate limiting
- Abuse prevention
- Red-team test patterns
"""
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import re
import hashlib


class ThreatLevel(str, Enum):
    """Security threat levels"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatType(str, Enum):
    """Types of security threats"""
    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK_ATTEMPT = "jailbreak_attempt"
    PII_EXPOSURE = "pii_exposure"
    MALICIOUS_INPUT = "malicious_input"
    RATE_LIMIT_ABUSE = "rate_limit_abuse"
    OUTPUT_MANIPULATION = "output_manipulation"


@dataclass
class SecurityScanResult:
    """Result of a security scan"""
    is_safe: bool
    threat_level: ThreatLevel
    threats_detected: List[Tuple[ThreatType, str]]  # (type, description)
    sanitized_input: Optional[str] = None
    scan_time_ms: float = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_safe": self.is_safe,
            "threat_level": self.threat_level.value,
            "threats": [
                {"type": t.value, "description": d}
                for t, d in self.threats_detected
            ]
        }


# =============================================================================
# PROMPT INJECTION PATTERNS
# =============================================================================

INJECTION_PATTERNS = [
    # Direct instruction override
    (r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?)", ThreatLevel.CRITICAL),
    (r"disregard\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?)", ThreatLevel.CRITICAL),
    (r"forget\s+(everything|all)\s+(above|before)", ThreatLevel.CRITICAL),
    
    # Role manipulation
    (r"you\s+are\s+(now|actually)\s+a", ThreatLevel.HIGH),
    (r"pretend\s+(you\s+are|to\s+be)", ThreatLevel.HIGH),
    (r"act\s+as\s+(if|though)\s+you", ThreatLevel.HIGH),
    (r"roleplay\s+as", ThreatLevel.MEDIUM),
    
    # System prompt extraction
    (r"(what|show|reveal|display)\s+(is\s+)?your\s+(system\s+)?prompt", ThreatLevel.HIGH),
    (r"(print|output|show)\s+(the\s+)?(system\s+)?(instructions?|prompt)", ThreatLevel.HIGH),
    (r"repeat\s+(the\s+)?(text|prompt)\s+above", ThreatLevel.HIGH),
    
    # Delimiter attacks
    (r"```\s*(system|assistant|user)\s*:", ThreatLevel.CRITICAL),
    (r"\[INST\]|\[/INST\]|\<\|im_start\|\>|\<\|im_end\|\>", ThreatLevel.CRITICAL),
    (r"<\|system\|>|<\|user\|>|<\|assistant\|>", ThreatLevel.CRITICAL),
    
    # Base64/encoding attempts
    (r"base64\s*:\s*[A-Za-z0-9+/=]{20,}", ThreatLevel.HIGH),
    (r"decode\s+(this|the\s+following)", ThreatLevel.MEDIUM),
    
    # Jailbreak keywords
    (r"(DAN|Do\s+Anything\s+Now)", ThreatLevel.CRITICAL),
    (r"jailbreak", ThreatLevel.CRITICAL),
    (r"bypass\s+(safety|filter|restriction)", ThreatLevel.CRITICAL),
]

# PII patterns to redact
PII_PATTERNS = [
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL]"),  # Email
    (r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "[PHONE]"),  # US Phone
    (r"\b\d{3}[-]?\d{2}[-]?\d{4}\b", "[SSN]"),  # SSN
    (r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b", "[CARD]"),  # Credit card
]


class InputSanitizer:
    """
    Sanitizes and validates user input before AI processing.
    
    First line of defense against prompt injection.
    """
    
    def __init__(self, max_input_length: int = 50000):
        self.max_input_length = max_input_length
    
    def sanitize(
        self,
        input_text: str,
        redact_pii: bool = True,
        check_injection: bool = True
    ) -> SecurityScanResult:
        """
        Sanitize input text.
        
        Args:
            input_text: Raw user input
            redact_pii: Whether to redact personally identifiable information
            check_injection: Whether to check for prompt injection
            
        Returns:
            SecurityScanResult with sanitized input
        """
        import time
        start_time = time.time()
        
        threats: List[Tuple[ThreatType, str]] = []
        sanitized = input_text
        
        # Length check
        if len(input_text) > self.max_input_length:
            sanitized = input_text[:self.max_input_length]
            threats.append((
                ThreatType.MALICIOUS_INPUT,
                f"Input truncated from {len(input_text)} to {self.max_input_length} chars"
            ))
        
        # Injection check
        if check_injection:
            injection_threats = self._check_injection(sanitized)
            threats.extend(injection_threats)
        
        # PII redaction
        if redact_pii:
            sanitized = self._redact_pii(sanitized)
        
        # Normalize dangerous characters
        sanitized = self._normalize_text(sanitized)
        
        # Determine overall threat level
        threat_level = self._calculate_threat_level(threats)
        
        scan_time = (time.time() - start_time) * 1000
        
        return SecurityScanResult(
            is_safe=threat_level not in [ThreatLevel.HIGH, ThreatLevel.CRITICAL],
            threat_level=threat_level,
            threats_detected=threats,
            sanitized_input=sanitized,
            scan_time_ms=scan_time
        )
    
    def _check_injection(self, text: str) -> List[Tuple[ThreatType, str]]:
        """Check for prompt injection patterns"""
        threats = []
        text_lower = text.lower()
        
        for pattern, level in INJECTION_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                threats.append((
                    ThreatType.PROMPT_INJECTION,
                    f"Injection pattern detected: {pattern[:30]}... (Level: {level.value})"
                ))
        
        return threats
    
    def _redact_pii(self, text: str) -> str:
        """Redact PII from text"""
        result = text
        for pattern, replacement in PII_PATTERNS:
            result = re.sub(pattern, replacement, result)
        return result
    
    def _normalize_text(self, text: str) -> str:
        """Normalize potentially dangerous text patterns"""
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Normalize unicode tricks
        # (homoglyph attacks, etc.)
        normalizations = [
            ('｜', '|'),
            ('＜', '<'),
            ('＞', '>'),
            ('［', '['),
            ('］', ']'),
        ]
        
        for old, new in normalizations:
            text = text.replace(old, new)
        
        return text
    
    def _calculate_threat_level(
        self,
        threats: List[Tuple[ThreatType, str]]
    ) -> ThreatLevel:
        """Calculate overall threat level"""
        if not threats:
            return ThreatLevel.NONE
        
        # Check for critical/high in threat descriptions
        for threat_type, desc in threats:
            if "CRITICAL" in desc.upper():
                return ThreatLevel.CRITICAL
            if threat_type in [ThreatType.PROMPT_INJECTION, ThreatType.JAILBREAK_ATTEMPT]:
                if "CRITICAL" in desc or "HIGH" in desc:
                    return ThreatLevel.HIGH
        
        if len(threats) >= 3:
            return ThreatLevel.HIGH
        elif len(threats) >= 2:
            return ThreatLevel.MEDIUM
        else:
            return ThreatLevel.LOW


class OutputValidator:
    """
    Validates AI output before returning to user.
    
    Last line of defense against harmful outputs.
    """
    
    # Patterns that should never appear in output
    FORBIDDEN_OUTPUT_PATTERNS = [
        # System prompt leakage
        r"(system\s+prompt|my\s+instructions\s+are)",
        r"I('m| am)\s+programmed\s+to",
        
        # Harmful content markers
        r"(here('s|s)\s+how\s+to\s+hack|bypass\s+security)",
        
        # Excessive certainty about outcomes
        r"(guaranteed|will\s+definitely)\s+(get|land|receive)\s+(the\s+)?job",
        r"100%\s+(success|chance|certain)",
    ]
    
    def validate(
        self,
        output: str,
        context: Optional[Dict[str, Any]] = None
    ) -> SecurityScanResult:
        """Validate AI output"""
        import time
        start_time = time.time()
        
        threats = []
        
        # Check forbidden patterns
        for pattern in self.FORBIDDEN_OUTPUT_PATTERNS:
            if re.search(pattern, output, re.IGNORECASE):
                threats.append((
                    ThreatType.OUTPUT_MANIPULATION,
                    f"Forbidden output pattern: {pattern[:30]}..."
                ))
        
        # Check for potential system prompt leakage
        if context and "system_prompt" in context:
            system_prompt = context["system_prompt"]
            if self._check_leakage(output, system_prompt):
                threats.append((
                    ThreatType.OUTPUT_MANIPULATION,
                    "Possible system prompt leakage detected"
                ))
        
        threat_level = ThreatLevel.CRITICAL if threats else ThreatLevel.NONE
        scan_time = (time.time() - start_time) * 1000
        
        return SecurityScanResult(
            is_safe=len(threats) == 0,
            threat_level=threat_level,
            threats_detected=threats,
            scan_time_ms=scan_time
        )
    
    def _check_leakage(self, output: str, system_prompt: str) -> bool:
        """Check if system prompt leaked into output"""
        # Check for significant overlap
        system_words = set(system_prompt.lower().split())
        output_words = set(output.lower().split())
        
        # Remove common words
        common = {"the", "a", "an", "is", "are", "to", "and", "or", "you", "your"}
        system_words -= common
        output_words -= common
        
        if len(system_words) == 0:
            return False
        
        overlap = len(system_words.intersection(output_words)) / len(system_words)
        
        # If >30% of system prompt words appear in output, flag it
        return overlap > 0.3


class RateLimiter:
    """
    Rate limiting for AI operations.
    
    Prevents abuse and controls costs.
    """
    
    def __init__(
        self,
        requests_per_minute: int = 20,
        requests_per_hour: int = 200,
        requests_per_day: int = 1000
    ):
        self.limits = {
            "minute": (requests_per_minute, timedelta(minutes=1)),
            "hour": (requests_per_hour, timedelta(hours=1)),
            "day": (requests_per_day, timedelta(days=1))
        }
        
        self.request_log: Dict[str, List[datetime]] = {}  # user_id -> timestamps
    
    def check_limit(self, user_id: str) -> Tuple[bool, Optional[str]]:
        """
        Check if user is within rate limits.
        
        Returns:
            (is_allowed, reason_if_blocked)
        """
        now = datetime.utcnow()
        
        if user_id not in self.request_log:
            self.request_log[user_id] = []
        
        # Clean old entries
        self._clean_old_entries(user_id, now)
        
        user_requests = self.request_log[user_id]
        
        for limit_name, (limit_count, limit_window) in self.limits.items():
            cutoff = now - limit_window
            recent_count = sum(1 for ts in user_requests if ts > cutoff)
            
            if recent_count >= limit_count:
                return False, f"Rate limit exceeded: {limit_count} requests per {limit_name}"
        
        return True, None
    
    def record_request(self, user_id: str) -> None:
        """Record a request for rate limiting"""
        if user_id not in self.request_log:
            self.request_log[user_id] = []
        
        self.request_log[user_id].append(datetime.utcnow())
    
    def _clean_old_entries(self, user_id: str, now: datetime) -> None:
        """Remove entries older than longest limit window"""
        if user_id not in self.request_log:
            return
        
        oldest_relevant = now - timedelta(days=1)
        self.request_log[user_id] = [
            ts for ts in self.request_log[user_id]
            if ts > oldest_relevant
        ]


class SecurityGateway:
    """
    Main security gateway that coordinates all security components.
    
    Use this as the single entry point for security operations.
    """
    
    def __init__(self):
        self.input_sanitizer = InputSanitizer()
        self.output_validator = OutputValidator()
        self.rate_limiter = RateLimiter()
        
        # Security event log
        self._security_events: List[Dict[str, Any]] = []
    
    async def process_input(
        self,
        user_id: str,
        input_text: str
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Process and validate input.
        
        Args:
            user_id: User making the request
            input_text: Raw input text
            
        Returns:
            (is_allowed, sanitized_input_or_error, error_message)
        """
        # Rate limit check
        allowed, limit_reason = self.rate_limiter.check_limit(user_id)
        if not allowed:
            self._log_event(user_id, "rate_limit", limit_reason)
            return False, "", limit_reason
        
        # Input sanitization
        scan_result = self.input_sanitizer.sanitize(input_text)
        
        if not scan_result.is_safe:
            self._log_event(user_id, "input_blocked", scan_result.to_dict())
            return False, "", f"Input blocked: {scan_result.threat_level.value} threat detected"
        
        # Record the request
        self.rate_limiter.record_request(user_id)
        
        return True, scan_result.sanitized_input or input_text, None
    
    def validate_output(
        self,
        output: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """
        Validate AI output before returning to user.
        
        Returns:
            (is_safe, output_or_error)
        """
        result = self.output_validator.validate(output, context)
        
        if not result.is_safe:
            return False, "Output validation failed. Please try again."
        
        return True, output
    
    def _log_event(
        self,
        user_id: str,
        event_type: str,
        details: Any
    ) -> None:
        """Log security event"""
        self._security_events.append({
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "event_type": event_type,
            "details": details
        })
    
    def get_security_events(
        self,
        user_id: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get security events for monitoring"""
        events = self._security_events
        
        if user_id:
            events = [e for e in events if e["user_id"] == user_id]
        
        if since:
            events = [
                e for e in events
                if datetime.fromisoformat(e["timestamp"]) >= since
            ]
        
        return events


# Global security gateway
_security_gateway: Optional[SecurityGateway] = None


def get_security_gateway() -> SecurityGateway:
    """Get the global security gateway"""
    global _security_gateway
    if _security_gateway is None:
        _security_gateway = SecurityGateway()
    return _security_gateway
