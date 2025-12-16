"""
Skill Intelligence Engine

Deterministic + AI-assisted skill analysis system.
Provides:
- Skill extraction and normalization
- Evidence scoring
- Gap analysis
- High-ROI skill recommendations
"""
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass
import re
from datetime import datetime

from app.domain.entities.skill import (
    Skill, SkillCategory, SkillLevel, SkillEvidence, EvidenceType,
    SkillGap, SkillProfile, normalize_skill_name, get_skill_category,
    SKILL_ALIASES
)
from app.domain.entities.resume import ResumeEntity, ResumeBullet
from app.domain.entities.job import JobDescriptionEntity, JobSkill


# =============================================================================
# SKILL ONTOLOGY DATA
# =============================================================================

# High-demand skills by category (2024 market data)
HIGH_DEMAND_SKILLS = {
    "technical": ["Python", "JavaScript", "TypeScript", "Go", "Rust", "SQL"],
    "framework": ["React", "Node.js", "FastAPI", "Next.js", "Django", "Spring Boot"],
    "cloud": ["AWS", "Google Cloud", "Microsoft Azure", "Kubernetes", "Docker"],
    "data": ["Machine Learning", "Data Science", "TensorFlow", "PyTorch", "SQL"],
    "soft_skill": ["Communication", "Leadership", "Problem Solving", "Collaboration"]
}

# Skills that are transferable across industries
TRANSFERABLE_SKILLS = {
    "Python", "JavaScript", "SQL", "Git", "Docker",
    "Communication", "Leadership", "Problem Solving", "Project Management",
    "Data Analysis", "Agile", "Scrum"
}

# Skill relationships (parent -> children)
SKILL_HIERARCHY = {
    "JavaScript": ["React", "Vue.js", "Angular", "Node.js", "TypeScript"],
    "Python": ["Django", "FastAPI", "Flask", "TensorFlow", "PyTorch"],
    "Cloud Computing": ["AWS", "Google Cloud", "Microsoft Azure"],
    "DevOps": ["Docker", "Kubernetes", "CI/CD", "Terraform"],
    "Data Science": ["Machine Learning", "Statistics", "Python", "R"]
}

# Action verbs that indicate skill usage
ACTION_VERBS = {
    "led", "developed", "built", "created", "designed", "implemented",
    "managed", "optimized", "architected", "deployed", "automated",
    "analyzed", "improved", "reduced", "increased", "achieved"
}


@dataclass
class SkillMatch:
    """Result of matching a skill"""
    skill_name: str
    normalized_name: str
    matched: bool
    partial_match: bool = False
    match_reason: str = ""
    evidence_strength: float = 0.0


class SkillIntelligenceEngine:
    """
    Skill analysis engine combining deterministic rules with AI assistance.
    
    Core responsibilities:
    1. Extract skills from resume text (deterministic + AI)
    2. Normalize and categorize skills
    3. Score skill evidence strength
    4. Analyze skill gaps against job requirements
    5. Recommend high-ROI skills to learn
    """
    
    def __init__(self, ai_orchestrator=None):
        """
        Args:
            ai_orchestrator: Optional AI orchestrator for enhanced extraction
        """
        self._ai = ai_orchestrator
        
        # Build reverse lookup for skill aliases
        self._alias_lookup: Dict[str, str] = {}
        for alias, canonical in SKILL_ALIASES.items():
            self._alias_lookup[alias.lower()] = canonical
    
    # =========================================================================
    # SKILL EXTRACTION
    # =========================================================================
    
    def extract_skills_from_resume(self, resume: ResumeEntity) -> List[Skill]:
        """
        Extract and analyze all skills from a resume.
        
        Uses multiple strategies:
        1. Explicit skills section
        2. Skills mentioned in experience bullets
        3. Tech stack from projects
        4. Inferred from context
        """
        all_skills: Dict[str, Skill] = {}
        
        # 1. Extract from explicit skills list
        for skill_text in resume.skills:
            skill = self._create_skill(
                skill_text,
                evidence_type=EvidenceType.LISTED,
                source_section="skills"
            )
            self._merge_skill(all_skills, skill)
        
        # 2. Extract from experience bullets
        for i, exp in enumerate(resume.experience):
            for bullet in exp.bullets:
                extracted = self._extract_skills_from_text(bullet.text)
                for skill_name in extracted:
                    skill = self._create_skill(
                        skill_name,
                        evidence_type=EvidenceType.EXPERIENCE,
                        source_section="experience",
                        source_text=bullet.text,
                        company=exp.company,
                        role=exp.role,
                        years_ago=i  # Rough estimate based on position
                    )
                    self._merge_skill(all_skills, skill)
        
        # 3. Extract from projects
        for proj in resume.projects:
            # Tech stack is explicit
            for tech in proj.tech_stack:
                skill = self._create_skill(
                    tech,
                    evidence_type=EvidenceType.PROJECT,
                    source_section="projects",
                    source_text=f"Project: {proj.name}"
                )
                self._merge_skill(all_skills, skill)
            
            # Also check bullets
            for bullet in proj.bullets:
                extracted = self._extract_skills_from_text(bullet.text)
                for skill_name in extracted:
                    skill = self._create_skill(
                        skill_name,
                        evidence_type=EvidenceType.PROJECT,
                        source_section="projects",
                        source_text=bullet.text
                    )
                    self._merge_skill(all_skills, skill)
        
        # 4. Extract from certifications
        for cert in resume.certifications:
            extracted = self._extract_skills_from_text(cert)
            for skill_name in extracted:
                skill = self._create_skill(
                    skill_name,
                    evidence_type=EvidenceType.CERTIFICATION,
                    source_section="certifications",
                    source_text=cert
                )
                self._merge_skill(all_skills, skill)
        
        # Enrich with market data
        skills = list(all_skills.values())
        self._enrich_skills_with_market_data(skills)
        
        return skills
    
    def _extract_skills_from_text(self, text: str) -> List[str]:
        """Extract skill names from free text"""
        found_skills = []
        text_lower = text.lower()
        
        # Check against known skill aliases
        for alias, canonical in self._alias_lookup.items():
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(alias) + r'\b'
            if re.search(pattern, text_lower):
                found_skills.append(canonical)
        
        # Also check for skills in our category list
        from app.domain.entities.skill import SKILL_CATEGORIES
        for skill_name in SKILL_CATEGORIES.keys():
            pattern = r'\b' + re.escape(skill_name.lower()) + r'\b'
            if re.search(pattern, text_lower):
                found_skills.append(skill_name)
        
        return list(set(found_skills))
    
    def _create_skill(
        self,
        skill_text: str,
        evidence_type: EvidenceType,
        source_section: str,
        source_text: Optional[str] = None,
        company: Optional[str] = None,
        role: Optional[str] = None,
        years_ago: Optional[int] = None
    ) -> Skill:
        """Create a Skill entity with evidence"""
        normalized = normalize_skill_name(skill_text)
        category = get_skill_category(skill_text)
        
        evidence = SkillEvidence(
            evidence_type=evidence_type,
            source_section=source_section,
            source_text=source_text,
            company=company,
            role=role,
            years_ago=years_ago,
            confidence=self._calculate_evidence_confidence(evidence_type, source_text)
        )
        
        skill = Skill(
            name=skill_text,
            normalized_name=normalized,
            category=category,
            evidence=[evidence],
            is_transferable=normalized in TRANSFERABLE_SKILLS
        )
        
        return skill
    
    def _calculate_evidence_confidence(
        self, 
        evidence_type: EvidenceType,
        source_text: Optional[str]
    ) -> float:
        """Calculate confidence score for evidence"""
        base_confidence = {
            EvidenceType.CERTIFICATION: 0.95,
            EvidenceType.PROJECT: 0.85,
            EvidenceType.EXPERIENCE: 0.80,
            EvidenceType.EDUCATION: 0.70,
            EvidenceType.LISTED: 0.60,
            EvidenceType.INFERRED: 0.40
        }
        
        confidence = base_confidence.get(evidence_type, 0.50)
        
        # Boost confidence if source text shows actual usage
        if source_text:
            text_lower = source_text.lower()
            if any(verb in text_lower for verb in ACTION_VERBS):
                confidence = min(1.0, confidence + 0.10)
            if any(char.isdigit() for char in source_text):
                # Has metrics
                confidence = min(1.0, confidence + 0.05)
        
        return confidence
    
    def _merge_skill(self, skills_dict: Dict[str, Skill], new_skill: Skill):
        """Merge skill evidence if skill already exists"""
        key = new_skill.normalized_name.lower()
        
        if key in skills_dict:
            # Add evidence to existing skill
            skills_dict[key].evidence.extend(new_skill.evidence)
        else:
            skills_dict[key] = new_skill
    
    def _enrich_skills_with_market_data(self, skills: List[Skill]):
        """Add market intelligence data to skills"""
        for skill in skills:
            normalized = skill.normalized_name
            
            # Check if trending
            skill.is_trending = any(
                normalized in skills_list 
                for skills_list in HIGH_DEMAND_SKILLS.values()
            )
            
            # Set demand level
            if skill.is_trending:
                skill.demand_level = "high"
            elif skill.is_transferable:
                skill.demand_level = "medium"
            else:
                skill.demand_level = "low"
    
    # =========================================================================
    # SKILL MATCHING
    # =========================================================================
    
    def match_skills(
        self,
        user_skills: List[Skill],
        required_skills: List[str]
    ) -> Tuple[List[SkillMatch], List[SkillMatch], List[SkillMatch]]:
        """
        Match user skills against required skills.
        
        Returns:
            Tuple of (matched, partial_matched, missing)
        """
        matched = []
        partial = []
        missing = []
        
        user_skill_names = {s.normalized_name.lower() for s in user_skills}
        user_skill_lookup = {s.normalized_name.lower(): s for s in user_skills}
        
        for required in required_skills:
            normalized_req = normalize_skill_name(required).lower()
            
            # Direct match
            if normalized_req in user_skill_names:
                skill = user_skill_lookup[normalized_req]
                matched.append(SkillMatch(
                    skill_name=required,
                    normalized_name=skill.normalized_name,
                    matched=True,
                    match_reason="Direct match",
                    evidence_strength=skill.evidence_strength
                ))
                continue
            
            # Check for related/parent skills
            partial_match = self._find_partial_match(normalized_req, user_skill_names)
            if partial_match:
                partial.append(SkillMatch(
                    skill_name=required,
                    normalized_name=partial_match[0],
                    matched=False,
                    partial_match=True,
                    match_reason=partial_match[1]
                ))
                continue
            
            # No match
            missing.append(SkillMatch(
                skill_name=required,
                normalized_name=normalize_skill_name(required),
                matched=False,
                match_reason="Not found in resume"
            ))
        
        return matched, partial, missing
    
    def _find_partial_match(
        self, 
        required_skill: str,
        user_skills: Set[str]
    ) -> Optional[Tuple[str, str]]:
        """Find partial/related skill match"""
        # Check skill hierarchy
        for parent, children in SKILL_HIERARCHY.items():
            children_lower = [c.lower() for c in children]
            
            if required_skill == parent.lower():
                # User has a child skill
                for child in children_lower:
                    if child in user_skills:
                        return (child, f"Related skill (knows {child})")
            
            if required_skill in children_lower:
                # User has parent skill
                if parent.lower() in user_skills:
                    return (parent, f"Has foundation ({parent})")
        
        return None
    
    # =========================================================================
    # GAP ANALYSIS
    # =========================================================================
    
    def analyze_skill_gaps(
        self,
        user_skills: List[Skill],
        job: JobDescriptionEntity
    ) -> List[SkillGap]:
        """
        Analyze skill gaps between user profile and job requirements.
        
        Returns prioritized list of skill gaps with recommendations.
        """
        gaps = []
        
        # Get all required skills from job
        required_skills = [s.name for s in job.required_skills]
        preferred_skills = [s.name for s in job.preferred_skills]
        
        matched, partial, missing = self.match_skills(user_skills, required_skills)
        
        # Create gaps for missing skills
        for miss in missing:
            # Find the original JobSkill for importance
            job_skill = next(
                (s for s in job.required_skills if s.name.lower() == miss.skill_name.lower()),
                None
            )
            
            importance = job_skill.importance.value if job_skill else "medium"
            
            gap = SkillGap(
                skill_name=miss.normalized_name,
                importance=importance,
                in_resume=False,
                evidence_strength=0.0,
                required_level=SkillLevel.INTERMEDIATE,
                is_learnable=True,
                learning_time_estimate=self._estimate_learning_time(miss.normalized_name),
                alternative_skills=self._find_alternatives(miss.normalized_name, user_skills),
                priority_score=self._calculate_gap_priority(importance, miss.normalized_name)
            )
            gaps.append(gap)
        
        # Create gaps for partial matches (weaker evidence)
        for part in partial:
            gap = SkillGap(
                skill_name=part.skill_name,
                importance="medium",
                in_resume=True,
                evidence_strength=0.3,  # Partial match
                required_level=SkillLevel.INTERMEDIATE,
                current_level=SkillLevel.BEGINNER,
                is_learnable=True,
                learning_time_estimate="1-2 weeks to strengthen",
                priority_score=0.5
            )
            gaps.append(gap)
        
        # Sort by priority
        gaps.sort(key=lambda g: g.priority_score, reverse=True)
        
        return gaps
    
    def _estimate_learning_time(self, skill_name: str) -> str:
        """Estimate time to learn a skill"""
        # Simplified - could be enhanced with more data
        category = get_skill_category(skill_name)
        
        estimates = {
            SkillCategory.LANGUAGE: "2-4 months",
            SkillCategory.FRAMEWORK: "2-6 weeks",
            SkillCategory.TOOL: "1-2 weeks",
            SkillCategory.CLOUD: "1-2 months",
            SkillCategory.DATABASE: "2-4 weeks",
            SkillCategory.SOFT_SKILL: "Ongoing development",
            SkillCategory.METHODOLOGY: "1-2 weeks",
        }
        
        return estimates.get(category, "2-4 weeks")
    
    def _find_alternatives(
        self, 
        skill_name: str,
        user_skills: List[Skill]
    ) -> List[str]:
        """Find alternative skills the user has"""
        alternatives = []
        
        # Check hierarchy for related skills
        for parent, children in SKILL_HIERARCHY.items():
            if skill_name.lower() == parent.lower():
                for child in children:
                    if any(s.normalized_name.lower() == child.lower() for s in user_skills):
                        alternatives.append(child)
            elif skill_name.lower() in [c.lower() for c in children]:
                # Check if user has other siblings
                for child in children:
                    if child.lower() != skill_name.lower():
                        if any(s.normalized_name.lower() == child.lower() for s in user_skills):
                            alternatives.append(child)
        
        return alternatives[:3]  # Limit to 3
    
    def _calculate_gap_priority(self, importance: str, skill_name: str) -> float:
        """Calculate priority score for addressing a skill gap"""
        base_priority = {
            "critical": 1.0,
            "high": 0.8,
            "medium": 0.5,
            "low": 0.3
        }
        
        priority = base_priority.get(importance, 0.5)
        
        # Boost if skill is trending
        normalized = normalize_skill_name(skill_name)
        if any(normalized in skills for skills in HIGH_DEMAND_SKILLS.values()):
            priority = min(1.0, priority + 0.15)
        
        return priority
    
    # =========================================================================
    # HIGH-ROI SKILL RECOMMENDATIONS
    # =========================================================================
    
    def recommend_high_roi_skills(
        self,
        user_skills: List[Skill],
        target_role: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Recommend high-ROI skills to learn.
        
        Considers:
        - Market demand
        - Transferability
        - Synergy with existing skills
        - Learning investment vs. impact
        """
        user_skill_names = {s.normalized_name.lower() for s in user_skills}
        recommendations = []
        
        # Collect candidate skills from high-demand lists
        candidates = set()
        for skills in HIGH_DEMAND_SKILLS.values():
            candidates.update(skills)
        
        # Filter out skills user already has
        candidates = {s for s in candidates if s.lower() not in user_skill_names}
        
        for skill_name in candidates:
            # Calculate ROI score
            roi_score = self._calculate_skill_roi(skill_name, user_skills, target_role)
            
            recommendations.append({
                "skill": skill_name,
                "category": get_skill_category(skill_name).value,
                "roi_score": roi_score,
                "learning_time": self._estimate_learning_time(skill_name),
                "synergy_with": self._find_synergies(skill_name, user_skills),
                "why_valuable": self._explain_value(skill_name, target_role)
            })
        
        # Sort by ROI and return top N
        recommendations.sort(key=lambda r: r["roi_score"], reverse=True)
        return recommendations[:limit]
    
    def _calculate_skill_roi(
        self,
        skill_name: str,
        user_skills: List[Skill],
        target_role: Optional[str]
    ) -> float:
        """Calculate return on investment for learning a skill"""
        roi = 0.5  # Base
        
        # High demand bonus
        if any(skill_name in skills for skills in HIGH_DEMAND_SKILLS.values()):
            roi += 0.2
        
        # Transferability bonus
        if skill_name in TRANSFERABLE_SKILLS:
            roi += 0.1
        
        # Synergy bonus (builds on existing skills)
        for parent, children in SKILL_HIERARCHY.items():
            if skill_name == parent:
                if any(c.lower() in {s.normalized_name.lower() for s in user_skills} for c in children):
                    roi += 0.15
            elif skill_name in children:
                if parent.lower() in {s.normalized_name.lower() for s in user_skills}:
                    roi += 0.15
        
        return min(1.0, roi)
    
    def _find_synergies(self, skill_name: str, user_skills: List[Skill]) -> List[str]:
        """Find existing skills that synergize with the target skill"""
        synergies = []
        user_names = {s.normalized_name for s in user_skills}
        
        for parent, children in SKILL_HIERARCHY.items():
            if skill_name == parent:
                synergies.extend([c for c in children if c in user_names])
            elif skill_name in children:
                if parent in user_names:
                    synergies.append(parent)
        
        return synergies[:3]
    
    def _explain_value(self, skill_name: str, target_role: Optional[str]) -> str:
        """Generate explanation of why a skill is valuable"""
        category = get_skill_category(skill_name)
        
        explanations = {
            SkillCategory.CLOUD: f"{skill_name} is essential for modern infrastructure and highly sought by employers.",
            SkillCategory.FRAMEWORK: f"{skill_name} is widely used in production applications and valued by tech companies.",
            SkillCategory.LANGUAGE: f"{skill_name} is a versatile language with strong job market demand.",
            SkillCategory.TOOL: f"{skill_name} is an industry-standard tool that improves development workflow.",
            SkillCategory.SOFT_SKILL: f"{skill_name} is crucial for career advancement and team effectiveness."
        }
        
        return explanations.get(category, f"{skill_name} is a valuable skill in the current job market.")
    
    # =========================================================================
    # SKILL PROFILE GENERATION
    # =========================================================================
    
    def generate_skill_profile(
        self,
        resume: ResumeEntity,
        target_job: Optional[JobDescriptionEntity] = None
    ) -> SkillProfile:
        """Generate complete skill profile from resume"""
        skills = self.extract_skills_from_resume(resume)
        
        profile = SkillProfile(
            user_id=resume.user_id,
            skills=skills
        )
        
        # Determine strongest category
        category_counts: Dict[SkillCategory, int] = {}
        for skill in skills:
            category_counts[skill.category] = category_counts.get(skill.category, 0) + 1
        
        if category_counts:
            profile.strongest_category = max(category_counts, key=category_counts.get)
        
        # Analyze gaps if job provided
        if target_job:
            profile.skill_gaps_for_target = self.analyze_skill_gaps(skills, target_job)
        
        # Get high-ROI recommendations
        recs = self.recommend_high_roi_skills(skills)
        profile.high_roi_skills = [r["skill"] for r in recs]
        
        return profile
