from sqlalchemy import Column, Integer, String, ForeignKey, Text, JSON, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Onboarding & Goals
    target_role = Column(String)
    experience_level = Column(String) # Fresher, Mid, Senior
    country = Column(String)
    career_goal = Column(Text)
    onboarding_completed = Column(Boolean, default=False)
    
    resumes = relationship("Resume", back_populates="owner")
    analyses = relationship("Analysis", back_populates="owner")
    applications = relationship("Application", back_populates="owner")

class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=True)
    
    title = Column(String)
    content_raw = Column(Text) # Original text content
    content_structured = Column(JSON) # Parsed JSON structure
    style_config = Column(JSON) # User overrides for the template
    
    # Heatmap & Quality Scores
    heatmap_data = Column(JSON) # Section-level quality scores
    bullet_feedback = Column(JSON) # Bullet-level AI feedback
    strength_score = Column(Integer, default=0) # 0-100 overall resume strength
    
    # A/B Testing
    variant_group_id = Column(String, index=True, nullable=True) # ID to group variants
    version = Column(Integer, default=1)
    parent_resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=True)
    
    file_path = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    owner = relationship("User", back_populates="resumes")
    template = relationship("Template", back_populates="resumes")
    analyses = relationship("Analysis", back_populates="resume")
    applications = relationship("Application", back_populates="resume")

class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    company = Column(String)
    content_raw = Column(Text)
    requirements_structured = Column(JSON) # Extracted skills/reqs
    url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    analyses = relationship("Analysis", back_populates="job_description")

class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    resume_id = Column(Integer, ForeignKey("resumes.id"))
    job_description_id = Column(Integer, ForeignKey("job_descriptions.id"))
    
    score_data = Column(JSON) # Detailed scoring breakdown
    gap_analysis = Column(JSON) # Missing skills, etc.
    recommendations = Column(JSON) # Actionable advice
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="analyses")
    resume = relationship("Resume", back_populates="analyses")
    job_description = relationship("JobDescription", back_populates="analyses")

class Template(Base):
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    category = Column(String) # e.g., "ATS-Safe", "Creative", "Developer"
    description = Column(Text)
    config_json = Column(JSON) # Template configuration
    preview_url = Column(String, nullable=True)
    is_premium = Column(Boolean, default=False)
    popularity_score = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    resumes = relationship("Resume", back_populates="template")

class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    resume_id = Column(Integer, ForeignKey("resumes.id"))
    
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
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    owner = relationship("User", back_populates="applications")
    resume = relationship("Resume", back_populates="applications")
