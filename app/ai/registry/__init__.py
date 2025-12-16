"""
Prompt & Model Registry

Versioned, immutable prompt and model configuration system.

Features:
- Immutable production prompts
- Version control with audit trail
- Status management (draft, testing, production, deprecated)
- Instant rollback capability
- Model metadata and cost tracking

Usage:
    from app.ai.registry import get_prompt_registry, get_model_registry
    
    prompt_registry = get_prompt_registry()
    prompt = prompt_registry.get_production_prompt("bullet_improver")
    
    model_registry = get_model_registry()
    model = model_registry.select_model(min_tier=ModelTier.STANDARD)
"""
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import hashlib
import json
import copy


class PromptStatus(str, Enum):
    """Prompt lifecycle status"""
    DRAFT = "draft"           # In development
    TESTING = "testing"       # Under evaluation
    PRODUCTION = "production" # Live in production
    DEPRECATED = "deprecated" # Scheduled for removal
    ROLLED_BACK = "rolled_back"  # Previously production, now inactive


class ModelTier(str, Enum):
    """Model capability tiers"""
    ECONOMY = "economy"       # Fastest, cheapest (GPT-3.5, Claude Instant)
    STANDARD = "standard"     # Balanced (GPT-4o-mini)
    PREMIUM = "premium"       # Best quality (GPT-4o, Claude 3.5 Sonnet)
    REASONING = "reasoning"   # Complex reasoning (o1, Claude with extended thinking)


@dataclass
class ModelConfig:
    """Configuration for an AI model"""
    model_id: str
    provider: str  # openai, anthropic, local
    tier: ModelTier
    
    # Capabilities
    max_tokens: int
    context_window: int
    supports_functions: bool = True
    supports_vision: bool = False
    supports_streaming: bool = True
    
    # Cost (per 1M tokens)
    cost_per_1m_input: float = 0.0
    cost_per_1m_output: float = 0.0
    
    # Performance
    avg_latency_ms: float = 500
    reliability_score: float = 0.99
    
    # Metadata
    release_date: Optional[datetime] = None
    sunset_date: Optional[datetime] = None
    notes: str = ""
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for a request"""
        input_cost = (input_tokens / 1_000_000) * self.cost_per_1m_input
        output_cost = (output_tokens / 1_000_000) * self.cost_per_1m_output
        return input_cost + output_cost


@dataclass
class PromptVersion:
    """A versioned prompt"""
    prompt_id: str
    version: str  # Semantic versioning: "1.0.0"
    
    # Content
    system_prompt: str
    user_template: str
    
    # Constraints
    required_variables: List[str] = field(default_factory=list)
    max_input_length: int = 4000
    max_output_length: int = 2000
    
    # Model requirements
    min_model_tier: ModelTier = ModelTier.STANDARD
    recommended_model: Optional[str] = None
    
    # Lifecycle
    status: PromptStatus = PromptStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "system"
    
    # Audit
    change_notes: str = ""
    parent_version: Optional[str] = None  # For version history
    
    # Evaluation scores
    quality_score: Optional[float] = None
    safety_score: Optional[float] = None
    
    def __post_init__(self):
        # Generate content hash for immutability verification
        self._content_hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        content = f"{self.system_prompt}|{self.user_template}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def verify_integrity(self) -> bool:
        """Verify prompt hasn't been modified"""
        return self._content_hash == self._compute_hash()
    
    def render(self, variables: Dict[str, Any]) -> tuple[str, str]:
        """Render prompt with variables"""
        # Validate required variables
        missing = set(self.required_variables) - set(variables.keys())
        if missing:
            raise ValueError(f"Missing required variables: {missing}")
        
        # Render templates
        system = self.system_prompt
        user = self.user_template
        
        for key, value in variables.items():
            placeholder = f"{{{key}}}"
            system = system.replace(placeholder, str(value))
            user = user.replace(placeholder, str(value))
        
        return system, user
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt_id": self.prompt_id,
            "version": self.version,
            "status": self.status.value,
            "min_model_tier": self.min_model_tier.value,
            "recommended_model": self.recommended_model,
            "created_at": self.created_at.isoformat(),
            "quality_score": self.quality_score,
            "content_hash": self._content_hash
        }


class PromptRegistry:
    """
    Registry for versioned prompts.
    
    Enforces immutability and provides rollback capability.
    """
    
    def __init__(self):
        self._prompts: Dict[str, Dict[str, PromptVersion]] = {}  # {prompt_id: {version: PromptVersion}}
        self._production_versions: Dict[str, str] = {}  # {prompt_id: version}
        self._history: List[Dict[str, Any]] = []
    
    def register(self, prompt: PromptVersion) -> None:
        """Register a new prompt version"""
        if prompt.prompt_id not in self._prompts:
            self._prompts[prompt.prompt_id] = {}
        
        # Check for duplicate version
        if prompt.version in self._prompts[prompt.prompt_id]:
            raise ValueError(f"Version {prompt.version} already exists for {prompt.prompt_id}")
        
        # Store (deep copy to ensure immutability)
        self._prompts[prompt.prompt_id][prompt.version] = copy.deepcopy(prompt)
        
        # Log registration
        self._log_event("register", prompt.prompt_id, prompt.version)
    
    def promote_to_production(self, prompt_id: str, version: str) -> None:
        """Promote a version to production"""
        if prompt_id not in self._prompts:
            raise ValueError(f"Unknown prompt: {prompt_id}")
        
        if version not in self._prompts[prompt_id]:
            raise ValueError(f"Unknown version: {version}")
        
        prompt = self._prompts[prompt_id][version]
        
        # Validate scores before promotion
        if prompt.quality_score is not None and prompt.quality_score < 0.7:
            raise ValueError(f"Quality score {prompt.quality_score} is below threshold (0.7)")
        
        if prompt.safety_score is not None and prompt.safety_score < 0.9:
            raise ValueError(f"Safety score {prompt.safety_score} is below threshold (0.9)")
        
        # Demote current production version
        if prompt_id in self._production_versions:
            old_version = self._production_versions[prompt_id]
            self._prompts[prompt_id][old_version].status = PromptStatus.DEPRECATED
        
        # Promote new version
        prompt.status = PromptStatus.PRODUCTION
        self._production_versions[prompt_id] = version
        
        self._log_event("promote", prompt_id, version)
    
    def rollback(self, prompt_id: str, to_version: Optional[str] = None) -> str:
        """
        Rollback to a previous version.
        
        Args:
            prompt_id: The prompt to rollback
            to_version: Specific version to rollback to (default: previous production)
            
        Returns:
            The version rolled back to
        """
        if prompt_id not in self._prompts:
            raise ValueError(f"Unknown prompt: {prompt_id}")
        
        if to_version is None:
            # Find previous production version from history
            to_version = self._find_previous_production(prompt_id)
            if not to_version:
                raise ValueError("No previous production version found")
        
        if to_version not in self._prompts[prompt_id]:
            raise ValueError(f"Unknown version: {to_version}")
        
        # Mark current as rolled back
        if prompt_id in self._production_versions:
            current = self._production_versions[prompt_id]
            self._prompts[prompt_id][current].status = PromptStatus.ROLLED_BACK
        
        # Restore target version
        self._prompts[prompt_id][to_version].status = PromptStatus.PRODUCTION
        self._production_versions[prompt_id] = to_version
        
        self._log_event("rollback", prompt_id, to_version)
        
        return to_version
    
    def get_production_prompt(self, prompt_id: str) -> Optional[PromptVersion]:
        """Get the current production version of a prompt"""
        if prompt_id not in self._production_versions:
            return None
        
        version = self._production_versions[prompt_id]
        return self._prompts[prompt_id][version]
    
    def get_prompt(self, prompt_id: str, version: str) -> Optional[PromptVersion]:
        """Get a specific version of a prompt"""
        if prompt_id not in self._prompts:
            return None
        return self._prompts[prompt_id].get(version)
    
    def list_versions(self, prompt_id: str) -> List[Dict[str, Any]]:
        """List all versions of a prompt"""
        if prompt_id not in self._prompts:
            return []
        
        return [p.to_dict() for p in self._prompts[prompt_id].values()]
    
    def _find_previous_production(self, prompt_id: str) -> Optional[str]:
        """Find the previous production version from history"""
        for event in reversed(self._history):
            if event["prompt_id"] == prompt_id and event["action"] == "promote":
                # Skip current production
                if event["version"] != self._production_versions.get(prompt_id):
                    return event["version"]
        return None
    
    def _log_event(self, action: str, prompt_id: str, version: str) -> None:
        """Log a registry event"""
        self._history.append({
            "action": action,
            "prompt_id": prompt_id,
            "version": version,
            "timestamp": datetime.utcnow().isoformat()
        })


class ModelRegistry:
    """
    Registry for AI model configurations.
    
    Provides model selection and fallback logic.
    """
    
    def __init__(self):
        self._models: Dict[str, ModelConfig] = {}
        self._default_by_tier: Dict[ModelTier, str] = {}
        
        # Register default models
        self._register_defaults()
    
    def _register_defaults(self):
        """Register default model configurations"""
        defaults = [
            ModelConfig(
                model_id="gpt-4o",
                provider="openai",
                tier=ModelTier.PREMIUM,
                max_tokens=16384,
                context_window=128000,
                supports_vision=True,
                cost_per_1m_input=2.50,
                cost_per_1m_output=10.00,
                avg_latency_ms=800
            ),
            ModelConfig(
                model_id="gpt-4o-mini",
                provider="openai",
                tier=ModelTier.STANDARD,
                max_tokens=16384,
                context_window=128000,
                cost_per_1m_input=0.15,
                cost_per_1m_output=0.60,
                avg_latency_ms=400
            ),
            ModelConfig(
                model_id="claude-3-5-sonnet-20241022",
                provider="anthropic",
                tier=ModelTier.PREMIUM,
                max_tokens=8192,
                context_window=200000,
                supports_vision=True,
                cost_per_1m_input=3.00,
                cost_per_1m_output=15.00,
                avg_latency_ms=600
            ),
            ModelConfig(
                model_id="claude-3-5-haiku-20241022",
                provider="anthropic",
                tier=ModelTier.ECONOMY,
                max_tokens=8192,
                context_window=200000,
                cost_per_1m_input=0.80,
                cost_per_1m_output=4.00,
                avg_latency_ms=300
            ),
        ]
        
        for model in defaults:
            self.register(model)
            if model.tier not in self._default_by_tier:
                self._default_by_tier[model.tier] = model.model_id
    
    def register(self, model: ModelConfig) -> None:
        """Register a model configuration"""
        self._models[model.model_id] = model
    
    def get_model(self, model_id: str) -> Optional[ModelConfig]:
        """Get a model configuration"""
        return self._models.get(model_id)
    
    def select_model(
        self,
        min_tier: ModelTier = ModelTier.STANDARD,
        prefer_provider: Optional[str] = None,
        max_cost_per_1m: Optional[float] = None,
        require_vision: bool = False
    ) -> Optional[ModelConfig]:
        """
        Select an appropriate model based on requirements.
        
        Args:
            min_tier: Minimum capability tier
            prefer_provider: Preferred provider (openai, anthropic)
            max_cost_per_1m: Maximum cost per 1M input tokens
            require_vision: Whether vision capability is required
            
        Returns:
            Best matching model or None
        """
        tier_order = [ModelTier.ECONOMY, ModelTier.STANDARD, ModelTier.PREMIUM, ModelTier.REASONING]
        min_tier_idx = tier_order.index(min_tier)
        
        candidates = []
        
        for model in self._models.values():
            # Check tier requirement
            model_tier_idx = tier_order.index(model.tier)
            if model_tier_idx < min_tier_idx:
                continue
            
            # Check vision requirement
            if require_vision and not model.supports_vision:
                continue
            
            # Check cost constraint
            if max_cost_per_1m and model.cost_per_1m_input > max_cost_per_1m:
                continue
            
            candidates.append(model)
        
        if not candidates:
            return None
        
        # Sort by preference
        def score(m: ModelConfig) -> tuple:
            provider_match = 1 if prefer_provider and m.provider == prefer_provider else 0
            return (provider_match, -tier_order.index(m.tier), -m.cost_per_1m_input)
        
        candidates.sort(key=score, reverse=True)
        return candidates[0]
    
    def get_fallback_chain(self, primary_model_id: str) -> List[str]:
        """Get fallback model chain for reliability"""
        primary = self._models.get(primary_model_id)
        if not primary:
            return []
        
        fallbacks = []
        
        # Same tier, different provider
        for model in self._models.values():
            if model.model_id != primary_model_id:
                if model.tier == primary.tier and model.provider != primary.provider:
                    fallbacks.append(model.model_id)
        
        # Lower tier fallback
        tier_order = [ModelTier.ECONOMY, ModelTier.STANDARD, ModelTier.PREMIUM]
        current_idx = tier_order.index(primary.tier) if primary.tier in tier_order else 1
        
        if current_idx > 0:
            lower_tier = tier_order[current_idx - 1]
            if lower_tier in self._default_by_tier:
                fallbacks.append(self._default_by_tier[lower_tier])
        
        return fallbacks


# Global registries
_prompt_registry: Optional[PromptRegistry] = None
_model_registry: Optional[ModelRegistry] = None


def get_prompt_registry() -> PromptRegistry:
    """Get the global prompt registry"""
    global _prompt_registry
    if _prompt_registry is None:
        _prompt_registry = PromptRegistry()
    return _prompt_registry


def get_model_registry() -> ModelRegistry:
    """Get the global model registry"""
    global _model_registry
    if _model_registry is None:
        _model_registry = ModelRegistry()
    return _model_registry
