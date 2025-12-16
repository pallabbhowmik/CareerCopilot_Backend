"""
Analysis Domain Entities

Core entities for analysis results and explanations.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4


class SignalStrength(str, Enum):
    """Strength of a detected signal"""
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"


class ConfidenceLevel(str, Enum):
    """Confidence in analysis result"""
    HIGH = "high"       # >85% confident
    MEDIUM = "medium"   # 60-85% confident
    LOW = "low"         # <60% confident


class ActionPriority(str, Enum):
    """Priority for recommended action"""
    CRITICAL = "critical"   # Must address
    HIGH = "high"           # Should address
    MEDIUM = "medium"       # Consider addressing
    LOW = "low"             # Nice to have


class ExplanationType(str, Enum):
    """Type of explanation"""
    WHY_IT_MATTERS = "why_it_matters"
    WHAT_WE_FOUND = "what_we_found"
    HOW_CONFIDENT = "how_confident"
    WHAT_TO_DO = "what_to_do"
    CONTEXT = "context"


@dataclass
class Explanation:
    """
    Human-readable explanation with context.
    
    Every AI/analysis output must be accompanied by explanations.
    """
    id: UUID = field(default_factory=uuid4)
    explanation_type: ExplanationType = ExplanationType.WHAT_WE_FOUND
    
    # Content
    title: str = ""                     # Short heading
    summary: str = ""                   # 1-2 sentence summary
    detail: Optional[str] = None        # Longer explanation if needed
    
    # Source tracking
    signal_name: str = ""               # What signal triggered this
    signal_value: Any = None            # The actual value/data
    signal_strength: SignalStrength = SignalStrength.MODERATE
    
    # Confidence
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    confidence_reason: Optional[str] = None
    
    # Actionability
    is_actionable: bool = False
    action_text: Optional[str] = None
    action_priority: ActionPriority = ActionPriority.MEDIUM
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "type": self.explanation_type.value,
            "title": self.title,
            "summary": self.summary,
            "detail": self.detail,
            "signal_name": self.signal_name,
            "signal_strength": self.signal_strength.value,
            "confidence": self.confidence.value,
            "confidence_reason": self.confidence_reason,
            "is_actionable": self.is_actionable,
            "action_text": self.action_text,
            "action_priority": self.action_priority.value if self.is_actionable else None
        }


@dataclass
class CheckResult:
    """Result of a single check/evaluation"""
    id: UUID = field(default_factory=uuid4)
    check_name: str = ""
    category: str = ""  # e.g., "formatting", "content", "keywords"
    
    # Status
    passed: bool = True
    status: str = "pass"  # pass/warning/fail
    
    # Scoring (optional - not all checks have scores)
    score: Optional[int] = None  # 0-100 if applicable
    
    # Details
    explanation: Explanation = field(default_factory=Explanation)
    sub_checks: List["CheckResult"] = field(default_factory=list)
    
    # Evidence
    evidence_items: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "check_name": self.check_name,
            "category": self.category,
            "passed": self.passed,
            "status": self.status,
            "score": self.score,
            "explanation": self.explanation.to_dict(),
            "sub_checks": [c.to_dict() for c in self.sub_checks],
            "evidence_items": self.evidence_items
        }


@dataclass
class MatchResult:
    """Result of matching resume to job"""
    # Skills matching
    matched_skills: List[str] = field(default_factory=list)
    partially_matched_skills: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    
    # Experience matching
    experience_match: str = "partial"  # strong/partial/weak
    experience_explanation: str = ""
    
    # Education matching
    education_match: str = "meets"  # exceeds/meets/below/unknown
    education_explanation: str = ""
    
    # Overall
    overall_fit: str = "good"  # excellent/good/fair/poor
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    
    # Explanations
    strengths: List[Explanation] = field(default_factory=list)
    gaps: List[Explanation] = field(default_factory=list)
    recommendations: List[Explanation] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "matched_skills": self.matched_skills,
            "partially_matched_skills": self.partially_matched_skills,
            "missing_skills": self.missing_skills,
            "experience_match": self.experience_match,
            "experience_explanation": self.experience_explanation,
            "education_match": self.education_match,
            "education_explanation": self.education_explanation,
            "overall_fit": self.overall_fit,
            "confidence": self.confidence.value,
            "strengths": [s.to_dict() for s in self.strengths],
            "gaps": [g.to_dict() for g in self.gaps],
            "recommendations": [r.to_dict() for r in self.recommendations]
        }


@dataclass
class ATSEvaluation:
    """
    ATS (Applicant Tracking System) Readiness Evaluation
    
    NEVER produces a single score. Always provides category-level
    assessments with explanations.
    """
    id: UUID = field(default_factory=uuid4)
    
    # Category checks
    parsing_check: CheckResult = field(default_factory=CheckResult)
    formatting_check: CheckResult = field(default_factory=CheckResult)
    keyword_check: CheckResult = field(default_factory=CheckResult)
    section_check: CheckResult = field(default_factory=CheckResult)
    readability_check: CheckResult = field(default_factory=CheckResult)
    
    # Aggregate (for internal use, not displayed as single score)
    _internal_score: int = 0
    
    # Overall assessment
    readiness_level: str = "good"  # excellent/good/needs_work/poor
    primary_issues: List[str] = field(default_factory=list)
    
    # Explanations
    summary_explanation: Explanation = field(default_factory=Explanation)
    detailed_explanations: List[Explanation] = field(default_factory=list)
    
    # Metadata
    evaluated_at: datetime = field(default_factory=datetime.utcnow)
    job_context: Optional[str] = None  # If evaluated against specific job
    
    def get_all_checks(self) -> List[CheckResult]:
        """Get all check results"""
        return [
            self.parsing_check,
            self.formatting_check,
            self.keyword_check,
            self.section_check,
            self.readability_check
        ]
    
    def get_failing_checks(self) -> List[CheckResult]:
        """Get checks that failed or have warnings"""
        return [c for c in self.get_all_checks() if not c.passed]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "readiness_level": self.readiness_level,
            "checks": {
                "parsing": self.parsing_check.to_dict(),
                "formatting": self.formatting_check.to_dict(),
                "keywords": self.keyword_check.to_dict(),
                "sections": self.section_check.to_dict(),
                "readability": self.readability_check.to_dict()
            },
            "primary_issues": self.primary_issues,
            "summary": self.summary_explanation.to_dict(),
            "detailed_explanations": [e.to_dict() for e in self.detailed_explanations],
            "evaluated_at": self.evaluated_at.isoformat(),
            "job_context": self.job_context
        }


@dataclass
class AnalysisResult:
    """
    Complete analysis result combining multiple evaluations.
    
    This is the main output entity for resume analysis.
    """
    id: UUID = field(default_factory=uuid4)
    resume_id: Optional[UUID] = None
    job_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    
    # Component results
    ats_evaluation: Optional[ATSEvaluation] = None
    match_result: Optional[MatchResult] = None
    
    # Top-level findings
    key_strengths: List[Explanation] = field(default_factory=list)
    key_improvements: List[Explanation] = field(default_factory=list)
    
    # Next actions (prioritized)
    recommended_actions: List[Explanation] = field(default_factory=list)
    
    # Confidence
    overall_confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    confidence_explanation: str = ""
    
    # Metadata
    analysis_type: str = "full"  # full/quick/ats_only/match_only
    created_at: datetime = field(default_factory=datetime.utcnow)
    processing_time_ms: Optional[int] = None
    
    def get_top_action(self) -> Optional[Explanation]:
        """Get the highest priority recommended action"""
        if not self.recommended_actions:
            return None
        return self.recommended_actions[0]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "resume_id": str(self.resume_id) if self.resume_id else None,
            "job_id": str(self.job_id) if self.job_id else None,
            "ats_evaluation": self.ats_evaluation.to_dict() if self.ats_evaluation else None,
            "match_result": self.match_result.to_dict() if self.match_result else None,
            "key_strengths": [s.to_dict() for s in self.key_strengths],
            "key_improvements": [i.to_dict() for i in self.key_improvements],
            "recommended_actions": [a.to_dict() for a in self.recommended_actions],
            "overall_confidence": self.overall_confidence.value,
            "confidence_explanation": self.confidence_explanation,
            "analysis_type": self.analysis_type,
            "created_at": self.created_at.isoformat(),
            "processing_time_ms": self.processing_time_ms
        }
