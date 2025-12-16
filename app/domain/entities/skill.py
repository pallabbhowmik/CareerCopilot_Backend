"""
Skill Domain Entities

Core skill intelligence domain objects.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4


class SkillCategory(str, Enum):
    """Skill categorization"""
    TECHNICAL = "technical"           # Hard technical skills
    FRAMEWORK = "framework"           # Frameworks & libraries
    TOOL = "tool"                     # Development tools
    LANGUAGE = "language"             # Programming languages
    DATABASE = "database"             # Database technologies
    CLOUD = "cloud"                   # Cloud platforms & services
    METHODOLOGY = "methodology"       # Agile, Scrum, etc.
    SOFT_SKILL = "soft_skill"         # Communication, leadership, etc.
    DOMAIN = "domain"                 # Domain expertise
    CERTIFICATION = "certification"   # Professional certifications
    OTHER = "other"


class SkillLevel(str, Enum):
    """Proficiency level"""
    BEGINNER = "beginner"       # Learning, basic knowledge
    INTERMEDIATE = "intermediate"  # Can work independently
    ADVANCED = "advanced"       # Deep expertise
    EXPERT = "expert"           # Industry-recognized expert


class EvidenceType(str, Enum):
    """How skill was demonstrated"""
    LISTED = "listed"                 # Explicitly listed in skills section
    EXPERIENCE = "experience"         # Mentioned in work experience
    PROJECT = "project"               # Demonstrated in projects
    EDUCATION = "education"           # From education/coursework
    CERTIFICATION = "certification"   # Has certification
    INFERRED = "inferred"             # AI-inferred from context


@dataclass
class SkillEvidence:
    """Evidence of skill in resume"""
    evidence_type: EvidenceType = EvidenceType.LISTED
    source_section: str = ""          # Which resume section
    source_text: Optional[str] = None # The text that provides evidence
    confidence: float = 0.8           # 0-1 confidence in this evidence
    
    # For experience/project evidence
    company: Optional[str] = None
    role: Optional[str] = None
    years_ago: Optional[int] = None   # How many years since last used
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_type": self.evidence_type.value,
            "source_section": self.source_section,
            "source_text": self.source_text,
            "confidence": self.confidence,
            "company": self.company,
            "role": self.role,
            "years_ago": self.years_ago
        }


@dataclass
class Skill:
    """
    Core Skill Entity
    
    Represents a skill with evidence and analysis.
    """
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    normalized_name: str = ""         # Canonical form (e.g., "JavaScript" not "JS")
    
    # Classification
    category: SkillCategory = SkillCategory.OTHER
    level: SkillLevel = SkillLevel.INTERMEDIATE
    
    # Evidence from resume
    evidence: List[SkillEvidence] = field(default_factory=list)
    
    # Related skills
    parent_skill: Optional[str] = None      # e.g., React -> JavaScript
    related_skills: List[str] = field(default_factory=list)
    
    # Market intelligence (populated from skill ontology)
    is_trending: bool = False
    demand_level: str = "medium"      # low/medium/high/critical
    typical_salary_impact: Optional[str] = None
    
    # Transferability
    is_transferable: bool = False     # Useful across industries
    transfer_to_roles: List[str] = field(default_factory=list)
    
    @property
    def evidence_strength(self) -> float:
        """Calculate overall evidence strength 0-1"""
        if not self.evidence:
            return 0.0
        
        # Weight by evidence type
        weights = {
            EvidenceType.CERTIFICATION: 1.0,
            EvidenceType.PROJECT: 0.9,
            EvidenceType.EXPERIENCE: 0.85,
            EvidenceType.EDUCATION: 0.7,
            EvidenceType.LISTED: 0.5,
            EvidenceType.INFERRED: 0.3
        }
        
        total_weight = sum(
            weights.get(e.evidence_type, 0.5) * e.confidence 
            for e in self.evidence
        )
        
        # Normalize to 0-1 range, max out at 5 evidence pieces
        return min(1.0, total_weight / 3)
    
    @property
    def has_strong_evidence(self) -> bool:
        """Has concrete evidence beyond just listing"""
        return any(
            e.evidence_type in [EvidenceType.EXPERIENCE, EvidenceType.PROJECT, EvidenceType.CERTIFICATION]
            for e in self.evidence
        )
    
    @property
    def recency_score(self) -> float:
        """How recently was this skill used (0-1, 1 = recent)"""
        min_years = None
        for e in self.evidence:
            if e.years_ago is not None:
                if min_years is None or e.years_ago < min_years:
                    min_years = e.years_ago
        
        if min_years is None:
            return 0.5  # Unknown
        elif min_years <= 1:
            return 1.0
        elif min_years <= 3:
            return 0.8
        elif min_years <= 5:
            return 0.6
        else:
            return 0.4
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "name": self.name,
            "normalized_name": self.normalized_name,
            "category": self.category.value,
            "level": self.level.value,
            "evidence": [e.to_dict() for e in self.evidence],
            "evidence_strength": self.evidence_strength,
            "has_strong_evidence": self.has_strong_evidence,
            "is_trending": self.is_trending,
            "demand_level": self.demand_level,
            "is_transferable": self.is_transferable,
            "related_skills": self.related_skills
        }


@dataclass
class SkillGap:
    """Gap between resume and job requirements"""
    skill_name: str = ""
    importance: str = "medium"  # low/medium/high/critical
    
    # Gap analysis
    in_resume: bool = False
    evidence_strength: float = 0.0
    required_level: SkillLevel = SkillLevel.INTERMEDIATE
    current_level: Optional[SkillLevel] = None
    
    # Recommendations
    is_learnable: bool = True
    learning_time_estimate: Optional[str] = None  # e.g., "2-4 weeks"
    learning_resources: List[str] = field(default_factory=list)
    alternative_skills: List[str] = field(default_factory=list)  # Skills that could substitute
    
    # Priority for addressing
    priority_score: float = 0.0  # 0-1, higher = more urgent to address
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_name": self.skill_name,
            "importance": self.importance,
            "in_resume": self.in_resume,
            "evidence_strength": self.evidence_strength,
            "required_level": self.required_level.value,
            "current_level": self.current_level.value if self.current_level else None,
            "is_learnable": self.is_learnable,
            "learning_time_estimate": self.learning_time_estimate,
            "alternative_skills": self.alternative_skills,
            "priority_score": self.priority_score
        }


@dataclass
class SkillProfile:
    """Complete skill profile for a user"""
    user_id: UUID = field(default_factory=uuid4)
    
    # Categorized skills
    skills: List[Skill] = field(default_factory=list)
    
    # Analysis
    strongest_category: Optional[SkillCategory] = None
    skill_gaps_for_target: List[SkillGap] = field(default_factory=list)
    
    # High ROI recommendations
    high_roi_skills: List[str] = field(default_factory=list)  # Skills that would most improve profile
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def get_skills_by_category(self) -> Dict[str, List[Skill]]:
        """Group skills by category"""
        result: Dict[str, List[Skill]] = {}
        for skill in self.skills:
            cat = skill.category.value
            if cat not in result:
                result[cat] = []
            result[cat].append(skill)
        return result
    
    def get_strong_skills(self) -> List[Skill]:
        """Get skills with strong evidence"""
        return [s for s in self.skills if s.has_strong_evidence]
    
    def get_transferable_skills(self) -> List[Skill]:
        """Get transferable skills"""
        return [s for s in self.skills if s.is_transferable]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": str(self.user_id),
            "skills": [s.to_dict() for s in self.skills],
            "skills_by_category": {
                k: [s.to_dict() for s in v] 
                for k, v in self.get_skills_by_category().items()
            },
            "strongest_category": self.strongest_category.value if self.strongest_category else None,
            "skill_gaps": [g.to_dict() for g in self.skill_gaps_for_target],
            "high_roi_skills": self.high_roi_skills,
            "strong_skills_count": len(self.get_strong_skills()),
            "transferable_skills_count": len(self.get_transferable_skills()),
            "created_at": self.created_at.isoformat()
        }


# Skill Ontology - Common skill mappings and relationships
SKILL_ALIASES: Dict[str, str] = {
    "js": "JavaScript",
    "javascript": "JavaScript",
    "ts": "TypeScript",
    "typescript": "TypeScript",
    "py": "Python",
    "python": "Python",
    "react.js": "React",
    "reactjs": "React",
    "react": "React",
    "node": "Node.js",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "mongo": "MongoDB",
    "mongodb": "MongoDB",
    "aws": "AWS",
    "amazon web services": "AWS",
    "gcp": "Google Cloud",
    "google cloud platform": "Google Cloud",
    "azure": "Microsoft Azure",
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    "docker": "Docker",
    "git": "Git",
    "github": "GitHub",
    "ci/cd": "CI/CD",
    "cicd": "CI/CD",
    "ml": "Machine Learning",
    "machine learning": "Machine Learning",
    "ai": "Artificial Intelligence",
    "artificial intelligence": "Artificial Intelligence",
    "sql": "SQL",
    "nosql": "NoSQL",
    "rest": "REST APIs",
    "restful": "REST APIs",
    "graphql": "GraphQL",
    "agile": "Agile",
    "scrum": "Scrum",
}

SKILL_CATEGORIES: Dict[str, SkillCategory] = {
    "Python": SkillCategory.LANGUAGE,
    "JavaScript": SkillCategory.LANGUAGE,
    "TypeScript": SkillCategory.LANGUAGE,
    "Java": SkillCategory.LANGUAGE,
    "Go": SkillCategory.LANGUAGE,
    "Rust": SkillCategory.LANGUAGE,
    "C++": SkillCategory.LANGUAGE,
    "React": SkillCategory.FRAMEWORK,
    "Node.js": SkillCategory.FRAMEWORK,
    "Django": SkillCategory.FRAMEWORK,
    "FastAPI": SkillCategory.FRAMEWORK,
    "Next.js": SkillCategory.FRAMEWORK,
    "Vue.js": SkillCategory.FRAMEWORK,
    "Angular": SkillCategory.FRAMEWORK,
    "PostgreSQL": SkillCategory.DATABASE,
    "MongoDB": SkillCategory.DATABASE,
    "MySQL": SkillCategory.DATABASE,
    "Redis": SkillCategory.DATABASE,
    "AWS": SkillCategory.CLOUD,
    "Google Cloud": SkillCategory.CLOUD,
    "Microsoft Azure": SkillCategory.CLOUD,
    "Docker": SkillCategory.TOOL,
    "Kubernetes": SkillCategory.TOOL,
    "Git": SkillCategory.TOOL,
    "CI/CD": SkillCategory.METHODOLOGY,
    "Agile": SkillCategory.METHODOLOGY,
    "Scrum": SkillCategory.METHODOLOGY,
    "Communication": SkillCategory.SOFT_SKILL,
    "Leadership": SkillCategory.SOFT_SKILL,
    "Problem Solving": SkillCategory.SOFT_SKILL,
    "Machine Learning": SkillCategory.TECHNICAL,
    "Data Science": SkillCategory.DOMAIN,
}

def normalize_skill_name(skill: str) -> str:
    """Normalize skill name to canonical form"""
    lower = skill.lower().strip()
    return SKILL_ALIASES.get(lower, skill.title())

def get_skill_category(skill: str) -> SkillCategory:
    """Get category for a skill"""
    normalized = normalize_skill_name(skill)
    return SKILL_CATEGORIES.get(normalized, SkillCategory.OTHER)
