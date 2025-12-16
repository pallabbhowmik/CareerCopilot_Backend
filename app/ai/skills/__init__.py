"""
Atomic AI Skills

Each skill is a single-responsibility AI function with:
- Strict input/output schema
- Confidence score
- Reasoning trace
- Tone constraints
- Version control

Skills are the building blocks of all AI operations.
"""
from typing import Dict, Any, List, Optional, Protocol
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
from datetime import datetime
import hashlib
import json


class SkillCategory(str, Enum):
    """Categories of AI skills"""
    ANALYSIS = "analysis"       # Analyzes content
    GENERATION = "generation"   # Generates new content
    EVALUATION = "evaluation"   # Evaluates quality
    RECOMMENDATION = "recommendation"  # Makes recommendations


class ToneConstraint(str, Enum):
    """Tone constraints for skill outputs"""
    SUPPORTIVE = "supportive"   # Encouraging, helpful
    DIRECT = "direct"           # Clear, no fluff
    CAUTIOUS = "cautious"       # Hedge appropriately
    PROFESSIONAL = "professional"  # Business-like


@dataclass
class SkillInput:
    """Standard input structure for all skills"""
    primary_content: str
    context: Dict[str, Any] = field(default_factory=dict)
    constraints: List[str] = field(default_factory=list)
    tone: ToneConstraint = ToneConstraint.SUPPORTIVE
    max_output_length: int = 500


@dataclass
class SkillOutput:
    """Standard output structure for all skills"""
    # The main output
    result: Any
    
    # Confidence and reasoning
    confidence: float
    reasoning_trace: str
    
    # Metadata
    skill_name: str
    skill_version: str
    execution_time_ms: float
    
    # Traceability
    input_hash: str = ""
    output_hash: str = ""
    
    # For audit
    timestamp: datetime = field(default_factory=datetime.utcnow)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "result": self.result,
            "confidence": self.confidence,
            "reasoning_trace": self.reasoning_trace,
            "skill_name": self.skill_name,
            "skill_version": self.skill_version,
            "execution_time_ms": self.execution_time_ms,
            "warnings": self.warnings,
            "timestamp": self.timestamp.isoformat()
        }


class AISkill(ABC):
    """
    Base class for all atomic AI skills.
    
    Every skill must:
    1. Have a single responsibility
    2. Define strict input/output schemas
    3. Include confidence scoring
    4. Provide reasoning trace
    5. Respect tone constraints
    """
    
    name: str = "base_skill"
    version: str = "1.0.0"
    category: SkillCategory = SkillCategory.ANALYSIS
    
    # Constraints
    requires_ai: bool = True  # Whether this skill requires LLM
    max_input_length: int = 10000
    max_output_length: int = 2000
    
    # Tone defaults
    default_tone: ToneConstraint = ToneConstraint.SUPPORTIVE
    
    def __init__(self, ai_orchestrator=None):
        self.ai_orchestrator = ai_orchestrator
        self.allowed_tones = list(ToneConstraint)
    
    @abstractmethod
    async def execute(self, input_data: SkillInput) -> SkillOutput:
        """Execute the skill"""
        pass
    
    def validate_input(self, input_data: SkillInput) -> List[str]:
        """Validate input data"""
        errors = []
        
        if len(input_data.primary_content) > self.max_input_length:
            errors.append(f"Input exceeds max length of {self.max_input_length}")
        
        if input_data.tone not in self.allowed_tones:
            errors.append(f"Tone {input_data.tone} not allowed for this skill")
        
        return errors
    
    def _hash_input(self, input_data: SkillInput) -> str:
        content = json.dumps({
            "content": input_data.primary_content,
            "context": input_data.context,
            "tone": input_data.tone.value
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _hash_output(self, result: Any) -> str:
        content = json.dumps(result, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
