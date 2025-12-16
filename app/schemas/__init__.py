"""
Schemas Package

Centralized Pydantic schemas for API validation.
"""
from .api import (
    # Base responses
    APIResponse,
    PaginatedResponse,
    ErrorResponse,
    
    # Enums
    ReadinessLevel,
    SignalStrength,
    ConfidenceLevel,
    ActionPriority,
    
    # Explanation
    ExplanationSchema,
    CheckResultSchema,
    
    # Resume
    PersonalInfoSchema,
    BulletSchema,
    ExperienceSchema,
    EducationSchema,
    ProjectSchema,
    ResumeStructuredSchema,
    ResumeCreateRequest,
    ResumeUpdateRequest,
    ResumeResponse,
    ResumeUploadResponse,
    
    # Job
    JobRequirementSchema,
    JobCreateRequest,
    JobResponse,
    
    # ATS Analysis
    ATSCheckResult,
    ATSEvaluationResponse,
    
    # Skills
    SkillMatchSchema,
    SkillGapSchema,
    SkillAnalysisResponse,
    
    # Match
    MatchCategorySchema,
    MatchAnalysisResponse,
    
    # Bullet
    BulletImprovementRequest,
    BulletSuggestionSchema,
    BulletImprovementResponse,
    
    # Chat
    ChatMessageRequest,
    ChatMessageResponse,
    
    # User
    UserBase,
    UserCreate,
    UserResponse,
    UserStatsResponse,
    
    # Health
    HealthResponse
)

# Keep backward compatibility with existing schemas
from .resume import (
    ResumeBase,
    ResumeCreate,
    ResumeUpdate,
    ResumeInDB,
    PersonalInfo,
    ExperienceItem,
    EducationItem,
    ProjectItem,
    ResumeStructured
)

from .user import (
    UserBase as UserBaseOld,
    UserCreate as UserCreateOld,
    UserInDB,
    Token,
    TokenPayload
)

__all__ = [
    # New API schemas
    "APIResponse",
    "PaginatedResponse", 
    "ErrorResponse",
    "ReadinessLevel",
    "SignalStrength",
    "ConfidenceLevel",
    "ActionPriority",
    "ExplanationSchema",
    "CheckResultSchema",
    "PersonalInfoSchema",
    "BulletSchema",
    "ExperienceSchema",
    "EducationSchema",
    "ProjectSchema",
    "ResumeStructuredSchema",
    "ResumeCreateRequest",
    "ResumeUpdateRequest",
    "ResumeResponse",
    "ResumeUploadResponse",
    "JobRequirementSchema",
    "JobCreateRequest",
    "JobResponse",
    "ATSCheckResult",
    "ATSEvaluationResponse",
    "SkillMatchSchema",
    "SkillGapSchema",
    "SkillAnalysisResponse",
    "MatchCategorySchema",
    "MatchAnalysisResponse",
    "BulletImprovementRequest",
    "BulletSuggestionSchema",
    "BulletImprovementResponse",
    "ChatMessageRequest",
    "ChatMessageResponse",
    "UserBase",
    "UserCreate",
    "UserResponse",
    "UserStatsResponse",
    "HealthResponse",
    
    # Legacy schemas (backward compatibility)
    "ResumeBase",
    "ResumeCreate",
    "ResumeUpdate",
    "ResumeInDB",
    "PersonalInfo",
    "ExperienceItem",
    "EducationItem",
    "ProjectItem",
    "ResumeStructured",
    "UserInDB",
    "Token",
    "TokenPayload"
]
