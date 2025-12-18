"""
AI Orchestrator - The Brain of CareerCopilot AI

This is NOT a wrapper around OpenAI.
This is a SAFETY-FIRST, EXPLANATION-MANDATORY, OUTCOME-LEARNING system.

Principles:
1. Atomic AI skills (single responsibility)
2. Versioned prompts (Git-tracked)
3. Schema validation (strict input/output)
4. Confidence scores (honest uncertainty)
5. Explanations mandatory (no magic black boxes)
6. Safety guardrails (tone, content, advice)
7. Outcome tracking (learn from results)
8. Instant rollback (bad prompts die fast)

"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import hashlib
from pydantic import BaseModel, Field


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CORE TYPES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ConfidenceLevel(str, Enum):
    """How sure are we about this AI output?"""
    HIGH = "high"          # 90%+ - Strong signal
    MEDIUM = "medium"      # 70-90% - Good signal
    LOW = "low"           # 50-70% - Weak signal  
    UNCERTAIN = "uncertain" # <50% - Don't trust this


class ToneSafety(str, Enum):
    """Is the tone appropriate for a career advisor?"""
    SAFE = "safe"          # Calm, professional, reassuring
    WARNING = "warning"    # Slightly pushy or anxious
    UNSAFE = "unsafe"      # Hype, guarantees, blame


class AdviceSafety(str, Enum):
    """Is the advice responsible?"""
    SAFE = "safe"          # Evidence-based, honest
    CAUTION = "caution"    # Borderline, needs review
    UNSAFE = "unsafe"      # Makes guarantees, overpromises


@dataclass
class SkillResult:
    """Standard return type for all AI skills"""
    
    # Core output
    output: Dict[str, Any]
    
    # Mandatory explanation
    explanation: str
    
    # Confidence
    confidence: ConfidenceLevel
    confidence_score: float  # 0.0 to 1.0
    
    # Safety checks
    tone_safety: ToneSafety
    advice_safety: AdviceSafety
    
    # Metadata
    skill_name: str
    prompt_version: str
    execution_time_ms: float
    tokens_used: int
    
    # Tracking
    skill_execution_id: str
    timestamp: datetime
    
    # Optional context
    reasoning: Optional[str] = None
    alternatives: Optional[List[Dict]] = None
    warnings: Optional[List[str]] = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ATOMIC AI SKILL INTERFACE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class AISkill(ABC):
    """
    Base class for all atomic AI skills.
    
    Each skill:
    - Has single responsibility
    - Validates input schema
    - Returns structured output
    - Provides explanation
    - Tracks confidence
    - Checks safety
    """
    
    def __init__(self, prompt_registry: 'PromptRegistry'):
        self.prompt_registry = prompt_registry
        self.skill_name = self.__class__.__name__
    
    @abstractmethod
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input matches expected schema"""
        pass
    
    @abstractmethod
    def execute(self, input_data: Dict[str, Any]) -> SkillResult:
        """Execute the skill and return structured result"""
        pass
    
    @abstractmethod
    def get_prompt_version(self) -> str:
        """Return current prompt version (e.g., 'v1.2.3')"""
        pass
    
    def _check_tone_safety(self, text: str) -> ToneSafety:
        """
        Validate tone is calm, not anxious or hyped.
        
        UNSAFE patterns:
        - Guarantees: "You WILL get hired"
        - Alarm: "This is TERRIBLE"
        - Pressure: "You MUST do this NOW"
        - Hype: "AMAZING opportunity"
        
        SAFE patterns:
        - Calm: "This could help"
        - Honest: "Based on what we see"
        - Encouraging: "You're on the right track"
        """
        unsafe_patterns = [
            "will get",
            "guaranteed",
            "must do this",
            "terrible",
            "awful",
            "urgent",
            "amazing opportunity"
        ]
        
        warning_patterns = [
            "should definitely",
            "highly recommend",
            "don't waste time"
        ]
        
        text_lower = text.lower()
        
        if any(pattern in text_lower for pattern in unsafe_patterns):
            return ToneSafety.UNSAFE
        
        if any(pattern in text_lower for pattern in warning_patterns):
            return ToneSafety.WARNING
        
        return ToneSafety.SAFE
    
    def _check_advice_safety(self, advice: str) -> AdviceSafety:
        """
        Validate advice doesn't make promises we can't keep.
        
        UNSAFE:
        - "This will get you the job"
        - "100% ATS compatible"
        - "Recruiters will love this"
        
        SAFE:
        - "This aligns with common practices"
        - "Based on resume trends we see"
        - "This might help your chances"
        """
        unsafe_patterns = [
            "will get you",
            "100%",
            "recruiters will love",
            "guaranteed to",
            "definitely pass"
        ]
        
        caution_patterns = [
            "likely to",
            "should work",
            "probably will"
        ]
        
        advice_lower = advice.lower()
        
        if any(pattern in advice_lower for pattern in unsafe_patterns):
            return AdviceSafety.UNSAFE
        
        if any(pattern in advice_lower for pattern in caution_patterns):
            return AdviceSafety.CAUTION
        
        return AdviceSafety.SAFE
    
    def _generate_execution_id(self, input_data: Dict) -> str:
        """Generate unique ID for this execution"""
        data_str = json.dumps(input_data, sort_keys=True)
        timestamp = datetime.utcnow().isoformat()
        combined = f"{self.skill_name}:{data_str}:{timestamp}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROMPT REGISTRY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class PromptVersion(BaseModel):
    """Versioned prompt with metadata"""
    version: str  # Semantic versioning: v1.2.3
    prompt_template: str
    system_message: str
    temperature: float = 0.7
    max_tokens: int = 1000
    
    # Safety
    requires_explanation: bool = True
    requires_confidence: bool = True
    
    # Metadata
    created_at: datetime
    created_by: str
    change_notes: str
    
    # Performance
    avg_execution_time_ms: Optional[float] = None
    avg_tokens_used: Optional[int] = None
    success_rate: Optional[float] = None
    
    # Quality
    user_satisfaction: Optional[float] = None
    outcome_correlation: Optional[float] = None


class PromptRegistry:
    """
    Version-controlled prompt storage.
    
    All prompts are:
    - Git-tracked (prompts/ folder)
    - Versioned (semantic versioning)
    - Testable (frozen test cases)
    - Rollbackable (instant revert)
    """
    
    def __init__(self, prompts_dir: str = "app/ai/prompts"):
        self.prompts_dir = prompts_dir
        self._cache: Dict[str, Dict[str, PromptVersion]] = {}
    
    def get_prompt(self, skill_name: str, version: str = "latest") -> PromptVersion:
        """
        Load prompt for a skill.
        
        Args:
            skill_name: Name of the AI skill
            version: Semantic version or 'latest'
        
        Returns:
            PromptVersion with template and metadata
        """
        # Check cache
        if skill_name in self._cache and version in self._cache[skill_name]:
            return self._cache[skill_name][version]
        
        # Load from file system
        # In production: Load from Git-tracked JSON files
        # For now: Return mock
        prompt = PromptVersion(
            version=version,
            prompt_template="",
            system_message="",
            created_at=datetime.utcnow(),
            created_by="system",
            change_notes="Initial version"
        )
        
        # Cache it
        if skill_name not in self._cache:
            self._cache[skill_name] = {}
        self._cache[skill_name][version] = prompt
        
        return prompt
    
    def register_prompt(self, skill_name: str, prompt: PromptVersion):
        """Register a new prompt version"""
        # In production: Write to Git-tracked file
        # Update cache
        if skill_name not in self._cache:
            self._cache[skill_name] = {}
        self._cache[skill_name][prompt.version] = prompt
    
    def list_versions(self, skill_name: str) -> List[str]:
        """List all versions for a skill"""
        return list(self._cache.get(skill_name, {}).keys())


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AI ORCHESTRATOR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class AIOrchestrator:
    """
    Coordinates all AI skills.
    
    Responsibilities:
    - Route requests to skills
    - Validate safety
    - Track execution
    - Cache results
    - Monitor quality
    """
    
    def __init__(
        self,
        prompt_registry: PromptRegistry,
        llm_client: Any,  # OpenAI client
    ):
        self.prompt_registry = prompt_registry
        self.llm_client = llm_client
        self.skills: Dict[str, AISkill] = {}
    
    def register_skill(self, skill: AISkill):
        """Register an AI skill"""
        self.skills[skill.skill_name] = skill
    
    async def execute_skill(
        self,
        skill_name: str,
        input_data: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> SkillResult:
        """
        Execute an AI skill with full safety checks.
        
        Flow:
        1. Validate skill exists
        2. Validate input schema
        3. Execute skill
        4. Check tone safety
        5. Check advice safety
        6. Track execution
        7. Return result
        """
        # Get skill
        if skill_name not in self.skills:
            raise ValueError(f"Unknown skill: {skill_name}")
        
        skill = self.skills[skill_name]
        
        # Validate input
        if not skill.validate_input(input_data):
            raise ValueError(f"Invalid input for skill: {skill_name}")
        
        # Execute
        result = skill.execute(input_data)
        
        # Safety checks
        if result.tone_safety == ToneSafety.UNSAFE:
            raise ValueError(f"Unsafe tone detected in {skill_name}")
        
        if result.advice_safety == AdviceSafety.UNSAFE:
            raise ValueError(f"Unsafe advice detected in {skill_name}")
        
        # Track execution (for outcome intelligence)
        await self._track_execution(result, user_id)
        
        return result
    
    async def _track_execution(
        self,
        result: SkillResult,
        user_id: Optional[str]
    ):
        """Track execution for quality monitoring"""
        # In production: Store in database
        # - skill_execution_id
        # - skill_name
        # - prompt_version
        # - execution_time_ms
        # - tokens_used
        # - confidence_score
        # - user_id (for outcome correlation)
        pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EXAMPLE: BULLET IMPROVEMENT SKILL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class BulletImprovementSkill(AISkill):
    """
    Improve a resume bullet point.
    
    Input:
    - original_bullet: str
    - job_context: Optional[str]
    
    Output:
    - improved_bullet: str
    - explanation: str (WHY this is better)
    - confidence: float
    - changes: List[str] (what changed)
    """
    
    def get_prompt_version(self) -> str:
        return "v1.0.0"
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        required_keys = ["original_bullet"]
        return all(key in input_data for key in required_keys)
    
    def execute(self, input_data: Dict[str, Any]) -> SkillResult:
        start_time = datetime.utcnow()
        
        original = input_data["original_bullet"]
        context = input_data.get("job_context", "")
        
        # Load prompt
        prompt = self.prompt_registry.get_prompt(
            self.skill_name,
            self.get_prompt_version()
        )
        
        # Call LLM (simplified - real implementation uses OpenAI)
        # improved, explanation, confidence = self._call_llm(original, context, prompt)
        
        # Mock result for now
        improved = "Led development of customer-facing dashboard, increasing user engagement by 40% (10,000+ active users)"
        explanation = "Added quantifiable impact metric (40% increase) and clarified scope (10,000+ users). Used action verb 'Led' to show ownership."
        confidence_score = 0.85
        
        # Check safety
        tone_safety = self._check_tone_safety(explanation)
        advice_safety = self._check_advice_safety(explanation)
        
        end_time = datetime.utcnow()
        execution_time = (end_time - start_time).total_seconds() * 1000
        
        return SkillResult(
            output={
                "improved_bullet": improved,
                "changes": [
                    "Added quantifiable metric (40% increase)",
                    "Clarified user scale (10,000+ users)",
                    "Strengthened action verb (Led)",
                ]
            },
            explanation=explanation,
            confidence=ConfidenceLevel.HIGH if confidence_score > 0.8 else ConfidenceLevel.MEDIUM,
            confidence_score=confidence_score,
            tone_safety=tone_safety,
            advice_safety=advice_safety,
            skill_name=self.skill_name,
            prompt_version=self.get_prompt_version(),
            execution_time_ms=execution_time,
            tokens_used=150,  # Mock
            skill_execution_id=self._generate_execution_id(input_data),
            timestamp=end_time
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# USAGE EXAMPLE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def example_usage():
    """How to use the AI Orchestrator"""
    
    # Setup
    prompt_registry = PromptRegistry()
    llm_client = None  # OpenAI client
    orchestrator = AIOrchestrator(prompt_registry, llm_client)
    
    # Register skills
    bullet_skill = BulletImprovementSkill(prompt_registry)
    orchestrator.register_skill(bullet_skill)
    
    # Execute skill
    result = await orchestrator.execute_skill(
        skill_name="BulletImprovementSkill",
        input_data={
            "original_bullet": "Worked on improving system performance",
            "job_context": "Senior Software Engineer role"
        },
        user_id="user_123"
    )
    
    # Check result
    print(f"Confidence: {result.confidence} ({result.confidence_score})")
    print(f"Improved: {result.output['improved_bullet']}")
    print(f"Explanation: {result.explanation}")
    print(f"Tone safety: {result.tone_safety}")
    print(f"Advice safety: {result.advice_safety}")
