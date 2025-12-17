from sqlalchemy import Column, String, ForeignKey, Text, JSON, DateTime, Boolean, Integer, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base
import uuid

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), unique=True, nullable=False) # References auth.users
    email = Column(String, unique=True, nullable=False)
    full_name = Column(String)
    target_role = Column(String)
    experience_level = Column(String)
    country = Column(String)
    career_goal = Column(Text)
    onboarding_completed = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))

    resumes = relationship("Resume", back_populates="owner")
    applications = relationship("Application", back_populates="owner")
    analyses = relationship("Analysis", back_populates="owner")

class Resume(Base):
    __tablename__ = "resumes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.user_id"), nullable=False)
    title = Column(String, nullable=False)
    template_id = Column(UUID(as_uuid=True), ForeignKey("templates.id"), nullable=True)
    
    current_version_id = Column(UUID(as_uuid=True), nullable=True)
    variant_group_id = Column(UUID(as_uuid=True), nullable=True)
    is_control = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))

    owner = relationship("UserProfile", back_populates="resumes")
    template = relationship("Template", back_populates="resumes")
    applications = relationship("Application", back_populates="resume")
    analyses = relationship("Analysis", back_populates="resume")

class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.user_id"), nullable=False)
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    location = Column(String)
    job_url = Column(String)
    
    raw_text = Column(Text, nullable=False)
    parsed_data = Column(JSON)
    
    experience_required = Column(Text)
    education_required = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))

    analyses = relationship("Analysis", back_populates="job_description")

class Template(Base):
    __tablename__ = "templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, index=True)
    slug = Column(String, nullable=True)
    category = Column(String) # e.g., "ATS-Safe", "Creative", "Developer"
    description = Column(Text, nullable=True)
    config_json = Column(JSON) # Template configuration
    preview_url = Column(String, nullable=True)
    preview_image_url = Column(String, nullable=True)
    is_premium = Column(Boolean, default=False)
    is_ats_safe = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    recommended_for = Column(JSON, default=list)  # List of role types
    popularity_score = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    resumes = relationship("Resume", back_populates="template")

class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.user_id"), nullable=False)
    resume_id = Column(UUID(as_uuid=True), ForeignKey("resumes.id"), nullable=True)
    job_description_id = Column(UUID(as_uuid=True), ForeignKey("job_descriptions.id"), nullable=True)
    
    score_data = Column(JSON) # Detailed scoring breakdown
    gap_analysis = Column(JSON) # Missing skills, etc.
    recommendations = Column(JSON) # Actionable advice
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("UserProfile", back_populates="analyses")
    resume = relationship("Resume", back_populates="analyses")
    job_description = relationship("JobDescription", back_populates="analyses")

class Application(Base):
    __tablename__ = "applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.user_id"), nullable=False)
    resume_id = Column(UUID(as_uuid=True), ForeignKey("resumes.id"), nullable=True)
    
    company = Column(String)
    job_title = Column(String)
    job_url = Column(String, nullable=True)
    status = Column(String, default="applied") # applied, interview, rejected, offer
    applied_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Outcome tracking
    response_received = Column(Boolean, default=False)
    interview_scheduled = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    owner = relationship("UserProfile", back_populates="applications")
    resume = relationship("Resume", back_populates="applications")
