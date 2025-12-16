"""
Explainability Engine

Every AI output must be explainable. This engine ensures all analysis
results include:
- Why this matters
- What signal was detected  
- How confident we are
- What to do next
"""
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json

from app.domain.entities.analysis import (
    Explanation, ExplanationType, SignalStrength, 
    ConfidenceLevel, ActionPriority
)


# =============================================================================
# EXPLANATION TEMPLATES
# =============================================================================

EXPLANATION_TEMPLATES = {
    # ATS-related explanations
    "ats_parsing_success": {
        "title": "Resume Parsed Successfully",
        "summary_template": "ATS detected {detected_count} sections from your resume.",
        "detail": "A successful parse means the ATS can read and categorize your resume content. Missing sections may indicate formatting issues or non-standard section headers.",
        "why_matters": "If ATS can't parse your resume, recruiters may never see your qualifications."
    },
    "ats_parsing_fail": {
        "title": "Parsing Issues Detected",
        "summary_template": "ATS struggled to detect {missing_count} key sections.",
        "detail": "Some resume sections weren't recognized. This usually happens with unusual formatting, tables, or non-standard section names.",
        "why_matters": "Without proper parsing, your skills and experience won't be indexed for job matching."
    },
    
    # Skill-related explanations
    "skill_match_strong": {
        "title": "Strong Skill Alignment",
        "summary_template": "{match_pct}% of required skills found on your resume.",
        "detail": "Your skills closely align with what this role requires. Strong skill matches help you rank higher in ATS results.",
        "why_matters": "Skill matching is often the primary factor in ATS ranking."
    },
    "skill_match_partial": {
        "title": "Partial Skill Match",
        "summary_template": "{match_pct}% skill match - some key skills may be missing.",
        "detail": "Your resume shows some relevant skills, but gaps exist. Consider adding missing skills you genuinely possess, or acquiring them.",
        "why_matters": "Skill gaps can disqualify candidates before human review."
    },
    "skill_gap_identified": {
        "title": "Skill Gap Identified",
        "summary_template": "{skill_name} is required but not found on your resume.",
        "detail": "This is a required skill for the role. If you have this skill, make sure it's clearly listed. If not, consider whether to acquire it.",
        "why_matters": "Missing required skills significantly reduce match scores."
    },
    
    # Bullet-related explanations
    "bullet_strength_strong": {
        "title": "Strong Impact Statement",
        "summary_template": "This bullet effectively demonstrates {impact_type}.",
        "detail": "Uses action verbs, includes specific metrics, and clearly shows your impact. This type of bullet resonates with both ATS and human reviewers.",
        "why_matters": "Strong bullets differentiate you from candidates with similar backgrounds."
    },
    "bullet_strength_weak": {
        "title": "Improvement Opportunity",
        "summary_template": "This bullet could be strengthened with {suggestion}.",
        "detail": "The current wording may not capture attention or demonstrate measurable impact. Adding specifics helps.",
        "why_matters": "Weak bullets can make strong experience seem unremarkable."
    },
    "bullet_no_metrics": {
        "title": "Add Quantifiable Results",
        "summary_template": "No metrics found - consider adding specific numbers.",
        "detail": "Adding numbers like '25% increase' or 'managed team of 8' makes achievements concrete and memorable.",
        "why_matters": "Numbers are memorable and help recruiters understand scale of impact."
    },
    
    # Experience-related explanations  
    "experience_duration_short": {
        "title": "Short Tenure Noted",
        "summary_template": "{duration} at {company} - consider how to present this.",
        "detail": "Short roles aren't necessarily negative but may raise questions. Be prepared to explain the value you added and why you moved on.",
        "why_matters": "Frequent short tenures can be a concern for some employers."
    },
    "experience_gap": {
        "title": "Employment Gap Detected",
        "summary_template": "{gap_length} gap between {end_role} and {start_role}.",
        "detail": "Employment gaps are increasingly common and accepted. Consider briefly addressing significant gaps in your summary or cover letter.",
        "why_matters": "Unexplained gaps may lead to assumptions. Brief context helps."
    },
    
    # General match explanations
    "overall_match_excellent": {
        "title": "Excellent Match",
        "summary_template": "Your profile is a strong fit for this role.",
        "detail": "Skills, experience level, and background align well with the job requirements. Your application should be competitive.",
        "why_matters": "Strong matches are more likely to progress to interviews."
    },
    "overall_match_good": {
        "title": "Good Match with Opportunities",
        "summary_template": "Solid fit with some areas to address.",
        "detail": "Your core qualifications match, but some optimizations could strengthen your application.",
        "why_matters": "Small improvements can make the difference in competitive pools."
    },
    "overall_match_developing": {
        "title": "Growing Match",
        "summary_template": "Some experience gaps but potential for growth.",
        "detail": "Your resume shows some relevant qualifications, but key requirements may be missing or unclear. Consider skill development or clearer positioning.",
        "why_matters": "Understanding gaps helps you decide if pursuing this role makes sense."
    }
}


class ExplainabilityEngine:
    """
    Generates human-readable explanations for all analysis outputs.
    
    Core principle: Every signal, score, or recommendation must
    be accompanied by an explanation that answers:
    - What did we find?
    - Why does it matter?
    - How confident are we?
    - What should you do?
    """
    
    def __init__(self):
        self.templates = EXPLANATION_TEMPLATES
    
    def create_explanation(
        self,
        template_key: str,
        template_vars: Optional[Dict[str, Any]] = None,
        signal_name: str = "",
        signal_value: Any = None,
        signal_strength: SignalStrength = SignalStrength.MODERATE,
        confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
        confidence_reason: Optional[str] = None,
        is_actionable: bool = False,
        action_text: Optional[str] = None,
        action_priority: ActionPriority = ActionPriority.MEDIUM
    ) -> Explanation:
        """
        Create an explanation from a template.
        
        Args:
            template_key: Key to look up in EXPLANATION_TEMPLATES
            template_vars: Variables to substitute in template
            signal_name: Machine-readable signal identifier
            signal_value: The raw value/score being explained
            signal_strength: How strong this signal is
            confidence: How confident we are in this analysis
            confidence_reason: Why we have this confidence level
            is_actionable: Whether user can/should take action
            action_text: Specific action recommendation
            action_priority: How urgent the action is
            
        Returns:
            Fully populated Explanation object
        """
        template = self.templates.get(template_key, {})
        vars_dict = template_vars or {}
        
        # Apply template variables
        title = template.get("title", template_key)
        summary = template.get("summary_template", "").format(**vars_dict)
        detail = template.get("detail", "")
        why_matters = template.get("why_matters", "")
        
        # Append why_matters to detail if available
        if why_matters:
            detail = f"{detail}\n\n**Why this matters:** {why_matters}"
        
        return Explanation(
            explanation_type=ExplanationType.WHAT_WE_FOUND,
            title=title,
            summary=summary,
            detail=detail,
            signal_name=signal_name,
            signal_value=signal_value,
            signal_strength=signal_strength,
            confidence=confidence,
            confidence_reason=confidence_reason,
            is_actionable=is_actionable,
            action_text=action_text,
            action_priority=action_priority
        )
    
    def explain_skill_match(
        self,
        matched_skills: List[str],
        missing_skills: List[str],
        total_required: int
    ) -> List[Explanation]:
        """Generate explanations for skill matching results"""
        explanations = []
        
        match_pct = int((len(matched_skills) / total_required * 100)) if total_required > 0 else 0
        
        # Overall match explanation
        if match_pct >= 80:
            template_key = "skill_match_strong"
            signal_strength = SignalStrength.STRONG
        else:
            template_key = "skill_match_partial"
            signal_strength = SignalStrength.MODERATE
        
        explanations.append(self.create_explanation(
            template_key=template_key,
            template_vars={"match_pct": match_pct},
            signal_name="skill_match_percentage",
            signal_value=match_pct,
            signal_strength=signal_strength,
            confidence=ConfidenceLevel.HIGH,
            is_actionable=match_pct < 80,
            action_text="Review missing skills and add any you possess" if match_pct < 80 else None,
            action_priority=ActionPriority.HIGH if match_pct < 60 else ActionPriority.MEDIUM
        ))
        
        # Individual skill gap explanations (top 3)
        for skill in missing_skills[:3]:
            explanations.append(self.create_explanation(
                template_key="skill_gap_identified",
                template_vars={"skill_name": skill},
                signal_name="skill_gap",
                signal_value=skill,
                signal_strength=SignalStrength.MODERATE,
                confidence=ConfidenceLevel.HIGH,
                is_actionable=True,
                action_text=f"Add '{skill}' to your skills section if you have experience with it",
                action_priority=ActionPriority.MEDIUM
            ))
        
        return explanations
    
    def explain_bullet_strength(
        self,
        bullet_text: str,
        has_action_verb: bool,
        has_metrics: bool,
        has_result: bool,
        suggested_improvement: Optional[str] = None
    ) -> Explanation:
        """Generate explanation for a bullet point analysis"""
        
        # Determine bullet strength
        strength_score = sum([has_action_verb, has_metrics, has_result])
        
        if strength_score == 3:
            return self.create_explanation(
                template_key="bullet_strength_strong",
                template_vars={"impact_type": "measurable results"},
                signal_name="bullet_strength",
                signal_value="strong",
                signal_strength=SignalStrength.STRONG,
                confidence=ConfidenceLevel.HIGH,
                is_actionable=False
            )
        
        # Determine what's missing
        missing = []
        if not has_action_verb:
            missing.append("action verb")
        if not has_metrics:
            missing.append("specific metrics")
        if not has_result:
            missing.append("clear outcome")
        
        suggestion = f"adding {' and '.join(missing)}" if missing else "more specifics"
        
        return self.create_explanation(
            template_key="bullet_strength_weak",
            template_vars={"suggestion": suggestion},
            signal_name="bullet_strength",
            signal_value="needs_improvement",
            signal_strength=SignalStrength.WEAK,
            confidence=ConfidenceLevel.HIGH,
            is_actionable=True,
            action_text=suggested_improvement or f"Consider {suggestion}",
            action_priority=ActionPriority.MEDIUM
        )
    
    def explain_overall_match(
        self,
        skill_match_pct: float,
        experience_years_match: bool,
        education_match: bool,
        keyword_density: float
    ) -> Explanation:
        """Generate explanation for overall job match"""
        
        # Calculate overall match level
        factors_met = sum([
            skill_match_pct >= 70,
            experience_years_match,
            education_match,
            keyword_density >= 0.6
        ])
        
        if factors_met >= 3:
            template_key = "overall_match_excellent"
            strength = SignalStrength.STRONG
            confidence = ConfidenceLevel.HIGH
        elif factors_met >= 2:
            template_key = "overall_match_good"
            strength = SignalStrength.MODERATE
            confidence = ConfidenceLevel.MEDIUM
        else:
            template_key = "overall_match_developing"
            strength = SignalStrength.WEAK
            confidence = ConfidenceLevel.MEDIUM
        
        return self.create_explanation(
            template_key=template_key,
            signal_name="overall_match",
            signal_value={"factors_met": factors_met, "skill_match": skill_match_pct},
            signal_strength=strength,
            confidence=confidence,
            confidence_reason="Based on analysis of skills, experience, and keyword alignment.",
            is_actionable=factors_met < 3,
            action_text="See detailed recommendations below" if factors_met < 3 else None,
            action_priority=ActionPriority.HIGH if factors_met < 2 else ActionPriority.MEDIUM
        )
    
    def explain_confidence(
        self,
        data_quality: str,  # "high", "medium", "low"
        analysis_type: str,
        factors: List[str]
    ) -> str:
        """
        Generate human-readable confidence explanation.
        
        Args:
            data_quality: How complete/reliable the input data is
            analysis_type: Type of analysis performed
            factors: Factors affecting confidence
            
        Returns:
            Human-readable confidence explanation
        """
        base_explanations = {
            "high": "We're confident in this analysis",
            "medium": "This analysis is based on available information",
            "low": "Limited data affects the confidence of this analysis"
        }
        
        explanation = base_explanations.get(data_quality, base_explanations["medium"])
        
        if factors:
            explanation += f" ({', '.join(factors)})"
        
        return explanation
    
    def explain_ai_limitation(
        self,
        analysis_type: str,
        what_ai_did: str,
        what_human_should_verify: str
    ) -> Explanation:
        """
        Generate explanation about AI analysis limitations.
        
        Ensures transparency about what AI can and cannot reliably assess.
        """
        return Explanation(
            explanation_type=ExplanationType.CONFIDENCE_LEVEL,
            title="Analysis Transparency",
            summary=f"This {analysis_type} analysis was assisted by AI.",
            detail=f"**What we analyzed:** {what_ai_did}\n\n**What you should verify:** {what_human_should_verify}",
            signal_name="ai_transparency",
            signal_strength=SignalStrength.MODERATE,
            confidence=ConfidenceLevel.MEDIUM,
            confidence_reason="AI analysis should be reviewed with human judgment.",
            is_actionable=False
        )
    
    def format_for_frontend(
        self,
        explanations: List[Explanation]
    ) -> List[Dict[str, Any]]:
        """
        Format explanations for frontend consumption.
        
        Returns simplified structure optimized for UI rendering.
        """
        formatted = []
        
        for exp in explanations:
            formatted.append({
                "type": exp.explanation_type.value,
                "title": exp.title,
                "summary": exp.summary,
                "detail": exp.detail,
                "signal": {
                    "name": exp.signal_name,
                    "value": exp.signal_value,
                    "strength": exp.signal_strength.value if exp.signal_strength else None
                },
                "confidence": {
                    "level": exp.confidence.value if exp.confidence else "medium",
                    "reason": exp.confidence_reason
                },
                "action": {
                    "needed": exp.is_actionable,
                    "text": exp.action_text,
                    "priority": exp.action_priority.value if exp.action_priority else None
                } if exp.is_actionable else None
            })
        
        return formatted
    
    def create_custom_explanation(
        self,
        explanation_type: ExplanationType,
        title: str,
        summary: str,
        detail: str,
        signal_name: str,
        signal_value: Any,
        signal_strength: SignalStrength,
        confidence: ConfidenceLevel,
        confidence_reason: Optional[str] = None,
        is_actionable: bool = False,
        action_text: Optional[str] = None,
        action_priority: Optional[ActionPriority] = None
    ) -> Explanation:
        """
        Create a custom explanation without using templates.
        
        Use when the predefined templates don't fit.
        """
        return Explanation(
            explanation_type=explanation_type,
            title=title,
            summary=summary,
            detail=detail,
            signal_name=signal_name,
            signal_value=signal_value,
            signal_strength=signal_strength,
            confidence=confidence,
            confidence_reason=confidence_reason,
            is_actionable=is_actionable,
            action_text=action_text,
            action_priority=action_priority
        )


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def explain_analysis_result(result: Dict[str, Any]) -> List[Explanation]:
    """
    Utility function to add explanations to any analysis result.
    
    Wraps the ExplainabilityEngine for simple use cases.
    """
    engine = ExplainabilityEngine()
    explanations = []
    
    # Auto-detect result type and generate appropriate explanations
    if "skill_match" in result:
        explanations.extend(engine.explain_skill_match(
            matched_skills=result.get("matched_skills", []),
            missing_skills=result.get("missing_skills", []),
            total_required=result.get("total_required", 0)
        ))
    
    if "overall_match" in result:
        explanations.append(engine.explain_overall_match(
            skill_match_pct=result.get("skill_match_pct", 0),
            experience_years_match=result.get("experience_match", False),
            education_match=result.get("education_match", False),
            keyword_density=result.get("keyword_density", 0)
        ))
    
    return explanations
