"""
Skill Gap Reasoner

Analyzes gaps between user skills and job requirements.
Provides reasoning about what skills to prioritize learning.
"""
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field
import time
import re

from . import AISkill, SkillInput, SkillOutput, SkillCategory, ToneConstraint


@dataclass 
class SkillGap:
    """A skill gap between resume and requirements"""
    skill: str
    importance: str  # critical, important, nice_to_have
    gap_type: str    # missing, partial, outdated
    current_level: Optional[str] = None
    required_level: Optional[str] = None
    reasoning: str = ""
    learning_path: str = ""


@dataclass
class SkillStrength:
    """A skill strength the candidate has"""
    skill: str
    evidence: str
    relevance: str  # high, medium, low


# Skill categories and their typical keywords
SKILL_CATEGORIES = {
    "programming": [
        "python", "javascript", "java", "c++", "c#", "go", "rust", "ruby",
        "typescript", "kotlin", "swift", "php", "scala", "perl"
    ],
    "frontend": [
        "react", "angular", "vue", "svelte", "html", "css", "sass", "tailwind",
        "webpack", "next.js", "nuxt", "gatsby"
    ],
    "backend": [
        "node.js", "django", "flask", "fastapi", "spring", "express", "rails",
        "asp.net", "laravel", "gin"
    ],
    "database": [
        "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
        "dynamodb", "cassandra", "oracle", "sql server"
    ],
    "cloud": [
        "aws", "azure", "gcp", "google cloud", "heroku", "digitalocean",
        "lambda", "ec2", "s3", "kubernetes", "docker"
    ],
    "data_science": [
        "machine learning", "deep learning", "tensorflow", "pytorch", "pandas",
        "numpy", "scikit-learn", "nlp", "computer vision", "data analysis"
    ],
    "devops": [
        "ci/cd", "jenkins", "github actions", "gitlab ci", "terraform",
        "ansible", "prometheus", "grafana", "linux", "bash"
    ],
    "soft_skills": [
        "leadership", "communication", "teamwork", "problem solving",
        "project management", "agile", "scrum", "mentoring"
    ]
}


class SkillGapReasoner(AISkill):
    """
    Analyzes skill gaps and provides learning recommendations.
    
    Single responsibility: Compare skills and reason about gaps.
    """
    
    name = "skill_gap_reasoner"
    version = "1.0.0"
    category = SkillCategory.ANALYSIS
    requires_ai = False  # Enhanced with AI when available
    
    async def execute(self, input_data: SkillInput) -> SkillOutput:
        start_time = time.time()
        
        errors = self.validate_input(input_data)
        if errors:
            return SkillOutput(
                result={"error": errors},
                confidence=0,
                reasoning_trace="Input validation failed",
                skill_name=self.name,
                skill_version=self.version,
                execution_time_ms=0,
                warnings=errors
            )
        
        # Extract skills from resume content
        resume_skills = self._extract_skills(input_data.primary_content)
        
        # Extract required skills from job description
        job_desc = input_data.context.get("job_description", "")
        required_skills = self._extract_required_skills(job_desc)
        
        # Analyze gaps
        gaps = self._analyze_gaps(resume_skills, required_skills)
        
        # Identify strengths
        strengths = self._identify_strengths(resume_skills, required_skills)
        
        # Generate prioritized learning path
        learning_priorities = self._prioritize_learning(gaps)
        
        # Calculate match score
        match_score = self._calculate_match_score(resume_skills, required_skills, gaps)
        
        execution_time = (time.time() - start_time) * 1000
        
        return SkillOutput(
            result={
                "match_score": match_score,
                "skills_found": len(resume_skills),
                "skills_required": len(required_skills),
                "gap_count": len(gaps),
                "gaps": [self._gap_to_dict(g) for g in gaps],
                "strengths": [self._strength_to_dict(s) for s in strengths],
                "learning_priorities": learning_priorities,
                "summary": self._generate_summary(gaps, strengths, match_score, input_data.tone)
            },
            confidence=self._calculate_confidence(resume_skills, required_skills),
            reasoning_trace=self._build_reasoning(resume_skills, required_skills, gaps),
            skill_name=self.name,
            skill_version=self.version,
            execution_time_ms=execution_time,
            input_hash=self._hash_input(input_data)
        )
    
    def _extract_skills(self, content: str) -> Dict[str, List[str]]:
        """Extract skills from content by category"""
        content_lower = content.lower()
        found_skills = {}
        
        for category, skills in SKILL_CATEGORIES.items():
            category_skills = []
            for skill in skills:
                # Match whole word
                pattern = r'\b' + re.escape(skill) + r'\b'
                if re.search(pattern, content_lower):
                    category_skills.append(skill)
            
            if category_skills:
                found_skills[category] = category_skills
        
        return found_skills
    
    def _extract_required_skills(self, job_desc: str) -> Dict[str, Tuple[str, str]]:
        """
        Extract required skills from job description with importance level.
        
        Returns: {skill: (importance, context)}
        """
        if not job_desc:
            return {}
        
        job_lower = job_desc.lower()
        required = {}
        
        # Importance indicators
        critical_patterns = [
            r'(?:must|required|essential|mandatory)\s+(?:have|possess|be)\s+.*?(\w+(?:\s+\w+)?)',
            r'(\w+(?:\s+\w+)?)\s+(?:is\s+)?required',
            r'(?:strong|expert|deep)\s+(?:knowledge|experience)\s+(?:in|with)\s+(\w+)',
        ]
        
        important_patterns = [
            r'(?:should|ideally|preferred)\s+(?:have|know)\s+(\w+)',
            r'(\w+)\s+(?:experience|skills?)\s+(?:is\s+)?preferred',
        ]
        
        # Check each skill category
        for category, skills in SKILL_CATEGORIES.items():
            for skill in skills:
                pattern = r'\b' + re.escape(skill) + r'\b'
                if re.search(pattern, job_lower):
                    # Determine importance
                    importance = "nice_to_have"  # Default
                    
                    # Check surrounding context for importance
                    for crit_pattern in critical_patterns:
                        if skill in re.findall(crit_pattern, job_lower):
                            importance = "critical"
                            break
                    
                    if importance != "critical":
                        for imp_pattern in important_patterns:
                            if skill in re.findall(imp_pattern, job_lower):
                                importance = "important"
                                break
                    
                    # If skill appears multiple times, increase importance
                    count = len(re.findall(pattern, job_lower))
                    if count >= 3 and importance == "nice_to_have":
                        importance = "important"
                    
                    required[skill] = (importance, category)
        
        return required
    
    def _analyze_gaps(
        self,
        resume_skills: Dict[str, List[str]],
        required_skills: Dict[str, Tuple[str, str]]
    ) -> List[SkillGap]:
        """Analyze gaps between resume skills and requirements"""
        gaps = []
        
        # Flatten resume skills
        all_resume_skills = set()
        for skills in resume_skills.values():
            all_resume_skills.update(skill.lower() for skill in skills)
        
        for skill, (importance, category) in required_skills.items():
            if skill not in all_resume_skills:
                # Check for partial matches
                gap_type = "missing"
                current_level = None
                
                # Look for related skills
                related = self._find_related_skills(skill, all_resume_skills)
                if related:
                    gap_type = "partial"
                    current_level = f"Related skills: {', '.join(related)}"
                
                # Generate reasoning
                reasoning = self._generate_gap_reasoning(skill, importance, gap_type, category)
                
                # Generate learning path
                learning_path = self._suggest_learning_path(skill, category)
                
                gaps.append(SkillGap(
                    skill=skill,
                    importance=importance,
                    gap_type=gap_type,
                    current_level=current_level,
                    required_level="proficient" if importance == "critical" else "familiar",
                    reasoning=reasoning,
                    learning_path=learning_path
                ))
        
        # Sort by importance
        importance_order = {"critical": 0, "important": 1, "nice_to_have": 2}
        gaps.sort(key=lambda g: importance_order.get(g.importance, 3))
        
        return gaps
    
    def _find_related_skills(self, target_skill: str, user_skills: set) -> List[str]:
        """Find related skills the user has"""
        related = []
        
        # Skill relationships
        relationships = {
            "react": ["javascript", "typescript", "frontend"],
            "django": ["python", "backend"],
            "fastapi": ["python", "backend"],
            "aws": ["cloud", "devops"],
            "kubernetes": ["docker", "devops"],
            "tensorflow": ["python", "machine learning"],
        }
        
        if target_skill in relationships:
            for related_skill in relationships[target_skill]:
                if related_skill in user_skills:
                    related.append(related_skill)
        
        return related
    
    def _generate_gap_reasoning(
        self,
        skill: str,
        importance: str,
        gap_type: str,
        category: str
    ) -> str:
        """Generate reasoning for why this gap matters"""
        if importance == "critical":
            return (f"{skill.title()} is a critical requirement for this role. "
                    f"Without demonstrated experience, your application may be filtered out.")
        elif importance == "important":
            return (f"{skill.title()} is mentioned as important. "
                    f"Having this skill would strengthen your candidacy.")
        else:
            return (f"{skill.title()} is listed as nice-to-have. "
                    f"This is lower priority but could differentiate you from other candidates.")
    
    def _suggest_learning_path(self, skill: str, category: str) -> str:
        """Suggest a learning path for the skill"""
        learning_paths = {
            "programming": "Online courses (Coursera, Udemy), coding challenges (LeetCode), personal projects",
            "frontend": "Build portfolio projects, contribute to open source, follow tutorials",
            "backend": "Build APIs, learn frameworks, study system design",
            "database": "SQL practice (HackerRank), database design courses, hands-on projects",
            "cloud": "Cloud provider certifications (AWS/Azure/GCP), hands-on labs, practice projects",
            "data_science": "Kaggle competitions, online courses, build ML projects",
            "devops": "Set up CI/CD pipelines, learn containerization, infrastructure as code projects",
            "soft_skills": "Leadership courses, volunteer to lead projects, seek mentorship"
        }
        
        return learning_paths.get(category, "Online courses and hands-on practice")
    
    def _identify_strengths(
        self,
        resume_skills: Dict[str, List[str]],
        required_skills: Dict[str, Tuple[str, str]]
    ) -> List[SkillStrength]:
        """Identify skill strengths"""
        strengths = []
        
        all_resume_skills = set()
        for skills in resume_skills.values():
            all_resume_skills.update(skill.lower() for skill in skills)
        
        for skill, (importance, category) in required_skills.items():
            if skill in all_resume_skills:
                relevance = "high" if importance == "critical" else "medium" if importance == "important" else "low"
                strengths.append(SkillStrength(
                    skill=skill,
                    evidence=f"Found in resume under {category}",
                    relevance=relevance
                ))
        
        # Sort by relevance
        relevance_order = {"high": 0, "medium": 1, "low": 2}
        strengths.sort(key=lambda s: relevance_order.get(s.relevance, 3))
        
        return strengths
    
    def _prioritize_learning(self, gaps: List[SkillGap]) -> List[Dict[str, Any]]:
        """Prioritize learning based on gaps"""
        priorities = []
        
        for i, gap in enumerate(gaps[:5]):  # Top 5 priorities
            priorities.append({
                "priority": i + 1,
                "skill": gap.skill,
                "importance": gap.importance,
                "reason": gap.reasoning,
                "suggested_path": gap.learning_path
            })
        
        return priorities
    
    def _calculate_match_score(
        self,
        resume_skills: Dict[str, List[str]],
        required_skills: Dict[str, Tuple[str, str]],
        gaps: List[SkillGap]
    ) -> float:
        """Calculate overall skill match score"""
        if not required_skills:
            return 100  # No requirements means 100% match
        
        # Flatten resume skills
        all_resume_skills = set()
        for skills in resume_skills.values():
            all_resume_skills.update(skill.lower() for skill in skills)
        
        # Weight by importance
        weights = {"critical": 3, "important": 2, "nice_to_have": 1}
        total_weight = sum(weights[imp] for imp, _ in required_skills.values())
        
        matched_weight = 0
        for skill, (importance, _) in required_skills.items():
            if skill in all_resume_skills:
                matched_weight += weights[importance]
            elif any(g.skill == skill and g.gap_type == "partial" for g in gaps):
                matched_weight += weights[importance] * 0.5  # Partial credit
        
        return (matched_weight / total_weight * 100) if total_weight > 0 else 0
    
    def _calculate_confidence(
        self,
        resume_skills: Dict[str, List[str]],
        required_skills: Dict[str, Tuple[str, str]]
    ) -> float:
        """Calculate confidence in analysis"""
        # More data = higher confidence
        skill_count = sum(len(skills) for skills in resume_skills.values())
        req_count = len(required_skills)
        
        if skill_count == 0 or req_count == 0:
            return 0.5
        
        return min(0.95, 0.6 + (skill_count / 50) * 0.2 + (req_count / 20) * 0.15)
    
    def _build_reasoning(
        self,
        resume_skills: Dict[str, List[str]],
        required_skills: Dict[str, Tuple[str, str]],
        gaps: List[SkillGap]
    ) -> str:
        """Build reasoning trace"""
        skill_count = sum(len(skills) for skills in resume_skills.values())
        critical_gaps = len([g for g in gaps if g.importance == "critical"])
        
        return (
            f"Extracted {skill_count} skills from resume across {len(resume_skills)} categories. "
            f"Job requires {len(required_skills)} skills. "
            f"Found {len(gaps)} gaps, {critical_gaps} critical. "
            f"Analysis based on keyword matching and importance inference."
        )
    
    def _generate_summary(
        self,
        gaps: List[SkillGap],
        strengths: List[SkillStrength],
        match_score: float,
        tone: ToneConstraint
    ) -> str:
        """Generate human-readable summary"""
        critical_gaps = [g for g in gaps if g.importance == "critical"]
        high_relevance_strengths = [s for s in strengths if s.relevance == "high"]
        
        if tone == ToneConstraint.SUPPORTIVE:
            if match_score >= 80:
                return (f"Great match! Your skill set aligns well with the requirements ({match_score:.0f}% match). "
                        f"You have {len(high_relevance_strengths)} key skills they're looking for.")
            elif match_score >= 60:
                return (f"Solid foundation ({match_score:.0f}% match). You have many relevant skills, "
                        f"and addressing {len(critical_gaps)} critical gap(s) would strengthen your application.")
            else:
                return (f"This role may require some upskilling ({match_score:.0f}% match). "
                        f"Focus on the {len(critical_gaps)} critical skill(s) to improve your chances.")
        else:
            return f"Match: {match_score:.0f}%. Critical gaps: {len(critical_gaps)}. Key strengths: {len(high_relevance_strengths)}."
    
    def _gap_to_dict(self, gap: SkillGap) -> Dict[str, Any]:
        return {
            "skill": gap.skill,
            "importance": gap.importance,
            "gap_type": gap.gap_type,
            "current_level": gap.current_level,
            "required_level": gap.required_level,
            "reasoning": gap.reasoning,
            "learning_path": gap.learning_path
        }
    
    def _strength_to_dict(self, strength: SkillStrength) -> Dict[str, Any]:
        return {
            "skill": strength.skill,
            "evidence": strength.evidence,
            "relevance": strength.relevance
        }
