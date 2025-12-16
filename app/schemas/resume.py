from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

class ResumeBase(BaseModel):
    title: Optional[str] = None

class ResumeCreate(BaseModel):
    title: str
    template_id: Optional[int] = None

class ResumeUpdate(BaseModel):
    title: Optional[str] = None
    content_structured: Optional[Dict[str, Any]] = None
    style_config: Optional[Dict[str, Any]] = None
    template_id: Optional[int] = None

class ResumeInDB(ResumeBase):
    id: int
    user_id: int
    template_id: Optional[int] = None
    content_raw: Optional[str] = None
    content_structured: Optional[Dict[str, Any]] = None
    style_config: Optional[Dict[str, Any]] = None
    heatmap_data: Optional[Dict[str, Any]] = None
    bullet_feedback: Optional[Dict[str, Any]] = None
    strength_score: int
    variant_group_id: Optional[str] = None
    version: int
    parent_resume_id: Optional[int] = None
    file_path: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ResumeUploadResponse(BaseModel):
    id: int
    title: str
    parsed_sections: Dict[str, Any]
    ats_readiness: Dict[str, Any]
    next_steps: List[str]

class PersonalInfo(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None

class ExperienceItem(BaseModel):
    company: str
    role: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    location: Optional[str] = None
    bullets: List[str]
    is_current: bool = False

class EducationItem(BaseModel):
    institution: str
    degree: str
    field: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    gpa: Optional[str] = None
    location: Optional[str] = None

class ProjectItem(BaseModel):
    name: str
    description: Optional[str] = None
    tech_stack: Optional[List[str]] = None
    bullets: Optional[List[str]] = None
    url: Optional[str] = None

class ResumeStructured(BaseModel):
    personal_info: PersonalInfo
    summary: Optional[str] = None
    skills: List[str] = []
    experience: List[ExperienceItem] = []
    education: List[EducationItem] = []
    projects: Optional[List[ProjectItem]] = None
    certifications: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    sections_order: List[str] = ["personal_info", "summary", "experience", "education", "skills"]
