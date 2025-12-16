"""
Layer 2 — Constrained AI Interpretation

This layer translates Layer 1 signals into human-readable explanations.

CONSTRAINTS:
- MUST reference Layer 1 signals
- CANNOT contradict any signal
- CANNOT add new facts not in signals
- CAN rephrase for clarity
- CAN add empathy/tone
- CAN combine related signals

Output is strictly bounded by Layer 1 facts.
"""
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json

from .layer1_signals import Signal, SignalType, SignalSeverity


class InterpretationTone(str, Enum):
    """Tone for interpretations"""
    SUPPORTIVE = "supportive"     # Encouraging, constructive
    DIRECT = "direct"             # Clear, factual
    CAUTIOUS = "cautious"         # When uncertain
    CELEBRATORY = "celebratory"   # For positive signals


@dataclass
class Interpretation:
    """
    A human-readable interpretation of one or more signals.
    
    Strictly bounded by the source signals.
    """
    # The signals being interpreted
    source_signals: List[Signal]
    
    # Human-readable explanation
    explanation: str
    
    # What action user can take
    suggested_action: Optional[str] = None
    
    # Tone used
    tone: InterpretationTone = InterpretationTone.SUPPORTIVE
    
    # Why this matters (bounded by signals)
    why_it_matters: Optional[str] = None
    
    # Confidence that interpretation is accurate
    confidence: float = 1.0  # Layer 2 should be high confidence
    
    # Category for grouping
    category: str = "general"
    
    # Priority for display ordering
    priority: int = 0
    
    # Audit fields
    interpretation_id: str = ""
    generated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_signal_ids": [s.signal_hash for s in self.source_signals],
            "explanation": self.explanation,
            "suggested_action": self.suggested_action,
            "tone": self.tone.value,
            "why_it_matters": self.why_it_matters,
            "confidence": self.confidence,
            "category": self.category,
            "priority": self.priority,
            "generated_at": self.generated_at.isoformat()
        }


# =============================================================================
# INTERPRETATION TEMPLATES (Deterministic)
# =============================================================================

INTERPRETATION_TEMPLATES = {
    # Missing sections
    (SignalType.SECTION_MISSING, SignalSeverity.CRITICAL): {
        "template": "Your resume is missing {value}, which is essential for ATS systems and recruiters.",
        "action": "Add a {value} section to ensure your resume can be properly parsed.",
        "why": "Without {value}, recruiters may not be able to contact you or understand your background.",
        "tone": InterpretationTone.DIRECT,
        "priority": 100
    },
    
    (SignalType.SECTION_MISSING, SignalSeverity.MEDIUM): {
        "template": "Adding a {value} section could strengthen your resume.",
        "action": "Consider adding a brief {value} section.",
        "why": "Many recruiters look for this section to quickly understand your profile.",
        "tone": InterpretationTone.SUPPORTIVE,
        "priority": 50
    },
    
    # Email issues
    (SignalType.EMAIL_MISSING, SignalSeverity.CRITICAL): {
        "template": "We couldn't find an email address on your resume.",
        "action": "Add your email address prominently in the contact section.",
        "why": "Recruiters need a way to reach you. Without an email, your application may be skipped.",
        "tone": InterpretationTone.DIRECT,
        "priority": 100
    },
    
    # Bullet quality
    (SignalType.BULLET_HAS_METRIC, SignalSeverity.HIGH): {
        "template": "Only {context[percentage]:.0f}% of your bullet points include quantifiable results.",
        "action": "Add specific numbers, percentages, or metrics to demonstrate your impact.",
        "why": "Metrics help recruiters understand the scale and impact of your work. They're memorable and credible.",
        "tone": InterpretationTone.SUPPORTIVE,
        "priority": 80
    },
    
    (SignalType.BULLET_HAS_ACTION_VERB, SignalSeverity.LOW): {
        "template": "This bullet doesn't start with a strong action verb.",
        "action": "Start with verbs like 'Led', 'Built', 'Improved', or 'Delivered'.",
        "why": "Action verbs make your accomplishments more dynamic and demonstrate leadership.",
        "tone": InterpretationTone.SUPPORTIVE,
        "priority": 30
    },
    
    # Skills
    (SignalType.SKILL_MISSING, SignalSeverity.HIGH): {
        "template": "The required skill '{value}' was not found on your resume.",
        "action": "If you have this skill, add it. If not, consider if this role is a good match.",
        "why": "This is listed as a requirement. Missing required skills may disqualify your application.",
        "tone": InterpretationTone.DIRECT,
        "priority": 70
    },
    
    (SignalType.SKILL_MATCH, SignalSeverity.INFO): {
        "template": "Great! Your '{value}' skill matches what the employer is looking for.",
        "action": None,
        "why": "This alignment increases your chances of passing initial screening.",
        "tone": InterpretationTone.CELEBRATORY,
        "priority": 20
    },
    
    # Format issues
    (SignalType.FORMAT_ISSUE, SignalSeverity.MEDIUM): {
        "template": "We detected formatting that may cause issues with ATS systems.",
        "action": "Consider using a simpler format without tables, columns, or special formatting.",
        "why": "Many ATS systems struggle to parse complex formatting, which can cause your information to be scrambled.",
        "tone": InterpretationTone.CAUTIOUS,
        "priority": 60
    },
    
    # Job hopping
    (SignalType.JOB_HOPPING, SignalSeverity.MEDIUM): {
        "template": "Your resume shows {value} positions with short tenure.",
        "action": "Be prepared to explain these transitions positively in interviews.",
        "why": "Some employers may question frequent job changes. Have clear, positive explanations ready.",
        "tone": InterpretationTone.CAUTIOUS,
        "priority": 40
    }
}


class InterpretationEngine:
    """
    Layer 2: Constrained AI Interpretation Engine
    
    Translates signals into human-readable explanations.
    Strictly bounded by Layer 1 outputs.
    """
    
    def __init__(self, ai_orchestrator=None):
        """
        Args:
            ai_orchestrator: Optional AI orchestrator for enhanced interpretations.
                            If None, uses pure template-based interpretation.
        """
        self.ai_orchestrator = ai_orchestrator
        self.templates = INTERPRETATION_TEMPLATES
    
    def interpret_signals(
        self,
        signals: List[Signal],
        use_ai: bool = False,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Interpretation]:
        """
        Generate interpretations for signals.
        
        Args:
            signals: Layer 1 signals to interpret
            use_ai: Whether to use AI for enhanced phrasing
            context: Additional context for interpretation
            
        Returns:
            List of interpretations, sorted by priority
        """
        interpretations = []
        
        # Group signals for combined interpretations
        grouped = self._group_related_signals(signals)
        
        for signal_group in grouped:
            if len(signal_group) == 1:
                # Single signal interpretation
                interp = self._interpret_single(signal_group[0], use_ai)
            else:
                # Combined interpretation
                interp = self._interpret_combined(signal_group, use_ai)
            
            if interp:
                interpretations.append(interp)
        
        # Sort by priority (higher first)
        interpretations.sort(key=lambda x: x.priority, reverse=True)
        
        return interpretations
    
    def _group_related_signals(self, signals: List[Signal]) -> List[List[Signal]]:
        """Group related signals for combined interpretation"""
        groups = []
        used = set()
        
        # Group skill matches together
        skill_matches = [s for s in signals if s.signal_type == SignalType.SKILL_MATCH]
        if skill_matches:
            groups.append(skill_matches)
            used.update(s.signal_hash for s in skill_matches)
        
        # Group skill missing together
        skill_missing = [s for s in signals if s.signal_type == SignalType.SKILL_MISSING]
        if skill_missing:
            groups.append(skill_missing)
            used.update(s.signal_hash for s in skill_missing)
        
        # Individual signals
        for signal in signals:
            if signal.signal_hash not in used:
                groups.append([signal])
        
        return groups
    
    def _interpret_single(self, signal: Signal, use_ai: bool) -> Optional[Interpretation]:
        """Interpret a single signal"""
        template_key = (signal.signal_type, signal.severity)
        template = self.templates.get(template_key)
        
        if template:
            # Use template-based interpretation
            explanation = self._render_template(template["template"], signal)
            action = self._render_template(template.get("action", ""), signal) if template.get("action") else None
            why = self._render_template(template.get("why", ""), signal) if template.get("why") else None
            
            return Interpretation(
                source_signals=[signal],
                explanation=explanation,
                suggested_action=action,
                tone=template.get("tone", InterpretationTone.SUPPORTIVE),
                why_it_matters=why,
                confidence=1.0,  # Template-based is deterministic
                category=self._get_category(signal),
                priority=template.get("priority", 0)
            )
        
        # Fallback: basic interpretation
        return Interpretation(
            source_signals=[signal],
            explanation=signal.description,
            tone=InterpretationTone.DIRECT,
            confidence=0.9,
            category=self._get_category(signal),
            priority=self._severity_to_priority(signal.severity)
        )
    
    def _interpret_combined(self, signals: List[Signal], use_ai: bool) -> Optional[Interpretation]:
        """Interpret multiple related signals together"""
        if not signals:
            return None
        
        first = signals[0]
        
        # Skill match summary
        if first.signal_type == SignalType.SKILL_MATCH:
            skills = [s.value for s in signals]
            return Interpretation(
                source_signals=signals,
                explanation=f"Your resume matches {len(skills)} required skills: {', '.join(skills[:5])}{'...' if len(skills) > 5 else ''}",
                tone=InterpretationTone.CELEBRATORY,
                why_it_matters="Strong skill alignment increases your chances of passing ATS screening.",
                confidence=1.0,
                category="skills",
                priority=60
            )
        
        # Skill missing summary
        if first.signal_type == SignalType.SKILL_MISSING:
            skills = [s.value for s in signals]
            return Interpretation(
                source_signals=signals,
                explanation=f"{len(skills)} required skills are missing from your resume: {', '.join(skills[:5])}{'...' if len(skills) > 5 else ''}",
                suggested_action="Add these skills if you have them, or evaluate if this role aligns with your experience.",
                tone=InterpretationTone.DIRECT,
                why_it_matters="Missing required skills may prevent your application from advancing.",
                confidence=1.0,
                category="skills",
                priority=75
            )
        
        # Default: interpret first signal
        return self._interpret_single(first, use_ai)
    
    def _render_template(self, template: str, signal: Signal) -> str:
        """Render a template with signal data"""
        try:
            return template.format(
                value=signal.value,
                context=signal.context,
                source_location=signal.source_location or "resume"
            )
        except (KeyError, IndexError):
            return template
    
    def _get_category(self, signal: Signal) -> str:
        """Determine category for a signal"""
        type_to_category = {
            SignalType.SECTION_PRESENT: "structure",
            SignalType.SECTION_MISSING: "structure",
            SignalType.EMAIL_VALID: "contact",
            SignalType.EMAIL_MISSING: "contact",
            SignalType.PHONE_PRESENT: "contact",
            SignalType.BULLET_COUNT: "content",
            SignalType.BULLET_HAS_METRIC: "content",
            SignalType.BULLET_HAS_ACTION_VERB: "content",
            SignalType.SKILL_COUNT: "skills",
            SignalType.SKILL_MATCH: "skills",
            SignalType.SKILL_MISSING: "skills",
            SignalType.FORMAT_ISSUE: "formatting",
            SignalType.ATS_PARSEABLE: "ats",
            SignalType.ATS_RISK: "ats"
        }
        return type_to_category.get(signal.signal_type, "general")
    
    def _severity_to_priority(self, severity: SignalSeverity) -> int:
        """Convert severity to display priority"""
        return {
            SignalSeverity.CRITICAL: 100,
            SignalSeverity.HIGH: 80,
            SignalSeverity.MEDIUM: 50,
            SignalSeverity.LOW: 20,
            SignalSeverity.INFO: 10
        }.get(severity, 0)
    
    def get_interpretation_summary(
        self,
        interpretations: List[Interpretation]
    ) -> Dict[str, Any]:
        """Generate summary of interpretations"""
        by_category = {}
        by_tone = {}
        
        for interp in interpretations:
            # Group by category
            if interp.category not in by_category:
                by_category[interp.category] = []
            by_category[interp.category].append(interp.to_dict())
            
            # Count by tone
            tone = interp.tone.value
            by_tone[tone] = by_tone.get(tone, 0) + 1
        
        return {
            "total_interpretations": len(interpretations),
            "by_category": by_category,
            "by_tone": by_tone,
            "top_priority": interpretations[0].to_dict() if interpretations else None
        }
