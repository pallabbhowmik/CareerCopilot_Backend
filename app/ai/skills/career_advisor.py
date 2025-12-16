"""
Career Transition Advisor Skill

Provides advice for career changers moving between industries/roles.
Uses conservative AI reasoning with appropriate uncertainty.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import time
import re

from . import AISkill, SkillInput, SkillOutput, SkillCategory, ToneConstraint


@dataclass
class TransferableSkill:
    """A skill that transfers between roles"""
    skill: str
    source_context: str
    target_application: str
    transferability_score: float  # 0-100
    framing_suggestion: str


@dataclass
class TransitionAdvice:
    """Career transition advice"""
    category: str
    advice: str
    confidence: float
    supporting_evidence: List[str]
    caveats: List[str]


# Career transition mappings
TRANSITION_PATTERNS = {
    "teacher_to_corporate_trainer": {
        "transferable": [
            ("curriculum design", "training program development"),
            ("classroom management", "workshop facilitation"),
            ("student assessment", "performance evaluation"),
            ("lesson planning", "training material creation"),
        ],
        "skills_to_develop": ["corporate terminology", "business acumen", "LMS platforms"],
        "key_reframes": {
            "students": "learners",
            "classroom": "training sessions",
            "grades": "competency assessments"
        }
    },
    "military_to_civilian": {
        "transferable": [
            ("leadership", "team leadership"),
            ("mission planning", "project management"),
            ("logistics", "operations management"),
            ("training subordinates", "team development"),
        ],
        "skills_to_develop": ["civilian workplace norms", "business communication"],
        "key_reframes": {
            "commanded": "led",
            "subordinates": "team members",
            "mission": "project/initiative",
            "personnel": "staff"
        }
    },
    "technical_to_management": {
        "transferable": [
            ("technical problem solving", "strategic problem solving"),
            ("code review", "team performance review"),
            ("system architecture", "organizational planning"),
            ("documentation", "process documentation"),
        ],
        "skills_to_develop": ["people management", "budgeting", "stakeholder communication"],
        "key_reframes": {
            "built": "led development of",
            "coded": "oversaw technical implementation of"
        }
    },
    "retail_to_sales": {
        "transferable": [
            ("customer service", "client relationship management"),
            ("upselling", "consultative selling"),
            ("inventory management", "pipeline management"),
            ("store metrics", "sales KPIs"),
        ],
        "skills_to_develop": ["CRM tools", "B2B communication", "sales methodology"],
        "key_reframes": {
            "customers": "clients",
            "store": "territory/accounts"
        }
    }
}


class CareerTransitionAdvisor(AISkill):
    """
    Advises on career transitions with transferable skill mapping.
    
    Single responsibility: Identify transferable skills and provide transition advice.
    
    CRITICAL CONSTRAINTS:
    - NEVER guarantee success in transition
    - ALWAYS express appropriate uncertainty
    - MUST provide realistic expectations
    - SHOULD highlight genuine transferable skills
    """
    
    name = "career_transition_advisor"
    version = "1.0.0"
    category = SkillCategory.RECOMMENDATION
    requires_ai = True  # Best with AI for nuanced advice
    
    # Allowed tones for sensitive career advice
    allowed_tones = [ToneConstraint.SUPPORTIVE, ToneConstraint.CAUTIOUS]
    
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
        
        # Get transition context
        current_role = input_data.context.get("current_role", "")
        target_role = input_data.context.get("target_role", "")
        years_experience = input_data.context.get("years_experience", 0)
        
        # Identify transferable skills
        transferable_skills = self._identify_transferable_skills(
            input_data.primary_content,
            current_role,
            target_role
        )
        
        # Generate transition advice
        advice = self._generate_advice(
            transferable_skills,
            current_role,
            target_role,
            years_experience,
            input_data.tone
        )
        
        # Calculate transition viability
        viability_score = self._calculate_viability(
            transferable_skills,
            current_role,
            target_role,
            years_experience
        )
        
        # Generate reframing suggestions
        reframes = self._generate_reframes(current_role, target_role)
        
        execution_time = (time.time() - start_time) * 1000
        
        return SkillOutput(
            result={
                "viability_score": viability_score,
                "transferable_skills": [self._skill_to_dict(s) for s in transferable_skills],
                "advice": [self._advice_to_dict(a) for a in advice],
                "reframes": reframes,
                "summary": self._generate_summary(viability_score, transferable_skills, input_data.tone),
                "important_caveats": self._get_standard_caveats()
            },
            confidence=self._calculate_confidence(transferable_skills, advice),
            reasoning_trace=self._build_reasoning(current_role, target_role, transferable_skills),
            skill_name=self.name,
            skill_version=self.version,
            execution_time_ms=execution_time,
            input_hash=self._hash_input(input_data)
        )
    
    def _identify_transferable_skills(
        self,
        resume_content: str,
        current_role: str,
        target_role: str
    ) -> List[TransferableSkill]:
        """Identify skills that transfer between roles"""
        transferable = []
        content_lower = resume_content.lower()
        
        # Find matching transition pattern
        pattern_key = self._find_transition_pattern(current_role, target_role)
        
        if pattern_key and pattern_key in TRANSITION_PATTERNS:
            pattern = TRANSITION_PATTERNS[pattern_key]
            
            for source_skill, target_skill in pattern.get("transferable", []):
                # Check if source skill is in resume
                if source_skill.lower() in content_lower:
                    transferable.append(TransferableSkill(
                        skill=source_skill,
                        source_context=f"From your {current_role} experience",
                        target_application=f"Applies as {target_skill}",
                        transferability_score=85,
                        framing_suggestion=f"Reframe '{source_skill}' as '{target_skill}'"
                    ))
        
        # General transferable skills
        general_skills = [
            ("communication", "stakeholder communication", 90),
            ("problem solving", "analytical thinking", 95),
            ("team collaboration", "cross-functional collaboration", 85),
            ("project management", "project leadership", 90),
            ("data analysis", "data-driven decision making", 85),
            ("presentation", "executive communication", 80),
        ]
        
        for skill, target_name, score in general_skills:
            if skill in content_lower and not any(t.skill == skill for t in transferable):
                transferable.append(TransferableSkill(
                    skill=skill,
                    source_context="General professional skill",
                    target_application=f"Valuable as {target_name}",
                    transferability_score=score,
                    framing_suggestion=f"Emphasize your {skill} experience with specific examples"
                ))
        
        # Sort by transferability
        transferable.sort(key=lambda x: x.transferability_score, reverse=True)
        
        return transferable[:10]  # Top 10
    
    def _find_transition_pattern(self, current: str, target: str) -> Optional[str]:
        """Find matching transition pattern"""
        current_lower = current.lower()
        target_lower = target.lower()
        
        pattern_matches = {
            ("teacher", "trainer"): "teacher_to_corporate_trainer",
            ("military", "civilian"): "military_to_civilian",
            ("developer", "manager"): "technical_to_management",
            ("engineer", "manager"): "technical_to_management",
            ("retail", "sales"): "retail_to_sales",
        }
        
        for (curr_key, targ_key), pattern in pattern_matches.items():
            if curr_key in current_lower and targ_key in target_lower:
                return pattern
        
        return None
    
    def _generate_advice(
        self,
        transferable_skills: List[TransferableSkill],
        current_role: str,
        target_role: str,
        years_experience: int,
        tone: ToneConstraint
    ) -> List[TransitionAdvice]:
        """Generate transition advice"""
        advice = []
        
        # Skill leverage advice
        if len(transferable_skills) >= 3:
            top_skills = transferable_skills[:3]
            advice.append(TransitionAdvice(
                category="skill_leverage",
                advice=f"Your strongest transferable skills are: {', '.join(s.skill for s in top_skills)}. "
                       f"Lead with these when positioning yourself for {target_role} roles.",
                confidence=0.8,
                supporting_evidence=[s.framing_suggestion for s in top_skills],
                caveats=["Skill relevance may vary by specific company and role requirements"]
            ))
        
        # Experience reframing advice
        if years_experience > 5:
            advice.append(TransitionAdvice(
                category="experience_framing",
                advice=f"Your {years_experience}+ years of experience demonstrate stability and expertise. "
                       f"Frame this as bringing a 'fresh perspective with proven track record.'",
                confidence=0.7,
                supporting_evidence=[
                    "Experienced professionals often bring valuable insights to new fields",
                    "Maturity and reliability are valued in most roles"
                ],
                caveats=[
                    "Some hiring managers may prefer candidates with direct experience",
                    "You may need to accept a more junior title initially"
                ]
            ))
        
        # Networking advice
        advice.append(TransitionAdvice(
            category="networking",
            advice=f"Consider connecting with professionals who have made similar transitions. "
                   f"They can provide realistic insights and potentially referrals.",
            confidence=0.85,
            supporting_evidence=[
                "Industry connections are often crucial for career changers",
                "Informational interviews can reveal unadvertised opportunities"
            ],
            caveats=["Building a new network takes time and consistent effort"]
        ))
        
        # Upskilling advice
        pattern_key = self._find_transition_pattern(current_role, target_role)
        if pattern_key and pattern_key in TRANSITION_PATTERNS:
            skills_to_develop = TRANSITION_PATTERNS[pattern_key].get("skills_to_develop", [])
            if skills_to_develop:
                advice.append(TransitionAdvice(
                    category="skill_development",
                    advice=f"Consider developing these skills to strengthen your candidacy: "
                           f"{', '.join(skills_to_develop)}.",
                    confidence=0.75,
                    supporting_evidence=["These skills are commonly expected in your target field"],
                    caveats=[
                        "Learning priorities should be based on specific job requirements",
                        "Practical experience often matters more than certifications"
                    ]
                ))
        
        return advice
    
    def _calculate_viability(
        self,
        transferable_skills: List[TransferableSkill],
        current_role: str,
        target_role: str,
        years_experience: int
    ) -> float:
        """Calculate transition viability score"""
        base_score = 50
        
        # Transferable skills boost
        if transferable_skills:
            avg_transferability = sum(s.transferability_score for s in transferable_skills) / len(transferable_skills)
            base_score += avg_transferability * 0.3
        
        # Experience factor
        if years_experience >= 3:
            base_score += 10
        if years_experience >= 7:
            base_score += 5
        
        # Known transition pattern boost
        if self._find_transition_pattern(current_role, target_role):
            base_score += 10
        
        return min(90, max(20, base_score))  # Cap at 90, floor at 20
    
    def _generate_reframes(self, current_role: str, target_role: str) -> Dict[str, str]:
        """Generate language reframing suggestions"""
        pattern_key = self._find_transition_pattern(current_role, target_role)
        
        if pattern_key and pattern_key in TRANSITION_PATTERNS:
            return TRANSITION_PATTERNS[pattern_key].get("key_reframes", {})
        
        # Generic reframes
        return {
            "worked on": "delivered",
            "helped with": "contributed to",
            "was part of": "collaborated on"
        }
    
    def _get_standard_caveats(self) -> List[str]:
        """Standard caveats for career advice"""
        return [
            "Career transitions involve individual circumstances that we cannot fully assess",
            "Success depends on many factors including market conditions and personal effort",
            "Consider consulting with career professionals for personalized guidance",
            "This analysis is based on general patterns and may not apply to your specific situation"
        ]
    
    def _generate_summary(
        self,
        viability_score: float,
        transferable_skills: List[TransferableSkill],
        tone: ToneConstraint
    ) -> str:
        """Generate summary"""
        if tone == ToneConstraint.SUPPORTIVE:
            if viability_score >= 70:
                return (f"Your background shows promising potential for this transition. "
                        f"With {len(transferable_skills)} transferable skills identified, "
                        f"you have a solid foundation to build from.")
            elif viability_score >= 50:
                return (f"This transition is achievable with focused effort. "
                        f"Your {len(transferable_skills)} transferable skills provide a starting point, "
                        f"though some additional development may help.")
            else:
                return (f"This transition may require significant preparation. "
                        f"Consider starting with roles that bridge your current and target fields.")
        else:  # CAUTIOUS
            return (f"Transition viability: {viability_score:.0f}/100. "
                    f"Transferable skills: {len(transferable_skills)}. "
                    f"Review caveats carefully.")
    
    def _calculate_confidence(
        self,
        transferable_skills: List[TransferableSkill],
        advice: List[TransitionAdvice]
    ) -> float:
        """Calculate confidence in advice"""
        if not transferable_skills:
            return 0.4
        
        base = 0.6
        base += len(transferable_skills) * 0.02
        base += len(advice) * 0.03
        
        return min(0.85, base)  # Cap confidence - transitions are uncertain
    
    def _build_reasoning(
        self,
        current_role: str,
        target_role: str,
        transferable_skills: List[TransferableSkill]
    ) -> str:
        """Build reasoning trace"""
        pattern = self._find_transition_pattern(current_role, target_role)
        
        return (
            f"Analyzed transition from '{current_role}' to '{target_role}'. "
            f"Pattern match: {'Yes - ' + pattern if pattern else 'No known pattern'}. "
            f"Identified {len(transferable_skills)} transferable skills. "
            f"Advice generated with appropriate uncertainty for career guidance."
        )
    
    def _skill_to_dict(self, skill: TransferableSkill) -> Dict[str, Any]:
        return {
            "skill": skill.skill,
            "source_context": skill.source_context,
            "target_application": skill.target_application,
            "transferability_score": skill.transferability_score,
            "framing_suggestion": skill.framing_suggestion
        }
    
    def _advice_to_dict(self, advice: TransitionAdvice) -> Dict[str, Any]:
        return {
            "category": advice.category,
            "advice": advice.advice,
            "confidence": advice.confidence,
            "supporting_evidence": advice.supporting_evidence,
            "caveats": advice.caveats
        }
