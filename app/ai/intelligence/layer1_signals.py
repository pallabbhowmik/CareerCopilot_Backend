"""
Layer 1 — Deterministic Signal Engine

Pure logic, zero AI. This layer produces FACTS that AI cannot contradict.

Signals are:
- Binary or categorical (not probabilistic)
- Reproducible (same input = same output)
- Auditable (clear reasoning chain)
- Immutable once computed

AI layers MUST respect all Layer 1 signals.
"""
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import re
import hashlib


class SignalType(str, Enum):
    """Categories of deterministic signals"""
    # Resume structure signals
    SECTION_PRESENT = "section_present"
    SECTION_MISSING = "section_missing"
    SECTION_ORDER = "section_order"
    
    # Contact signals
    EMAIL_VALID = "email_valid"
    EMAIL_MISSING = "email_missing"
    PHONE_PRESENT = "phone_present"
    LINKEDIN_PRESENT = "linkedin_present"
    
    # Experience signals
    EXPERIENCE_COUNT = "experience_count"
    EXPERIENCE_DURATION = "experience_duration"
    EMPLOYMENT_GAP = "employment_gap"
    JOB_HOPPING = "job_hopping"
    
    # Bullet signals
    BULLET_COUNT = "bullet_count"
    BULLET_HAS_METRIC = "bullet_has_metric"
    BULLET_HAS_ACTION_VERB = "bullet_has_action_verb"
    BULLET_TOO_LONG = "bullet_too_long"
    BULLET_TOO_SHORT = "bullet_too_short"
    
    # Skill signals
    SKILL_COUNT = "skill_count"
    SKILL_MATCH = "skill_match"
    SKILL_MISSING = "skill_missing"
    SKILL_PARTIAL_MATCH = "skill_partial_match"
    
    # Format signals
    FORMAT_ISSUE = "format_issue"
    SPECIAL_CHARS = "special_chars"
    INCONSISTENT_DATES = "inconsistent_dates"
    
    # ATS signals
    ATS_PARSEABLE = "ats_parseable"
    ATS_RISK = "ats_risk"


class SignalSeverity(str, Enum):
    """How critical is this signal"""
    CRITICAL = "critical"  # Blocks hiring (missing email, unparseable)
    HIGH = "high"          # Strongly negative (no metrics, gaps)
    MEDIUM = "medium"      # Improvement opportunity
    LOW = "low"            # Nice to have
    INFO = "info"          # Neutral information


@dataclass
class Signal:
    """
    A single deterministic signal.
    
    This is a FACT that AI cannot dispute or modify.
    """
    signal_type: SignalType
    severity: SignalSeverity
    value: Any  # The actual value (count, bool, string, etc.)
    
    # Context for explanation
    context: Dict[str, Any] = field(default_factory=dict)
    
    # Where in the resume this signal was found
    source_location: Optional[str] = None
    
    # Human-readable description (deterministic template)
    description: str = ""
    
    # Unique hash for deduplication
    signal_hash: str = field(default="")
    
    # Timestamp for auditing
    computed_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        if not self.signal_hash:
            # Create deterministic hash
            hash_input = f"{self.signal_type}:{self.value}:{self.source_location}"
            self.signal_hash = hashlib.md5(hash_input.encode()).hexdigest()[:12]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_type": self.signal_type.value,
            "severity": self.severity.value,
            "value": self.value,
            "context": self.context,
            "source_location": self.source_location,
            "description": self.description,
            "signal_hash": self.signal_hash,
            "computed_at": self.computed_at.isoformat()
        }


# =============================================================================
# SIGNAL DETECTION RULES (Pure Logic)
# =============================================================================

# Action verbs for bullet analysis
ACTION_VERBS = {
    "achieved", "administered", "analyzed", "built", "collaborated",
    "conducted", "coordinated", "created", "decreased", "delivered",
    "designed", "developed", "directed", "established", "executed",
    "expanded", "generated", "implemented", "improved", "increased",
    "initiated", "launched", "led", "managed", "mentored", "negotiated",
    "optimized", "orchestrated", "organized", "pioneered", "planned",
    "produced", "reduced", "resolved", "scaled", "spearheaded",
    "streamlined", "supervised", "transformed", "upgraded"
}

# Metric patterns
METRIC_PATTERNS = [
    r'\d+%',              # Percentages
    r'\$[\d,]+',          # Dollar amounts
    r'[\d,]+\s*(users|customers|clients|employees|team members)',  # People counts
    r'[\d,]+x',           # Multipliers
    r'\d+\s*(million|billion|k|M|B)',  # Large numbers
    r'#\d+',              # Rankings
    r'\d+\s*(hours?|days?|weeks?|months?|years?)',  # Time savings
]

# Required sections for completeness
REQUIRED_SECTIONS = {"personal_info", "experience", "skills"}
RECOMMENDED_SECTIONS = {"education", "summary"}


class SignalEngine:
    """
    Layer 1: Deterministic Signal Engine
    
    Extracts facts from resume data using pure logic.
    NO AI involvement whatsoever.
    """
    
    def __init__(self):
        self.metric_patterns = [re.compile(p, re.IGNORECASE) for p in METRIC_PATTERNS]
    
    def extract_signals(
        self,
        resume_data: Dict[str, Any],
        job_data: Optional[Dict[str, Any]] = None
    ) -> List[Signal]:
        """
        Extract all deterministic signals from resume data.
        
        Args:
            resume_data: Parsed resume in structured format
            job_data: Optional job description for matching
            
        Returns:
            List of Signal objects (facts)
        """
        signals = []
        
        # Section signals
        signals.extend(self._analyze_sections(resume_data))
        
        # Contact signals
        signals.extend(self._analyze_contact(resume_data.get("personal_info", {})))
        
        # Experience signals
        signals.extend(self._analyze_experience(resume_data.get("experience", [])))
        
        # Bullet signals
        signals.extend(self._analyze_bullets(resume_data.get("experience", [])))
        
        # Skill signals
        signals.extend(self._analyze_skills(
            resume_data.get("skills", []),
            job_data.get("required_skills", []) if job_data else []
        ))
        
        # Format signals
        signals.extend(self._analyze_format(resume_data))
        
        return signals
    
    def _analyze_sections(self, data: Dict[str, Any]) -> List[Signal]:
        """Check for required and recommended sections"""
        signals = []
        present_sections = set()
        
        if data.get("personal_info"):
            present_sections.add("personal_info")
        if data.get("experience"):
            present_sections.add("experience")
        if data.get("skills"):
            present_sections.add("skills")
        if data.get("education"):
            present_sections.add("education")
        if data.get("summary"):
            present_sections.add("summary")
        if data.get("projects"):
            present_sections.add("projects")
        
        # Check required sections
        for section in REQUIRED_SECTIONS:
            if section in present_sections:
                signals.append(Signal(
                    signal_type=SignalType.SECTION_PRESENT,
                    severity=SignalSeverity.INFO,
                    value=section,
                    description=f"Required section '{section}' is present"
                ))
            else:
                signals.append(Signal(
                    signal_type=SignalType.SECTION_MISSING,
                    severity=SignalSeverity.CRITICAL,
                    value=section,
                    description=f"Required section '{section}' is missing"
                ))
        
        # Check recommended sections
        for section in RECOMMENDED_SECTIONS:
            if section not in present_sections:
                signals.append(Signal(
                    signal_type=SignalType.SECTION_MISSING,
                    severity=SignalSeverity.MEDIUM,
                    value=section,
                    description=f"Recommended section '{section}' is missing"
                ))
        
        return signals
    
    def _analyze_contact(self, personal_info: Dict[str, Any]) -> List[Signal]:
        """Analyze contact information completeness"""
        signals = []
        
        # Email check
        email = personal_info.get("email", "")
        if email:
            # Basic email validation
            if re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
                signals.append(Signal(
                    signal_type=SignalType.EMAIL_VALID,
                    severity=SignalSeverity.INFO,
                    value=True,
                    description="Valid email address present"
                ))
            else:
                signals.append(Signal(
                    signal_type=SignalType.EMAIL_VALID,
                    severity=SignalSeverity.HIGH,
                    value=False,
                    context={"email": email},
                    description="Email address format appears invalid"
                ))
        else:
            signals.append(Signal(
                signal_type=SignalType.EMAIL_MISSING,
                severity=SignalSeverity.CRITICAL,
                value=True,
                description="No email address found - critical for recruiter contact"
            ))
        
        # Phone check
        if personal_info.get("phone"):
            signals.append(Signal(
                signal_type=SignalType.PHONE_PRESENT,
                severity=SignalSeverity.INFO,
                value=True,
                description="Phone number present"
            ))
        
        # LinkedIn check
        linkedin = personal_info.get("linkedin", "")
        if linkedin and "linkedin" in linkedin.lower():
            signals.append(Signal(
                signal_type=SignalType.LINKEDIN_PRESENT,
                severity=SignalSeverity.INFO,
                value=True,
                description="LinkedIn profile present"
            ))
        
        return signals
    
    def _analyze_experience(self, experiences: List[Dict[str, Any]]) -> List[Signal]:
        """Analyze work experience patterns"""
        signals = []
        
        # Experience count
        exp_count = len(experiences)
        signals.append(Signal(
            signal_type=SignalType.EXPERIENCE_COUNT,
            severity=SignalSeverity.INFO,
            value=exp_count,
            description=f"{exp_count} work experience entries found"
        ))
        
        if exp_count == 0:
            signals.append(Signal(
                signal_type=SignalType.SECTION_MISSING,
                severity=SignalSeverity.CRITICAL,
                value="experience",
                description="No work experience entries found"
            ))
        
        # Check for short tenures (job hopping)
        short_tenures = 0
        for exp in experiences:
            # Simplified tenure calculation
            start = exp.get("start_date", "")
            end = exp.get("end_date", "Present")
            
            # If we can detect short tenure (< 1 year), flag it
            if start and end and end != "Present":
                # Basic check - if same year, likely short
                if start[:4] == end[:4]:  # Same year
                    short_tenures += 1
        
        if short_tenures >= 3:
            signals.append(Signal(
                signal_type=SignalType.JOB_HOPPING,
                severity=SignalSeverity.MEDIUM,
                value=short_tenures,
                description=f"{short_tenures} positions with potentially short tenure detected"
            ))
        
        return signals
    
    def _analyze_bullets(self, experiences: List[Dict[str, Any]]) -> List[Signal]:
        """Analyze bullet point quality - pure pattern matching"""
        signals = []
        
        total_bullets = 0
        bullets_with_metrics = 0
        bullets_with_verbs = 0
        bullets_too_long = 0
        bullets_too_short = 0
        
        for exp in experiences:
            bullets = exp.get("bullets", [])
            company = exp.get("company", "Unknown")
            
            for i, bullet in enumerate(bullets):
                total_bullets += 1
                text = bullet if isinstance(bullet, str) else bullet.get("text", "")
                
                # Check for metrics
                has_metric = any(p.search(text) for p in self.metric_patterns)
                if has_metric:
                    bullets_with_metrics += 1
                
                # Check for action verb at start
                first_word = text.split()[0].lower() if text else ""
                has_action_verb = first_word in ACTION_VERBS
                if has_action_verb:
                    bullets_with_verbs += 1
                else:
                    signals.append(Signal(
                        signal_type=SignalType.BULLET_HAS_ACTION_VERB,
                        severity=SignalSeverity.LOW,
                        value=False,
                        source_location=f"{company}, bullet {i+1}",
                        context={"text": text[:100], "first_word": first_word},
                        description=f"Bullet does not start with strong action verb"
                    ))
                
                # Length checks
                if len(text) > 200:
                    bullets_too_long += 1
                    signals.append(Signal(
                        signal_type=SignalType.BULLET_TOO_LONG,
                        severity=SignalSeverity.LOW,
                        value=len(text),
                        source_location=f"{company}, bullet {i+1}",
                        description=f"Bullet is {len(text)} characters (recommend < 200)"
                    ))
                elif len(text) < 30:
                    bullets_too_short += 1
        
        # Aggregate signals
        if total_bullets > 0:
            metric_pct = (bullets_with_metrics / total_bullets) * 100
            verb_pct = (bullets_with_verbs / total_bullets) * 100
            
            signals.append(Signal(
                signal_type=SignalType.BULLET_COUNT,
                severity=SignalSeverity.INFO,
                value=total_bullets,
                context={
                    "with_metrics": bullets_with_metrics,
                    "metric_percentage": round(metric_pct, 1),
                    "with_action_verbs": bullets_with_verbs,
                    "verb_percentage": round(verb_pct, 1)
                },
                description=f"{total_bullets} bullets: {metric_pct:.0f}% have metrics, {verb_pct:.0f}% start with action verbs"
            ))
            
            # Flag low metric usage
            if metric_pct < 30:
                signals.append(Signal(
                    signal_type=SignalType.BULLET_HAS_METRIC,
                    severity=SignalSeverity.HIGH,
                    value=False,
                    context={"percentage": metric_pct},
                    description=f"Only {metric_pct:.0f}% of bullets contain quantifiable metrics"
                ))
        
        return signals
    
    def _analyze_skills(
        self,
        resume_skills: List[str],
        job_skills: List[str]
    ) -> List[Signal]:
        """Analyze skill presence and matching"""
        signals = []
        
        # Skill count
        skill_count = len(resume_skills)
        signals.append(Signal(
            signal_type=SignalType.SKILL_COUNT,
            severity=SignalSeverity.INFO,
            value=skill_count,
            description=f"{skill_count} skills listed"
        ))
        
        if skill_count < 5:
            signals.append(Signal(
                signal_type=SignalType.SKILL_COUNT,
                severity=SignalSeverity.MEDIUM,
                value=skill_count,
                description=f"Only {skill_count} skills listed (recommend 8-15)"
            ))
        
        # Job skill matching (if job provided)
        if job_skills:
            resume_skills_lower = {s.lower() for s in resume_skills}
            
            matched = []
            missing = []
            
            for skill in job_skills:
                skill_lower = skill.lower()
                if skill_lower in resume_skills_lower:
                    matched.append(skill)
                else:
                    missing.append(skill)
            
            # Log matches
            for skill in matched:
                signals.append(Signal(
                    signal_type=SignalType.SKILL_MATCH,
                    severity=SignalSeverity.INFO,
                    value=skill,
                    description=f"Required skill '{skill}' found on resume"
                ))
            
            # Log missing skills
            for skill in missing:
                signals.append(Signal(
                    signal_type=SignalType.SKILL_MISSING,
                    severity=SignalSeverity.HIGH,
                    value=skill,
                    description=f"Required skill '{skill}' not found on resume"
                ))
        
        return signals
    
    def _analyze_format(self, data: Dict[str, Any]) -> List[Signal]:
        """Check for formatting issues"""
        signals = []
        
        raw_text = data.get("raw_text", "")
        
        # Check for problematic characters
        problematic = re.findall(r'[│┌─┐└┘├┤┬┴┼]', raw_text)
        if problematic:
            signals.append(Signal(
                signal_type=SignalType.FORMAT_ISSUE,
                severity=SignalSeverity.MEDIUM,
                value="table_characters",
                context={"count": len(problematic)},
                description="Table formatting characters detected - may cause ATS parsing issues"
            ))
        
        # Check for excessive special characters
        special_count = len(re.findall(r'[^\x00-\x7F]', raw_text))
        if special_count > 50:
            signals.append(Signal(
                signal_type=SignalType.SPECIAL_CHARS,
                severity=SignalSeverity.LOW,
                value=special_count,
                description=f"{special_count} non-ASCII characters detected"
            ))
        
        return signals
    
    def get_signal_summary(self, signals: List[Signal]) -> Dict[str, Any]:
        """Generate summary of all signals"""
        summary = {
            "total_signals": len(signals),
            "by_severity": {},
            "by_type": {},
            "critical_issues": [],
            "high_issues": []
        }
        
        for signal in signals:
            # Count by severity
            sev = signal.severity.value
            summary["by_severity"][sev] = summary["by_severity"].get(sev, 0) + 1
            
            # Count by type
            stype = signal.signal_type.value
            summary["by_type"][stype] = summary["by_type"].get(stype, 0) + 1
            
            # Collect critical/high issues
            if signal.severity == SignalSeverity.CRITICAL:
                summary["critical_issues"].append(signal.to_dict())
            elif signal.severity == SignalSeverity.HIGH:
                summary["high_issues"].append(signal.to_dict())
        
        return summary
