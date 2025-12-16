"""
Database Models - SQLAlchemy ORM Models

Production-grade database schema with:
- UUIDs for all primary keys
- Soft deletes
- Audit timestamps
- Proper relationships
- JSON schema validation ready
"""
from sqlalchemy import (
    Column, String, Integer, Float, Text, JSON, DateTime, Boolean,
    ForeignKey, Index, Enum as SQLEnum, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from app.db.session import Base


# =============================================================================
# MIXINS
# =============================================================================

class TimestampMixin:
    """Adds created_at and updated_at timestamps"""
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SoftDeleteMixin:
    """Adds soft delete capability"""
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)


# =============================================================================
# USER & AUTH MODELS
# =============================================================================

class User(Base, TimestampMixin, SoftDeleteMixin):
    """User account model"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    
    # Auth
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Profile
    full_name = Column(String(255))
    avatar_url = Column(String(500), nullable=True)
    
    # Onboarding & Career Context
    target_role = Column(String(255), nullable=True)
    experience_level = Column(String(50), nullable=True)  # entry/mid/senior/lead
    experience_years = Column(Integer, nullable=True)
    country = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    career_goal = Column(Text, nullable=True)
    onboarding_completed = Column(Boolean, default=False)
    onboarding_step = Column(Integer, default=0)
    
    # Subscription & Limits
    subscription_tier = Column(String(50), default="free")  # free/pro/enterprise
    subscription_expires_at = Column(DateTime(timezone=True), nullable=True)
    monthly_ai_credits = Column(Integer, default=50)
    ai_credits_used = Column(Integer, default=0)
    
    # Preferences
    preferences = Column(JSON, default=dict)
    
    # Relationships
    resumes = relationship("Resume", back_populates="owner", cascade="all, delete-orphan")
    analyses = relationship("Analysis", back_populates="owner")
    applications = relationship("Application", back_populates="owner")
    ai_requests = relationship("AIRequest", back_populates="user")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_email_active', 'email', 'is_active'),
        Index('idx_user_subscription', 'subscription_tier', 'subscription_expires_at'),
    )


class UserProfile(Base, TimestampMixin):
    """Extended user profile for career intelligence"""
    __tablename__ = "user_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    
    # Career history summary
    total_experience_years = Column(Float, nullable=True)
    industries_worked = Column(JSON, default=list)  # List of industries
    roles_held = Column(JSON, default=list)  # List of past roles
    
    # Skills profile
    skill_profile = Column(JSON, default=dict)  # Structured skill data
    top_skills = Column(JSON, default=list)  # Top 10 skills
    skill_gaps = Column(JSON, default=list)  # Identified gaps for target role
    
    # Career intelligence
    recommended_roles = Column(JSON, default=list)
    career_trajectory = Column(JSON, default=dict)
    
    # Privacy
    data_retention_preference = Column(String(50), default="standard")  # standard/minimal/extended


# =============================================================================
# RESUME MODELS
# =============================================================================

class Resume(Base, TimestampMixin, SoftDeleteMixin):
    """Resume model with versioning support"""
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=True)
    
    # Content
    title = Column(String(255), nullable=False)
    content_raw = Column(Text, nullable=True)  # Original text
    content_structured = Column(JSON, nullable=True)  # Parsed structure
    style_config = Column(JSON, default=dict)  # User style overrides
    
    # File storage
    file_path = Column(String(500), nullable=True)
    file_type = Column(String(20), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    
    # Parsing metadata
    parsing_confidence = Column(Float, default=0.8)
    parsing_issues = Column(JSON, default=list)
    sections_detected = Column(JSON, default=list)
    
    # Quality scores (cached for performance)
    completeness_score = Column(Integer, default=0)
    bullet_strength_score = Column(Integer, default=0)
    
    # Heatmap & Feedback
    heatmap_data = Column(JSON, nullable=True)
    bullet_feedback = Column(JSON, nullable=True)
    
    # Versioning for A/B testing
    version = Column(Integer, default=1)
    variant_group_id = Column(String(100), index=True, nullable=True)
    parent_resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=True)
    is_primary = Column(Boolean, default=True)  # Main version vs variant
    
    # Status
    status = Column(String(50), default="draft")  # draft/active/archived
    last_analyzed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    owner = relationship("User", back_populates="resumes")
    template = relationship("Template", back_populates="resumes")
    sections = relationship("ResumeSection", back_populates="resume", cascade="all, delete-orphan")
    analyses = relationship("Analysis", back_populates="resume")
    applications = relationship("Application", back_populates="resume")
    parent = relationship("Resume", remote_side=[id])
    
    __table_args__ = (
        Index('idx_resume_user_status', 'user_id', 'status'),
        Index('idx_resume_variant', 'variant_group_id', 'version'),
    )


class ResumeSection(Base, TimestampMixin):
    """Individual resume section for granular editing"""
    __tablename__ = "resume_sections"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()))
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"))
    
    section_type = Column(String(50), nullable=False)  # experience/education/skills/etc
    title = Column(String(255), nullable=True)
    content = Column(JSON, nullable=True)
    order = Column(Integer, default=0)
    
    # Parsing
    confidence = Column(Float, default=0.8)
    is_detected = Column(Boolean, default=True)
    is_ambiguous = Column(Boolean, default=False)
    
    # Quality
    quality_score = Column(Integer, default=0)
    issues = Column(JSON, default=list)
    suggestions = Column(JSON, default=list)
    
    resume = relationship("Resume", back_populates="sections")


class ResumeBullet(Base, TimestampMixin):
    """Individual bullet point with analysis"""
    __tablename__ = "resume_bullets"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()))
    section_id = Column(Integer, ForeignKey("resume_sections.id", ondelete="CASCADE"))
    
    text = Column(Text, nullable=False)
    order = Column(Integer, default=0)
    
    # Analysis
    strength = Column(String(20), default="moderate")  # strong/moderate/weak
    has_action_verb = Column(Boolean, default=False)
    has_metrics = Column(Boolean, default=False)
    has_impact = Column(Boolean, default=False)
    detected_skills = Column(JSON, default=list)
    
    # AI suggestions
    improved_version = Column(Text, nullable=True)
    improvement_explanation = Column(Text, nullable=True)


# =============================================================================
# JOB DESCRIPTION MODELS
# =============================================================================

class JobDescription(Base, TimestampMixin, SoftDeleteMixin):
    """Job description with extracted requirements"""
    __tablename__ = "job_descriptions"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Basic info
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    is_remote = Column(Boolean, default=False)
    job_type = Column(String(50), default="full-time")
    
    # Content
    content_raw = Column(Text, nullable=False)
    content_summary = Column(Text, nullable=True)
    
    # Extracted data
    requirements_structured = Column(JSON, default=dict)
    required_skills = Column(JSON, default=list)
    preferred_skills = Column(JSON, default=list)
    
    # Experience requirements
    experience_level = Column(String(50), nullable=True)
    years_experience_min = Column(Integer, nullable=True)
    years_experience_max = Column(Integer, nullable=True)
    
    # Education
    education_required = Column(String(100), nullable=True)
    
    # Source
    source_url = Column(String(500), nullable=True)
    posted_date = Column(DateTime(timezone=True), nullable=True)
    
    # Analysis metadata
    parsing_confidence = Column(Float, default=0.8)
    
    # Relationships
    analyses = relationship("Analysis", back_populates="job_description")
    skill_requirements = relationship("JobSkillRequirement", back_populates="job")


class JobSkillRequirement(Base, TimestampMixin):
    """Individual skill requirement from job description"""
    __tablename__ = "job_skill_requirements"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("job_descriptions.id", ondelete="CASCADE"))
    
    skill_name = Column(String(100), nullable=False)
    normalized_name = Column(String(100), nullable=True)
    importance = Column(String(20), default="medium")  # critical/high/medium/low
    category = Column(String(50), nullable=True)
    
    # Context
    mentioned_count = Column(Integer, default=1)
    context_snippets = Column(JSON, default=list)
    
    job = relationship("JobDescription", back_populates="skill_requirements")


# =============================================================================
# ANALYSIS MODELS
# =============================================================================

class Analysis(Base, TimestampMixin):
    """Analysis result linking resume and job"""
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"))
    resume_id = Column(Integer, ForeignKey("resumes.id"))
    job_description_id = Column(Integer, ForeignKey("job_descriptions.id"), nullable=True)
    
    # Analysis type
    analysis_type = Column(String(50), default="full")  # full/quick/ats_only/match_only
    
    # Results
    ats_evaluation = Column(JSON, nullable=True)
    match_result = Column(JSON, nullable=True)
    skill_analysis = Column(JSON, nullable=True)
    
    # Scores (for quick access, not displayed as single score to user)
    _internal_ats_score = Column(Integer, nullable=True)
    _internal_match_score = Column(Integer, nullable=True)
    
    # Explanations
    key_strengths = Column(JSON, default=list)
    key_improvements = Column(JSON, default=list)
    recommended_actions = Column(JSON, default=list)
    
    # Metadata
    confidence_level = Column(String(20), default="medium")
    processing_time_ms = Column(Integer, nullable=True)
    
    # Relationships
    owner = relationship("User", back_populates="analyses")
    resume = relationship("Resume", back_populates="analyses")
    job_description = relationship("JobDescription", back_populates="analyses")
    explanations = relationship("AnalysisExplanation", back_populates="analysis")


class AnalysisExplanation(Base, TimestampMixin):
    """Detailed explanation for an analysis finding"""
    __tablename__ = "analysis_explanations"
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id", ondelete="CASCADE"))
    
    explanation_type = Column(String(50), nullable=False)  # why/what/how/action
    category = Column(String(50), nullable=True)  # formatting/skills/experience/etc
    
    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False)
    detail = Column(Text, nullable=True)
    
    # Signal info
    signal_name = Column(String(100), nullable=True)
    signal_strength = Column(String(20), default="moderate")
    
    # Action
    is_actionable = Column(Boolean, default=False)
    action_text = Column(Text, nullable=True)
    action_priority = Column(String(20), default="medium")
    
    analysis = relationship("Analysis", back_populates="explanations")


class ATSEvaluation(Base, TimestampMixin):
    """Cached ATS evaluation results"""
    __tablename__ = "ats_evaluations"
    
    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"))
    job_id = Column(Integer, ForeignKey("job_descriptions.id"), nullable=True)
    
    # Check results
    parsing_check = Column(JSON, default=dict)
    formatting_check = Column(JSON, default=dict)
    keyword_check = Column(JSON, default=dict)
    section_check = Column(JSON, default=dict)
    readability_check = Column(JSON, default=dict)
    
    # Summary
    readiness_level = Column(String(20), default="good")
    primary_issues = Column(JSON, default=list)
    
    # Internal only (never shown as single score)
    _internal_score = Column(Integer, nullable=True)


# =============================================================================
# SKILL MODELS
# =============================================================================

class SkillTaxonomy(Base, TimestampMixin):
    """Master skill taxonomy for normalization"""
    __tablename__ = "skill_taxonomy"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Skill info
    canonical_name = Column(String(100), unique=True, nullable=False)
    aliases = Column(JSON, default=list)  # Alternative names
    category = Column(String(50), nullable=False)
    
    # Relationships
    parent_skill_id = Column(Integer, ForeignKey("skill_taxonomy.id"), nullable=True)
    related_skills = Column(JSON, default=list)
    
    # Market data
    is_trending = Column(Boolean, default=False)
    demand_level = Column(String(20), default="medium")
    
    # Learning
    typical_learning_time = Column(String(50), nullable=True)
    difficulty = Column(String(20), default="medium")


class ExtractedSkill(Base, TimestampMixin):
    """Skill extracted from a resume"""
    __tablename__ = "extracted_skills"
    
    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"))
    taxonomy_id = Column(Integer, ForeignKey("skill_taxonomy.id"), nullable=True)
    
    # Skill info
    original_text = Column(String(200), nullable=False)
    normalized_name = Column(String(100), nullable=True)
    category = Column(String(50), nullable=True)
    
    # Evidence
    evidence_type = Column(String(50), default="listed")
    evidence_source = Column(String(100), nullable=True)
    evidence_text = Column(Text, nullable=True)
    confidence = Column(Float, default=0.8)
    
    # Assessment
    level = Column(String(20), default="intermediate")
    evidence_strength = Column(Float, default=0.5)


# =============================================================================
# TEMPLATE MODELS
# =============================================================================

class Template(Base, TimestampMixin, SoftDeleteMixin):
    """Resume template configuration"""
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()))
    
    # Basic info
    name = Column(String(100), unique=True, nullable=False)
    slug = Column(String(100), unique=True, nullable=True)
    category = Column(String(50), nullable=False)  # ATS-Safe/Creative/Executive/etc
    description = Column(Text, nullable=True)
    
    # Configuration
    config_json = Column(JSON, nullable=False)  # Template structure
    default_styles = Column(JSON, default=dict)  # Default font, spacing, etc
    safe_style_ranges = Column(JSON, default=dict)  # Min/max for safe values
    
    # Preview
    preview_url = Column(String(500), nullable=True)
    preview_image_url = Column(String(500), nullable=True)
    
    # Targeting
    recommended_for = Column(JSON, default=list)  # Roles this is good for
    experience_levels = Column(JSON, default=list)  # entry/mid/senior
    industries = Column(JSON, default=list)
    
    # Flags
    is_premium = Column(Boolean, default=False)
    is_ats_safe = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    
    # Popularity
    popularity_score = Column(Integer, default=0)
    use_count = Column(Integer, default=0)
    
    resumes = relationship("Resume", back_populates="template")


# =============================================================================
# APPLICATION TRACKING MODELS
# =============================================================================

class Application(Base, TimestampMixin, SoftDeleteMixin):
    """Job application tracking"""
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=True)
    job_id = Column(Integer, ForeignKey("job_descriptions.id"), nullable=True)
    
    # Job info (can be manual entry)
    company_name = Column(String(255), nullable=False)
    job_title = Column(String(255), nullable=False)
    job_url = Column(String(500), nullable=True)
    location = Column(String(255), nullable=True)
    
    # Status tracking
    status = Column(String(50), default="applied")
    status_history = Column(JSON, default=list)  # [{status, date, notes}]
    applied_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Outcome tracking
    response_received = Column(Boolean, default=False)
    response_date = Column(DateTime(timezone=True), nullable=True)
    interview_scheduled = Column(Boolean, default=False)
    interview_dates = Column(JSON, default=list)
    
    # Notes
    notes = Column(Text, nullable=True)
    contact_name = Column(String(255), nullable=True)
    contact_email = Column(String(255), nullable=True)
    
    # Resume version used
    resume_version_tag = Column(String(50), nullable=True)
    
    # Salary
    salary_expected = Column(Integer, nullable=True)
    salary_offered = Column(Integer, nullable=True)
    
    # Final outcome
    outcome = Column(String(50), nullable=True)  # hired/rejected/withdrawn
    outcome_date = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(String(255), nullable=True)
    
    # Relationships
    owner = relationship("User", back_populates="applications")
    resume = relationship("Resume", back_populates="applications")
    job = relationship("JobDescription")
    
    __table_args__ = (
        Index('idx_application_user_status', 'user_id', 'status'),
        Index('idx_application_dates', 'user_id', 'applied_at'),
    )


class ApplicationOutcome(Base, TimestampMixin):
    """Detailed outcome tracking for analytics"""
    __tablename__ = "application_outcomes"
    
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"))
    
    # Outcome details
    stage_reached = Column(String(50), nullable=False)  # applied/screening/interview/offer
    days_to_response = Column(Integer, nullable=True)
    interview_rounds = Column(Integer, default=0)
    
    # What worked/didn't
    resume_feedback = Column(Text, nullable=True)
    interview_feedback = Column(Text, nullable=True)
    
    # Learning
    lessons_learned = Column(Text, nullable=True)


# =============================================================================
# AI & OBSERVABILITY MODELS
# =============================================================================

class AIRequest(Base, TimestampMixin):
    """Log of all AI API calls for observability and cost tracking"""
    __tablename__ = "ai_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Request info
    request_type = Column(String(50), nullable=False)  # parse_resume/improve_bullet/etc
    model = Column(String(50), nullable=False)  # gpt-4o-mini, claude-3, etc
    provider = Column(String(20), nullable=False)  # openai/anthropic
    
    # Prompt
    prompt_template = Column(String(100), nullable=True)
    prompt_version = Column(String(20), default="1.0")
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    
    # Response
    response_status = Column(String(20), nullable=False)  # success/error/timeout
    response_time_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Cost tracking
    estimated_cost_usd = Column(Float, nullable=True)
    
    # Metadata
    correlation_id = Column(String(100), nullable=True)  # For request tracing
    metadata = Column(JSON, default=dict)
    
    user = relationship("User", back_populates="ai_requests")
    
    __table_args__ = (
        Index('idx_ai_request_user', 'user_id', 'created_at'),
        Index('idx_ai_request_type', 'request_type', 'created_at'),
    )


class FeatureFlag(Base, TimestampMixin):
    """Feature flags for gradual rollout"""
    __tablename__ = "feature_flags"
    
    id = Column(Integer, primary_key=True, index=True)
    
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    
    # Targeting
    is_enabled = Column(Boolean, default=False)
    enabled_for_tiers = Column(JSON, default=list)  # ["pro", "enterprise"]
    enabled_for_users = Column(JSON, default=list)  # Specific user IDs
    rollout_percentage = Column(Integer, default=0)  # 0-100
    
    # Metadata
    category = Column(String(50), nullable=True)
