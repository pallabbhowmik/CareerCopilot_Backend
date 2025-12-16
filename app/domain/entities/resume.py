"""
Resume Domain Entities

Pure domain objects representing resume concepts.
No database or framework dependencies.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4


class SectionType(str, Enum):
    """Standard resume section types"""
    PERSONAL_INFO = "personal_info"
    SUMMARY = "summary"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    SKILLS = "skills"
    PROJECTS = "projects"
    CERTIFICATIONS = "certifications"
    LANGUAGES = "languages"
    AWARDS = "awards"
    PUBLICATIONS = "publications"
    VOLUNTEER = "volunteer"
    CUSTOM = "custom"


class BulletStrength(str, Enum):
    """Bullet point quality assessment"""
    STRONG = "strong"      # Has action verb + metrics + impact
    MODERATE = "moderate"  # Has action verb, missing metrics
    WEAK = "weak"          # Generic or passive
    AMBIGUOUS = "ambiguous"


class ParsingConfidence(str, Enum):
    """Confidence level for parsed data"""
    HIGH = "high"      # >90% certain
    MEDIUM = "medium"  # 70-90% certain
    LOW = "low"        # <70% certain


@dataclass
class PersonalInfo:
    """Contact and personal information"""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None
    
    @property
    def is_complete(self) -> bool:
        """Check if minimum required info is present"""
        return bool(self.name and self.email)
    
    @property
    def completeness_score(self) -> int:
        """Score 0-100 for contact info completeness"""
        fields = [self.name, self.email, self.phone, self.linkedin, self.location]
        filled = sum(1 for f in fields if f)
        return int((filled / len(fields)) * 100)


@dataclass
class ResumeBullet:
    """Individual bullet point with metadata"""
    id: UUID = field(default_factory=uuid4)
    text: str = ""
    
    # Analysis results
    strength: BulletStrength = BulletStrength.MODERATE
    has_action_verb: bool = False
    has_metrics: bool = False
    has_impact: bool = False
    detected_skills: List[str] = field(default_factory=list)
    
    # Parsing metadata
    confidence: ParsingConfidence = ParsingConfidence.MEDIUM
    original_text: Optional[str] = None
    
    # AI suggestions
    improved_version: Optional[str] = None
    improvement_explanation: Optional[str] = None
    
    def calculate_strength(self) -> BulletStrength:
        """Calculate bullet strength based on components"""
        score = sum([self.has_action_verb, self.has_metrics, self.has_impact])
        if score >= 3:
            return BulletStrength.STRONG
        elif score >= 2:
            return BulletStrength.MODERATE
        else:
            return BulletStrength.WEAK
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "text": self.text,
            "strength": self.strength.value,
            "has_action_verb": self.has_action_verb,
            "has_metrics": self.has_metrics,
            "has_impact": self.has_impact,
            "detected_skills": self.detected_skills,
            "confidence": self.confidence.value,
            "improved_version": self.improved_version
        }


@dataclass
class ExperienceEntry:
    """Single work experience entry"""
    id: UUID = field(default_factory=uuid4)
    company: str = ""
    role: str = ""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    location: Optional[str] = None
    is_current: bool = False
    bullets: List[ResumeBullet] = field(default_factory=list)
    
    # Parsing metadata
    confidence: ParsingConfidence = ParsingConfidence.MEDIUM
    detected_skills: List[str] = field(default_factory=list)
    
    @property
    def duration_months(self) -> Optional[int]:
        """Calculate duration in months if dates available"""
        # Implementation would parse dates
        return None
    
    @property
    def bullet_strength_summary(self) -> Dict[str, int]:
        """Count bullets by strength"""
        summary = {s.value: 0 for s in BulletStrength}
        for bullet in self.bullets:
            summary[bullet.strength.value] += 1
        return summary
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "company": self.company,
            "role": self.role,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "location": self.location,
            "is_current": self.is_current,
            "bullets": [b.to_dict() for b in self.bullets],
            "confidence": self.confidence.value,
            "detected_skills": self.detected_skills
        }


@dataclass
class EducationEntry:
    """Single education entry"""
    id: UUID = field(default_factory=uuid4)
    institution: str = ""
    degree: str = ""
    field_of_study: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    gpa: Optional[str] = None
    location: Optional[str] = None
    honors: Optional[List[str]] = None
    
    confidence: ParsingConfidence = ParsingConfidence.MEDIUM
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "institution": self.institution,
            "degree": self.degree,
            "field_of_study": self.field_of_study,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "gpa": self.gpa,
            "location": self.location,
            "honors": self.honors,
            "confidence": self.confidence.value
        }


@dataclass
class ProjectEntry:
    """Project entry"""
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: Optional[str] = None
    tech_stack: List[str] = field(default_factory=list)
    bullets: List[ResumeBullet] = field(default_factory=list)
    url: Optional[str] = None
    github_url: Optional[str] = None
    
    confidence: ParsingConfidence = ParsingConfidence.MEDIUM
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "tech_stack": self.tech_stack,
            "bullets": [b.to_dict() for b in self.bullets],
            "url": self.url,
            "github_url": self.github_url,
            "confidence": self.confidence.value
        }


@dataclass  
class ResumeSection:
    """Generic resume section with content and metadata"""
    id: UUID = field(default_factory=uuid4)
    section_type: SectionType = SectionType.CUSTOM
    title: str = ""
    content: Any = None  # Typed based on section_type
    order: int = 0
    
    # Parsing metadata
    confidence: ParsingConfidence = ParsingConfidence.MEDIUM
    detected: bool = True  # Was this section found in the original resume?
    ambiguous: bool = False  # Was there uncertainty in parsing?
    
    # Quality signals
    quality_score: int = 0  # 0-100
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class ResumeEntity:
    """
    Core Resume Domain Entity
    
    Represents a fully parsed and analyzed resume with all metadata.
    This is the canonical representation used throughout the system.
    """
    id: UUID = field(default_factory=uuid4)
    user_id: Optional[UUID] = None
    
    # Core content
    personal_info: PersonalInfo = field(default_factory=PersonalInfo)
    summary: Optional[str] = None
    experience: List[ExperienceEntry] = field(default_factory=list)
    education: List[EducationEntry] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    projects: List[ProjectEntry] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    
    # Section ordering
    sections_order: List[SectionType] = field(default_factory=lambda: [
        SectionType.PERSONAL_INFO,
        SectionType.SUMMARY,
        SectionType.EXPERIENCE,
        SectionType.EDUCATION,
        SectionType.SKILLS
    ])
    
    # Metadata
    version: int = 1
    parent_id: Optional[UUID] = None  # For versioning/A-B testing
    variant_group: Optional[str] = None
    
    # Parsing metadata
    raw_text: Optional[str] = None
    file_type: Optional[str] = None
    parsing_confidence: ParsingConfidence = ParsingConfidence.MEDIUM
    parsing_issues: List[str] = field(default_factory=list)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Computed properties
    @property
    def total_experience_years(self) -> float:
        """Estimate total years of experience"""
        # Simplified - would need proper date parsing
        return len(self.experience) * 2.0  # Rough estimate
    
    @property
    def total_bullets(self) -> int:
        """Count all bullet points"""
        count = sum(len(exp.bullets) for exp in self.experience)
        count += sum(len(proj.bullets) for proj in self.projects)
        return count
    
    @property
    def skill_count(self) -> int:
        return len(self.skills)
    
    @property
    def completeness_score(self) -> int:
        """Overall resume completeness 0-100"""
        score = 0
        
        # Personal info (20 points)
        if self.personal_info.is_complete:
            score += 20
        elif self.personal_info.name:
            score += 10
        
        # Summary (10 points)
        if self.summary and len(self.summary) > 50:
            score += 10
        
        # Experience (30 points)
        if self.experience:
            score += min(30, len(self.experience) * 10)
        
        # Education (15 points)
        if self.education:
            score += 15
        
        # Skills (15 points)
        if len(self.skills) >= 5:
            score += 15
        elif self.skills:
            score += 8
        
        # Projects (10 points)
        if self.projects:
            score += 10
        
        return min(100, score)
    
    def get_all_detected_skills(self) -> List[str]:
        """Extract all skills from all sections"""
        skills = set(self.skills)
        
        for exp in self.experience:
            skills.update(exp.detected_skills)
            for bullet in exp.bullets:
                skills.update(bullet.detected_skills)
        
        for proj in self.projects:
            skills.update(proj.tech_stack)
            for bullet in proj.bullets:
                skills.update(bullet.detected_skills)
        
        return list(skills)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "personal_info": {
                "name": self.personal_info.name,
                "email": self.personal_info.email,
                "phone": self.personal_info.phone,
                "linkedin": self.personal_info.linkedin,
                "github": self.personal_info.github,
                "website": self.personal_info.website,
                "location": self.personal_info.location
            },
            "summary": self.summary,
            "experience": [exp.to_dict() for exp in self.experience],
            "education": [edu.to_dict() for edu in self.education],
            "skills": self.skills,
            "projects": [proj.to_dict() for proj in self.projects],
            "certifications": self.certifications,
            "languages": self.languages,
            "sections_order": [s.value for s in self.sections_order],
            "version": self.version,
            "parsing_confidence": self.parsing_confidence.value,
            "parsing_issues": self.parsing_issues,
            "completeness_score": self.completeness_score,
            "total_experience_years": self.total_experience_years,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResumeEntity":
        """Create from dictionary"""
        entity = cls()
        
        # Personal info
        pi_data = data.get("personal_info", {})
        entity.personal_info = PersonalInfo(
            name=pi_data.get("name"),
            email=pi_data.get("email"),
            phone=pi_data.get("phone"),
            linkedin=pi_data.get("linkedin"),
            github=pi_data.get("github"),
            website=pi_data.get("website"),
            location=pi_data.get("location")
        )
        
        entity.summary = data.get("summary")
        entity.skills = data.get("skills", [])
        entity.certifications = data.get("certifications", [])
        entity.languages = data.get("languages", [])
        
        # Experience
        for exp_data in data.get("experience", []):
            exp = ExperienceEntry(
                company=exp_data.get("company", ""),
                role=exp_data.get("role", ""),
                start_date=exp_data.get("start_date"),
                end_date=exp_data.get("end_date"),
                location=exp_data.get("location"),
                is_current=exp_data.get("is_current", False)
            )
            for bullet_data in exp_data.get("bullets", []):
                if isinstance(bullet_data, str):
                    exp.bullets.append(ResumeBullet(text=bullet_data))
                else:
                    exp.bullets.append(ResumeBullet(
                        text=bullet_data.get("text", ""),
                        strength=BulletStrength(bullet_data.get("strength", "moderate"))
                    ))
            entity.experience.append(exp)
        
        # Education
        for edu_data in data.get("education", []):
            entity.education.append(EducationEntry(
                institution=edu_data.get("institution", ""),
                degree=edu_data.get("degree", ""),
                field_of_study=edu_data.get("field", edu_data.get("field_of_study")),
                start_date=edu_data.get("start_date"),
                end_date=edu_data.get("end_date"),
                gpa=edu_data.get("gpa"),
                location=edu_data.get("location")
            ))
        
        # Projects
        for proj_data in data.get("projects", []):
            proj = ProjectEntry(
                name=proj_data.get("name", ""),
                description=proj_data.get("description"),
                tech_stack=proj_data.get("tech_stack", []),
                url=proj_data.get("url"),
                github_url=proj_data.get("github_url")
            )
            for bullet_data in proj_data.get("bullets", []):
                if isinstance(bullet_data, str):
                    proj.bullets.append(ResumeBullet(text=bullet_data))
            entity.projects.append(proj)
        
        return entity
