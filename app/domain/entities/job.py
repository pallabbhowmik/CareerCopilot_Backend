"""
Job Description Domain Entities

Pure domain objects for job analysis.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4


class RequirementType(str, Enum):
    """Types of job requirements"""
    REQUIRED = "required"         # Must have
    PREFERRED = "preferred"       # Nice to have
    BONUS = "bonus"               # Extra credit
    INFERRED = "inferred"         # AI-detected but not explicit


class SkillImportance(str, Enum):
    """Importance level for job skills"""
    CRITICAL = "critical"    # Deal-breaker if missing
    HIGH = "high"            # Strongly expected
    MEDIUM = "medium"        # Helpful but not required
    LOW = "low"              # Nice to have


class ExperienceLevel(str, Enum):
    """Standard experience levels"""
    ENTRY = "entry"           # 0-2 years
    MID = "mid"               # 2-5 years
    SENIOR = "senior"         # 5-8 years
    LEAD = "lead"             # 8-12 years
    PRINCIPAL = "principal"   # 12+ years
    UNSPECIFIED = "unspecified"


@dataclass
class JobRequirement:
    """Individual job requirement with metadata"""
    id: UUID = field(default_factory=uuid4)
    text: str = ""
    requirement_type: RequirementType = RequirementType.REQUIRED
    
    # Extracted data
    skills: List[str] = field(default_factory=list)
    years_experience: Optional[int] = None
    education_level: Optional[str] = None
    
    # Source tracking
    original_text: Optional[str] = None
    confidence: float = 0.8  # 0-1 confidence in extraction
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "text": self.text,
            "requirement_type": self.requirement_type.value,
            "skills": self.skills,
            "years_experience": self.years_experience,
            "education_level": self.education_level,
            "confidence": self.confidence
        }


@dataclass
class JobSkill:
    """Skill extracted from job description"""
    name: str = ""
    importance: SkillImportance = SkillImportance.MEDIUM
    category: str = ""  # e.g., "Programming", "Framework", "Soft Skill"
    
    # Context
    mentioned_count: int = 1
    context_snippets: List[str] = field(default_factory=list)
    
    # Analysis
    is_common: bool = False  # Is this skill common in the industry?
    difficulty_to_learn: str = "medium"  # low/medium/high
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "importance": self.importance.value,
            "category": self.category,
            "mentioned_count": self.mentioned_count,
            "is_common": self.is_common
        }


@dataclass
class CompanyInfo:
    """Company information extracted from JD"""
    name: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[str] = None  # startup/mid/enterprise
    culture_signals: List[str] = field(default_factory=list)
    benefits_mentioned: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "industry": self.industry,
            "size": self.size,
            "culture_signals": self.culture_signals,
            "benefits_mentioned": self.benefits_mentioned
        }


@dataclass
class SalaryInfo:
    """Salary information if available"""
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    currency: str = "USD"
    period: str = "yearly"  # yearly/monthly/hourly
    is_estimated: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "min_salary": self.min_salary,
            "max_salary": self.max_salary,
            "currency": self.currency,
            "period": self.period,
            "is_estimated": self.is_estimated
        }


@dataclass
class JobDescriptionEntity:
    """
    Core Job Description Domain Entity
    
    Represents a fully analyzed job description with extracted requirements,
    skills, and metadata for matching against resumes.
    """
    id: UUID = field(default_factory=uuid4)
    
    # Basic info
    title: str = ""
    company: CompanyInfo = field(default_factory=CompanyInfo)
    location: Optional[str] = None
    is_remote: bool = False
    job_type: str = "full-time"  # full-time/part-time/contract
    
    # Content
    raw_text: str = ""
    description_summary: Optional[str] = None
    
    # Extracted requirements
    requirements: List[JobRequirement] = field(default_factory=list)
    required_skills: List[JobSkill] = field(default_factory=list)
    preferred_skills: List[JobSkill] = field(default_factory=list)
    
    # Experience
    experience_level: ExperienceLevel = ExperienceLevel.UNSPECIFIED
    years_experience_min: Optional[int] = None
    years_experience_max: Optional[int] = None
    
    # Education
    education_required: Optional[str] = None
    education_preferred: Optional[str] = None
    
    # Compensation
    salary: SalaryInfo = field(default_factory=SalaryInfo)
    
    # Metadata
    source_url: Optional[str] = None
    posted_date: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # Analysis metadata
    parsing_confidence: float = 0.8
    analysis_version: str = "1.0"
    
    @property
    def all_skills(self) -> List[str]:
        """Get all skill names"""
        skills = [s.name for s in self.required_skills]
        skills.extend([s.name for s in self.preferred_skills])
        return list(set(skills))
    
    @property
    def critical_skills(self) -> List[str]:
        """Get skills marked as critical"""
        return [
            s.name for s in self.required_skills 
            if s.importance == SkillImportance.CRITICAL
        ]
    
    @property
    def total_requirements(self) -> int:
        return len(self.requirements)
    
    @property
    def required_requirements(self) -> List[JobRequirement]:
        return [r for r in self.requirements if r.requirement_type == RequirementType.REQUIRED]
    
    def get_skills_by_category(self) -> Dict[str, List[JobSkill]]:
        """Group all skills by category"""
        categories: Dict[str, List[JobSkill]] = {}
        for skill in self.required_skills + self.preferred_skills:
            if skill.category not in categories:
                categories[skill.category] = []
            categories[skill.category].append(skill)
        return categories
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "title": self.title,
            "company": self.company.to_dict(),
            "location": self.location,
            "is_remote": self.is_remote,
            "job_type": self.job_type,
            "description_summary": self.description_summary,
            "requirements": [r.to_dict() for r in self.requirements],
            "required_skills": [s.to_dict() for s in self.required_skills],
            "preferred_skills": [s.to_dict() for s in self.preferred_skills],
            "experience_level": self.experience_level.value,
            "years_experience_min": self.years_experience_min,
            "years_experience_max": self.years_experience_max,
            "education_required": self.education_required,
            "salary": self.salary.to_dict(),
            "source_url": self.source_url,
            "parsing_confidence": self.parsing_confidence,
            "all_skills": self.all_skills,
            "critical_skills": self.critical_skills,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_raw_text(cls, raw_text: str, title: str = "", company: str = "") -> "JobDescriptionEntity":
        """Create a basic entity from raw text (to be enhanced by analyzers)"""
        entity = cls(
            title=title,
            raw_text=raw_text
        )
        entity.company.name = company
        return entity
