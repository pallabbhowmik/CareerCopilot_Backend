"""
API Schemas

Enhanced Pydantic schemas for request/response validation.
All responses include explanations - never just scores.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from enum import Enum


# =============================================================================
# ENUMS
# =============================================================================

class ReadinessLevel(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    NEEDS_WORK = "needs_work"


class SignalStrength(str, Enum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ActionPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# =============================================================================
# BASE SCHEMAS
# =============================================================================

class APIResponse(BaseModel):
    """Standard API response wrapper"""
    success: bool = True
    data: Optional[Any] = None
    error: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginatedResponse(APIResponse):
    """Paginated response"""
    total: int = 0
    page: int = 1
    page_size: int = 20
    has_next: bool = False
    has_prev: bool = False


class ErrorResponse(BaseModel):
    """Error response"""
    success: bool = False
    error: str
    error_code: Optional[str] = None
    detail: Optional[str] = None
    request_id: Optional[str] = None


# =============================================================================
# EXPLANATION SCHEMAS
# =============================================================================

class ExplanationSchema(BaseModel):
    """Explanation for any analysis output"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Strong Skill Match",
                "summary": "85% of required skills found on your resume.",
                "detail": "Your skills closely align with the job requirements.",
                "signal": {
                    "name": "skill_match",
                    "value": 85,
                    "strength": "strong"
                },
                "confidence": {
                    "level": "high",
                    "reason": "Direct skill name matching"
                },
                "action": {
                    "needed": False
                }
            }
        }
    )
    
    title: str
    summary: str
    detail: Optional[str] = None
    signal: Optional[Dict[str, Any]] = None
    confidence: Optional[Dict[str, Any]] = None
    action: Optional[Dict[str, Any]] = None


class CheckResultSchema(BaseModel):
    """Result of a single check (ATS, formatting, etc.)"""
    check_name: str
    category: str
    status: str  # pass, warning, fail
    passed: bool
    evidence_items: List[str] = []
    explanation: ExplanationSchema


# =============================================================================
# RESUME SCHEMAS
# =============================================================================

class PersonalInfoSchema(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None


class BulletSchema(BaseModel):
    text: str
    order: int = 0
    strength_score: Optional[int] = Field(None, ge=0, le=100)
    has_action_verb: bool = False
    has_metrics: bool = False
    suggestions: List[str] = []


class ExperienceSchema(BaseModel):
    company: str
    role: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    location: Optional[str] = None
    bullets: List[BulletSchema] = []
    is_current: bool = False


class EducationSchema(BaseModel):
    institution: str
    degree: str
    field: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    gpa: Optional[str] = None


class ProjectSchema(BaseModel):
    name: str
    description: Optional[str] = None
    tech_stack: List[str] = []
    bullets: List[str] = []
    url: Optional[str] = None


class ResumeStructuredSchema(BaseModel):
    """Full structured resume data"""
    personal_info: PersonalInfoSchema
    summary: Optional[str] = None
    skills: List[str] = []
    experience: List[ExperienceSchema] = []
    education: List[EducationSchema] = []
    projects: List[ProjectSchema] = []
    certifications: List[str] = []


class ResumeCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    raw_text: Optional[str] = None


class ResumeUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    structured_data: Optional[ResumeStructuredSchema] = None


class ResumeResponse(BaseModel):
    """Resume response with metadata"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    uuid: str
    title: str
    version: int
    structured_data: Optional[ResumeStructuredSchema] = None
    parsing_confidence: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class ResumeUploadResponse(BaseModel):
    """Response after resume upload and parsing"""
    id: int
    uuid: str
    title: str
    parsed_sections: ResumeStructuredSchema
    parsing_quality: Dict[str, Any]
    next_steps: List[str]


# =============================================================================
# JOB DESCRIPTION SCHEMAS
# =============================================================================

class JobRequirementSchema(BaseModel):
    text: str
    is_required: bool = True
    category: str = "general"


class JobCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    company: str = Field(..., min_length=1, max_length=200)
    raw_text: str = Field(..., min_length=50)
    url: Optional[str] = None
    location: Optional[str] = None


class JobResponse(BaseModel):
    """Job description response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    uuid: str
    title: str
    company: str
    location: Optional[str] = None
    required_skills: List[str] = []
    preferred_skills: List[str] = []
    requirements: List[JobRequirementSchema] = []
    created_at: datetime


# =============================================================================
# ATS ANALYSIS SCHEMAS (NO SINGLE SCORES!)
# =============================================================================

class ATSCheckResult(BaseModel):
    """Individual ATS check result"""
    check_name: str
    status: str  # "pass", "warning", "fail"
    explanation: ExplanationSchema
    evidence: List[str] = []


class ATSEvaluationResponse(BaseModel):
    """
    ATS evaluation response.
    
    IMPORTANT: Never includes a single ATS score.
    Only category-level assessments with explanations.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "readiness_level": "good",
                "summary": {
                    "title": "ATS Readiness Summary",
                    "summary": "Your resume should pass most ATS filters with minor improvements.",
                    "detail": "Most checks passed with some areas for improvement."
                },
                "checks": [
                    {
                        "check_name": "Section Detection",
                        "status": "pass",
                        "explanation": {
                            "title": "Section Detection",
                            "summary": "ATS detected 5 out of 6 standard sections."
                        },
                        "evidence": ["Contact Info", "Experience", "Education", "Skills"]
                    }
                ],
                "primary_issues": [],
                "recommendations": ["Consider adding a summary section"]
            }
        }
    )
    
    readiness_level: ReadinessLevel
    summary: ExplanationSchema
    checks: List[ATSCheckResult]
    primary_issues: List[str] = []
    recommendations: List[str] = []


# =============================================================================
# SKILL ANALYSIS SCHEMAS
# =============================================================================

class SkillMatchSchema(BaseModel):
    """Skill match result"""
    skill: str
    match_type: str  # "exact", "partial", "missing"
    confidence: ConfidenceLevel
    evidence: Optional[str] = None


class SkillGapSchema(BaseModel):
    """Identified skill gap"""
    skill: str
    importance: str  # "required", "preferred", "nice_to_have"
    explanation: ExplanationSchema
    learning_resources: List[str] = []
    related_skills_you_have: List[str] = []


class SkillAnalysisResponse(BaseModel):
    """Skill analysis response"""
    matched_skills: List[SkillMatchSchema]
    partial_matches: List[SkillMatchSchema]
    missing_skills: List[SkillGapSchema]
    skill_coverage: Dict[str, Any]  # Category-level coverage, not single score
    high_roi_recommendations: List[Dict[str, Any]]
    explanations: List[ExplanationSchema]


# =============================================================================
# MATCH ANALYSIS SCHEMAS
# =============================================================================

class MatchCategorySchema(BaseModel):
    """Match assessment for a specific category"""
    category: str
    level: str  # "strong", "moderate", "developing"
    explanation: ExplanationSchema
    highlights: List[str] = []
    gaps: List[str] = []


class MatchAnalysisResponse(BaseModel):
    """
    Resume-to-job match analysis.
    
    NO single match percentage. Only category-level assessments.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "overall_assessment": {
                    "title": "Good Match with Opportunities",
                    "summary": "Your profile aligns well with this role's requirements.",
                    "detail": "Strong skill alignment with room for improvement in experience demonstration."
                },
                "categories": [
                    {
                        "category": "Technical Skills",
                        "level": "strong",
                        "explanation": {
                            "title": "Technical Skills Assessment",
                            "summary": "Strong alignment with required technical skills."
                        },
                        "highlights": ["Python", "AWS", "SQL"],
                        "gaps": ["Kubernetes"]
                    }
                ],
                "strengths": [],
                "improvement_areas": [],
                "action_items": []
            }
        }
    )
    
    overall_assessment: ExplanationSchema
    categories: List[MatchCategorySchema]
    strengths: List[ExplanationSchema]
    improvement_areas: List[ExplanationSchema]
    action_items: List[Dict[str, Any]]


# =============================================================================
# BULLET IMPROVEMENT SCHEMAS
# =============================================================================

class BulletImprovementRequest(BaseModel):
    original_text: str = Field(..., min_length=10)
    context: Optional[str] = None  # Job context if available
    focus: Optional[str] = None  # "metrics", "impact", "action_verbs"


class BulletSuggestionSchema(BaseModel):
    suggested_text: str
    improvement_type: str
    explanation: ExplanationSchema
    confidence: ConfidenceLevel


class BulletImprovementResponse(BaseModel):
    original: str
    analysis: ExplanationSchema
    suggestions: List[BulletSuggestionSchema]
    quick_tips: List[str]


# =============================================================================
# CHAT/CAREER ADVISOR SCHEMAS
# =============================================================================

class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    conversation_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None  # Resume/job context


class ChatMessageResponse(BaseModel):
    message: str
    conversation_id: str
    suggestions: List[str] = []
    related_actions: List[Dict[str, Any]] = []


# =============================================================================
# USER & AUTH SCHEMAS
# =============================================================================

class UserBase(BaseModel):
    email: str
    name: Optional[str] = None


class UserCreate(UserBase):
    firebase_uid: str


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    uuid: str
    created_at: datetime


class UserStatsResponse(BaseModel):
    resumes_created: int
    analyses_run: int
    member_since: Optional[str] = None
    last_active: Optional[str] = None


# =============================================================================
# HEALTH & STATUS SCHEMAS
# =============================================================================

class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    services: Dict[str, str] = {}
