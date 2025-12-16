"""
Layer 3 — Limited AI Judgment

This layer provides AI-generated suggestions, alternatives, and reasoning.

CONSTRAINTS:
- MUST cite Layer 1/2 signals/interpretations
- CANNOT contradict facts from Layer 1
- CANNOT guarantee outcomes
- MUST express uncertainty appropriately
- MUST be traceable to source signals

This is where LLMs have the most freedom, but still within guardrails.
"""
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
import re

from .layer1_signals import Signal, SignalType, SignalSeverity
from .layer2_interpretation import Interpretation


class JudgmentType(str, Enum):
    """Types of AI judgments"""
    REWRITE_SUGGESTION = "rewrite_suggestion"      # Suggest rewrites
    SKILL_RECOMMENDATION = "skill_recommendation"  # Recommend skills to add
    CAREER_INSIGHT = "career_insight"              # Career advice
    IMPROVEMENT_PRIORITY = "improvement_priority"  # What to fix first
    ALTERNATIVE_FRAMING = "alternative_framing"    # Different ways to phrase
    GAP_ANALYSIS = "gap_analysis"                  # Skill/experience gaps
    STRENGTH_HIGHLIGHT = "strength_highlight"      # What's working well


class ConfidenceReason(str, Enum):
    """Why confidence is at a certain level"""
    SIGNAL_BASED = "signal_based"           # Based on Layer 1 signals
    PATTERN_MATCH = "pattern_match"         # Matched known patterns
    INFERENCE = "inference"                 # AI inference
    UNCERTAIN = "uncertain"                 # Limited data


@dataclass
class JudgmentBoundary:
    """
    Defines what an AI judgment can and cannot do.
    
    These are hard constraints enforced at generation time.
    """
    can_suggest_rewrites: bool = True
    can_recommend_skills: bool = True
    can_give_career_advice: bool = False  # Limited by default
    can_predict_outcomes: bool = False     # NEVER
    can_compare_to_others: bool = False    # Privacy concern
    max_suggestions: int = 5
    required_signal_citation: bool = True


@dataclass
class Judgment:
    """
    An AI-generated judgment with full traceability.
    
    Every judgment must cite its sources and express appropriate uncertainty.
    """
    judgment_type: JudgmentType
    
    # What the AI is suggesting/concluding
    content: str
    
    # Source citations (REQUIRED)
    cited_signals: List[Signal]
    cited_interpretations: List[Interpretation] = field(default_factory=list)
    
    # Confidence and reasoning
    confidence: float = 0.7  # Default moderate confidence
    confidence_reason: ConfidenceReason = ConfidenceReason.INFERENCE
    reasoning_trace: str = ""
    
    # For suggestions: the original and suggested content
    original_content: Optional[str] = None
    suggested_content: Optional[str] = None
    
    # Caveats and limitations
    caveats: List[str] = field(default_factory=list)
    
    # Audit
    judgment_id: str = ""
    model_used: str = ""
    generated_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        # Enforce citation requirement
        if not self.cited_signals and not self.cited_interpretations:
            raise ValueError("Judgments must cite at least one signal or interpretation")
        
        # Auto-add caveats based on type
        if self.judgment_type == JudgmentType.CAREER_INSIGHT:
            if "This is general guidance" not in str(self.caveats):
                self.caveats.append("This is general guidance and may not apply to your specific situation")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "judgment_type": self.judgment_type.value,
            "content": self.content,
            "cited_signal_ids": [s.signal_hash for s in self.cited_signals],
            "confidence": self.confidence,
            "confidence_reason": self.confidence_reason.value,
            "reasoning_trace": self.reasoning_trace,
            "original_content": self.original_content,
            "suggested_content": self.suggested_content,
            "caveats": self.caveats,
            "model_used": self.model_used,
            "generated_at": self.generated_at.isoformat()
        }


# =============================================================================
# JUDGMENT CONSTRAINTS (Hard Rules)
# =============================================================================

# Phrases AI must NEVER use
FORBIDDEN_PHRASES = [
    "guaranteed",
    "will definitely",
    "100%",
    "always get",
    "never fail",
    "promise",
    "certainly will",
    "your resume is perfect",
    "no improvements needed"
]

# Required uncertainty expressions
UNCERTAINTY_PHRASES = [
    "may help",
    "could improve",
    "consider",
    "might strengthen",
    "potentially",
    "in many cases",
    "often works well",
    "recruiters typically"
]

# Signal types that enable specific judgments
JUDGMENT_ENABLERS = {
    JudgmentType.REWRITE_SUGGESTION: [
        SignalType.BULLET_HAS_METRIC,
        SignalType.BULLET_HAS_ACTION_VERB,
        SignalType.BULLET_TOO_LONG,
        SignalType.BULLET_TOO_SHORT
    ],
    JudgmentType.SKILL_RECOMMENDATION: [
        SignalType.SKILL_MISSING,
        SignalType.SKILL_PARTIAL_MATCH,
        SignalType.SKILL_COUNT
    ],
    JudgmentType.GAP_ANALYSIS: [
        SignalType.SKILL_MISSING,
        SignalType.EXPERIENCE_COUNT,
        SignalType.SECTION_MISSING
    ]
}


class JudgmentEngine:
    """
    Layer 3: Limited AI Judgment Engine
    
    Generates suggestions and insights while respecting hard constraints.
    """
    
    def __init__(self, ai_orchestrator=None):
        """
        Args:
            ai_orchestrator: AI orchestrator for LLM calls.
                            If None, uses rule-based judgments only.
        """
        self.ai_orchestrator = ai_orchestrator
        self.boundaries = JudgmentBoundary()
    
    def generate_judgments(
        self,
        signals: List[Signal],
        interpretations: List[Interpretation],
        judgment_types: Optional[List[JudgmentType]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Judgment]:
        """
        Generate AI judgments based on signals and interpretations.
        
        Args:
            signals: Layer 1 signals
            interpretations: Layer 2 interpretations
            judgment_types: Which types of judgments to generate
            context: Additional context (job description, user preferences)
            
        Returns:
            List of judgments with full traceability
        """
        judgments = []
        
        # Default judgment types
        if judgment_types is None:
            judgment_types = [
                JudgmentType.REWRITE_SUGGESTION,
                JudgmentType.IMPROVEMENT_PRIORITY,
                JudgmentType.STRENGTH_HIGHLIGHT
            ]
        
        for jtype in judgment_types:
            # Check if we have enabling signals
            if not self._has_enabling_signals(jtype, signals):
                continue
            
            # Generate judgments of this type
            if jtype == JudgmentType.REWRITE_SUGGESTION:
                judgments.extend(self._generate_rewrites(signals, context))
            elif jtype == JudgmentType.IMPROVEMENT_PRIORITY:
                judgments.append(self._generate_priority(signals, interpretations))
            elif jtype == JudgmentType.STRENGTH_HIGHLIGHT:
                judgments.extend(self._generate_strengths(signals))
            elif jtype == JudgmentType.SKILL_RECOMMENDATION:
                judgments.extend(self._generate_skill_recommendations(signals, context))
        
        # Validate all judgments
        valid_judgments = [j for j in judgments if j and self._validate_judgment(j)]
        
        return valid_judgments
    
    def _has_enabling_signals(self, jtype: JudgmentType, signals: List[Signal]) -> bool:
        """Check if we have signals that enable this judgment type"""
        enablers = JUDGMENT_ENABLERS.get(jtype, [])
        if not enablers:
            return True  # No specific enablers required
        
        signal_types = {s.signal_type for s in signals}
        return bool(signal_types.intersection(enablers))
    
    def _generate_rewrites(
        self,
        signals: List[Signal],
        context: Optional[Dict[str, Any]]
    ) -> List[Judgment]:
        """Generate bullet rewrite suggestions"""
        judgments = []
        
        # Find bullets that need improvement
        weak_bullets = [
            s for s in signals
            if s.signal_type == SignalType.BULLET_HAS_ACTION_VERB 
            and s.value == False
        ]
        
        for signal in weak_bullets[:self.boundaries.max_suggestions]:
            original = signal.context.get("text", "")
            if not original:
                continue
            
            # Generate suggestion (rule-based or AI)
            suggested = self._suggest_rewrite(original, signal)
            
            judgments.append(Judgment(
                judgment_type=JudgmentType.REWRITE_SUGGESTION,
                content=f"Consider strengthening this bullet point",
                cited_signals=[signal],
                confidence=0.75,
                confidence_reason=ConfidenceReason.PATTERN_MATCH,
                reasoning_trace=f"Bullet lacks action verb at start. First word: '{signal.context.get('first_word', '')}'",
                original_content=original,
                suggested_content=suggested,
                caveats=["This is a suggestion - adjust to match your actual experience"]
            ))
        
        return judgments
    
    def _suggest_rewrite(self, original: str, signal: Signal) -> str:
        """Suggest a rewritten bullet (rule-based)"""
        # If AI orchestrator available, use it
        if self.ai_orchestrator:
            return self._ai_suggest_rewrite(original, signal)
        
        # Rule-based rewrite
        first_word = signal.context.get("first_word", "")
        
        # Simple transformation: add action verb prefix
        action_verbs = ["Led", "Developed", "Implemented", "Managed", "Created"]
        
        # Pick verb based on content hints
        if "team" in original.lower():
            prefix = "Led"
        elif "code" in original.lower() or "software" in original.lower():
            prefix = "Developed"
        elif "project" in original.lower():
            prefix = "Managed"
        else:
            prefix = "Delivered"
        
        # Reconstruct bullet
        if first_word and original.startswith(first_word):
            return f"{prefix} {original[len(first_word):].strip()}"
        
        return f"{prefix} {original}"
    
    def _ai_suggest_rewrite(self, original: str, signal: Signal) -> str:
        """Use AI to suggest rewrite (with constraints)"""
        # This would call the AI orchestrator with strict prompt
        # For now, return rule-based
        return self._suggest_rewrite(original, signal)
    
    def _generate_priority(
        self,
        signals: List[Signal],
        interpretations: List[Interpretation]
    ) -> Judgment:
        """Generate improvement priority recommendation"""
        # Find highest severity signals
        critical = [s for s in signals if s.severity == SignalSeverity.CRITICAL]
        high = [s for s in signals if s.severity == SignalSeverity.HIGH]
        
        if critical:
            top_signal = critical[0]
            content = f"Priority: Address critical issues first - {top_signal.description}"
            confidence = 0.95
        elif high:
            top_signal = high[0]
            content = f"Priority: Focus on high-impact improvements - {top_signal.description}"
            confidence = 0.85
        else:
            top_signal = signals[0] if signals else None
            content = "Your resume is in good shape. Consider fine-tuning the suggested improvements."
            confidence = 0.7
        
        return Judgment(
            judgment_type=JudgmentType.IMPROVEMENT_PRIORITY,
            content=content,
            cited_signals=[top_signal] if top_signal else [],
            cited_interpretations=interpretations[:1],
            confidence=confidence,
            confidence_reason=ConfidenceReason.SIGNAL_BASED,
            reasoning_trace=f"Prioritized based on signal severity. Critical: {len(critical)}, High: {len(high)}",
            caveats=["Priority may vary based on your target role and timeline"]
        )
    
    def _generate_strengths(self, signals: List[Signal]) -> List[Judgment]:
        """Generate highlights of what's working well"""
        judgments = []
        
        # Find positive signals
        positive_types = [
            SignalType.SKILL_MATCH,
            SignalType.SECTION_PRESENT,
            SignalType.EMAIL_VALID
        ]
        
        positive_signals = [s for s in signals if s.signal_type in positive_types]
        
        # Group skill matches
        skill_matches = [s for s in positive_signals if s.signal_type == SignalType.SKILL_MATCH]
        if skill_matches:
            judgments.append(Judgment(
                judgment_type=JudgmentType.STRENGTH_HIGHLIGHT,
                content=f"Strong skill alignment: {len(skill_matches)} of your skills match the requirements",
                cited_signals=skill_matches,
                confidence=0.9,
                confidence_reason=ConfidenceReason.SIGNAL_BASED,
                reasoning_trace="Direct skill matching between resume and job requirements"
            ))
        
        return judgments
    
    def _generate_skill_recommendations(
        self,
        signals: List[Signal],
        context: Optional[Dict[str, Any]]
    ) -> List[Judgment]:
        """Generate skill acquisition recommendations"""
        judgments = []
        
        missing_skills = [s for s in signals if s.signal_type == SignalType.SKILL_MISSING]
        
        if missing_skills:
            skills = [s.value for s in missing_skills[:5]]
            
            judgments.append(Judgment(
                judgment_type=JudgmentType.SKILL_RECOMMENDATION,
                content=f"Consider developing these skills if relevant to your career goals: {', '.join(skills)}",
                cited_signals=missing_skills[:5],
                confidence=0.7,
                confidence_reason=ConfidenceReason.INFERENCE,
                reasoning_trace="Skills identified as missing from job requirements",
                caveats=[
                    "Only pursue skills aligned with your career direction",
                    "Consider transferable skills you may have under different names"
                ]
            ))
        
        return judgments
    
    def _validate_judgment(self, judgment: Judgment) -> bool:
        """Validate that judgment respects constraints"""
        content_lower = judgment.content.lower()
        
        # Check for forbidden phrases
        for phrase in FORBIDDEN_PHRASES:
            if phrase in content_lower:
                return False
        
        # Ensure uncertainty is expressed for low confidence
        if judgment.confidence < 0.8:
            has_uncertainty = any(
                phrase in content_lower
                for phrase in UNCERTAINTY_PHRASES
            )
            # Allow if confidence reason is signal-based
            if not has_uncertainty and judgment.confidence_reason != ConfidenceReason.SIGNAL_BASED:
                # Modify content to add uncertainty
                judgment.content = f"This may help: {judgment.content}"
        
        # Ensure citations exist
        if not judgment.cited_signals and not judgment.cited_interpretations:
            return False
        
        return True
    
    def get_judgment_summary(self, judgments: List[Judgment]) -> Dict[str, Any]:
        """Generate summary of judgments"""
        by_type = {}
        avg_confidence = 0
        
        for j in judgments:
            jtype = j.judgment_type.value
            if jtype not in by_type:
                by_type[jtype] = []
            by_type[jtype].append(j.to_dict())
            avg_confidence += j.confidence
        
        return {
            "total_judgments": len(judgments),
            "by_type": by_type,
            "average_confidence": avg_confidence / len(judgments) if judgments else 0,
            "has_rewrites": JudgmentType.REWRITE_SUGGESTION.value in by_type,
            "has_priorities": JudgmentType.IMPROVEMENT_PRIORITY.value in by_type
        }
