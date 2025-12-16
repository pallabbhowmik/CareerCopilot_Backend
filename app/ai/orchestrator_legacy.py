"""
AI Orchestrator

Central orchestration for all AI operations with:
- Structured output validation
- Fallback logic
- Cost tracking
- Observability
- Rate limiting
"""
from typing import Dict, Any, Optional, List, Type, TypeVar
from dataclasses import dataclass
import json
import logging
from datetime import datetime
from uuid import uuid4

from app.ai.providers import AIProvider, AIRequest, AIResponse, create_provider, ProviderType
from app.ai.prompts import PromptRegistry, PromptTemplate

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class OrchestrationConfig:
    """Configuration for AI orchestration"""
    primary_provider: str = "openai"
    fallback_provider: Optional[str] = None
    default_model: str = "gpt-4o-mini"
    fallback_model: Optional[str] = None
    
    # Rate limiting
    max_requests_per_minute: int = 60
    max_tokens_per_minute: int = 100000
    
    # Cost controls
    max_cost_per_request: float = 0.10
    max_daily_cost: float = 50.0
    
    # Timeouts
    request_timeout_seconds: int = 30


@dataclass  
class OrchestrationResult:
    """Result from AI orchestration"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    raw_response: Optional[str] = None
    
    # Metadata
    request_id: str = ""
    provider_used: str = ""
    model_used: str = ""
    tokens_used: int = 0
    response_time_ms: int = 0
    estimated_cost: float = 0.0
    
    # Error handling
    error: Optional[str] = None
    used_fallback: bool = False
    validation_errors: List[str] = None
    
    def __post_init__(self):
        if not self.request_id:
            self.request_id = str(uuid4())
        if self.validation_errors is None:
            self.validation_errors = []


class AIOrchestrator:
    """
    Central AI orchestration service.
    
    Responsibilities:
    - Route requests to appropriate providers
    - Validate and parse structured outputs
    - Handle fallbacks on failure
    - Track costs and usage
    - Provide observability
    """
    
    def __init__(
        self,
        config: OrchestrationConfig,
        openai_key: Optional[str] = None,
        anthropic_key: Optional[str] = None
    ):
        self.config = config
        self._providers: Dict[str, AIProvider] = {}
        
        # Initialize providers
        if openai_key:
            self._providers["openai"] = create_provider("openai", openai_key)
        if anthropic_key:
            self._providers["anthropic"] = create_provider("anthropic", anthropic_key)
        
        # Always have mock available for testing
        self._providers["mock"] = create_provider("mock")
        
        # Usage tracking
        self._daily_cost = 0.0
        self._daily_requests = 0
        self._last_reset = datetime.utcnow().date()
    
    def _get_provider(self, name: str) -> Optional[AIProvider]:
        """Get a provider by name if available"""
        provider = self._providers.get(name)
        if provider and provider.is_available():
            return provider
        return None
    
    def _reset_daily_counters_if_needed(self):
        """Reset daily counters if it's a new day"""
        today = datetime.utcnow().date()
        if today > self._last_reset:
            self._daily_cost = 0.0
            self._daily_requests = 0
            self._last_reset = today
    
    async def execute_prompt(
        self,
        prompt_name: str,
        prompt_version: str = "1.0",
        variables: Optional[Dict[str, Any]] = None,
        model_override: Optional[str] = None,
        skip_validation: bool = False
    ) -> OrchestrationResult:
        """
        Execute a registered prompt and return structured result.
        
        Args:
            prompt_name: Name of the prompt in PromptRegistry
            prompt_version: Version of the prompt
            variables: Variables to substitute in prompt template
            model_override: Override the default model
            skip_validation: Skip JSON validation (for text responses)
        """
        self._reset_daily_counters_if_needed()
        
        # Get prompt template
        prompt = PromptRegistry.get(prompt_name, prompt_version)
        if not prompt:
            return OrchestrationResult(
                success=False,
                error=f"Prompt not found: {prompt_name} v{prompt_version}"
            )
        
        # Check cost limits
        if self._daily_cost >= self.config.max_daily_cost:
            return OrchestrationResult(
                success=False,
                error="Daily cost limit exceeded"
            )
        
        # Prepare request
        variables = variables or {}
        try:
            user_prompt = prompt.format_user_prompt(**variables)
        except KeyError as e:
            return OrchestrationResult(
                success=False,
                error=f"Missing prompt variable: {e}"
            )
        
        model = model_override or self.config.default_model
        
        request = AIRequest(
            system_prompt=prompt.system_prompt,
            user_prompt=user_prompt,
            model=model,
            temperature=prompt.temperature,
            max_tokens=prompt.max_tokens,
            response_format=None if skip_validation else prompt.expected_output_format
        )
        
        # Try primary provider
        primary_provider = self._get_provider(self.config.primary_provider)
        result = await self._execute_with_provider(
            primary_provider, 
            request,
            prompt.expected_output_format if not skip_validation else "text"
        )
        
        # Try fallback if primary failed
        if not result.success and self.config.fallback_provider:
            fallback_provider = self._get_provider(self.config.fallback_provider)
            if fallback_provider:
                logger.warning(f"Primary provider failed, trying fallback: {result.error}")
                
                if self.config.fallback_model:
                    request.model = self.config.fallback_model
                
                result = await self._execute_with_provider(
                    fallback_provider,
                    request,
                    prompt.expected_output_format if not skip_validation else "text"
                )
                result.used_fallback = True
        
        # Track usage
        self._daily_cost += result.estimated_cost
        self._daily_requests += 1
        
        return result
    
    async def _execute_with_provider(
        self,
        provider: Optional[AIProvider],
        request: AIRequest,
        expected_format: str
    ) -> OrchestrationResult:
        """Execute request with a specific provider"""
        if not provider:
            return OrchestrationResult(
                success=False,
                error="No available provider"
            )
        
        try:
            response = await provider.complete(request)
            
            result = OrchestrationResult(
                success=True,
                raw_response=response.content,
                provider_used=provider.provider_type.value,
                model_used=response.model,
                tokens_used=response.total_tokens,
                response_time_ms=response.response_time_ms,
                estimated_cost=response.estimated_cost_usd
            )
            
            # Parse JSON if expected
            if expected_format == "json":
                try:
                    result.data = json.loads(response.content)
                except json.JSONDecodeError as e:
                    result.success = False
                    result.error = f"Invalid JSON response: {e}"
                    result.validation_errors.append(str(e))
            else:
                result.data = {"text": response.content}
            
            return result
            
        except Exception as e:
            logger.error(f"Provider execution failed: {e}")
            return OrchestrationResult(
                success=False,
                error=str(e),
                provider_used=provider.provider_type.value if provider else "none"
            )
    
    async def parse_resume(self, resume_text: str) -> OrchestrationResult:
        """Parse resume text into structured data"""
        return await self.execute_prompt(
            "resume_parse",
            variables={"resume_text": resume_text[:8000]}  # Limit text length
        )
    
    async def analyze_job(
        self, 
        job_title: str,
        company: str,
        job_description: str
    ) -> OrchestrationResult:
        """Analyze job description"""
        return await self.execute_prompt(
            "job_analyze",
            variables={
                "job_title": job_title,
                "company": company,
                "job_description": job_description[:6000]
            }
        )
    
    async def analyze_match(
        self,
        resume_skills: List[str],
        experience_summary: str,
        experience_years: float,
        required_skills: List[str],
        preferred_skills: List[str],
        experience_level: str
    ) -> OrchestrationResult:
        """Analyze resume-job match"""
        return await self.execute_prompt(
            "match_analyze",
            variables={
                "resume_skills": ", ".join(resume_skills[:30]),
                "experience_summary": experience_summary[:1000],
                "experience_years": experience_years,
                "required_skills": ", ".join(required_skills[:20]),
                "preferred_skills": ", ".join(preferred_skills[:15]),
                "experience_level": experience_level
            }
        )
    
    async def improve_bullet(
        self,
        bullet: str,
        role: str,
        company: str,
        is_current: bool = False
    ) -> OrchestrationResult:
        """Improve a resume bullet point"""
        return await self.execute_prompt(
            "bullet_improve",
            variables={
                "bullet": bullet,
                "role": role,
                "company": company,
                "is_current": str(is_current).lower()
            }
        )
    
    async def career_chat(
        self,
        question: str,
        user_context: Dict[str, Any],
        additional_context: str = ""
    ) -> OrchestrationResult:
        """Career advice chat"""
        # Build system prompt with user context
        prompt = PromptRegistry.get("career_chat", "1.0")
        if not prompt:
            return OrchestrationResult(success=False, error="Chat prompt not found")
        
        system_prompt = prompt.system_prompt.format(
            target_role=user_context.get("target_role", "Not specified"),
            experience_level=user_context.get("experience_level", "Not specified"),
            industry=user_context.get("industry", "Not specified"),
            location=user_context.get("country", "Not specified"),
            career_goal=user_context.get("career_goal", "Not specified")
        )
        
        user_prompt = prompt.format_user_prompt(
            question=question,
            additional_context=additional_context
        )
        
        request = AIRequest(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=self.config.default_model,
            temperature=prompt.temperature,
            max_tokens=prompt.max_tokens,
            response_format=None
        )
        
        return await self._execute_with_provider(
            self._get_provider(self.config.primary_provider),
            request,
            "text"
        )
    
    async def extract_skills(self, text: str, context: str = "resume") -> OrchestrationResult:
        """Extract skills from text"""
        return await self.execute_prompt(
            "skill_extract",
            variables={
                "text": text[:3000],
                "context": context
            }
        )
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics"""
        return {
            "daily_cost": self._daily_cost,
            "daily_requests": self._daily_requests,
            "cost_limit": self.config.max_daily_cost,
            "cost_remaining": self.config.max_daily_cost - self._daily_cost,
            "last_reset": self._last_reset.isoformat()
        }


# Singleton instance (initialized in main.py)
_orchestrator: Optional[AIOrchestrator] = None


def get_orchestrator() -> AIOrchestrator:
    """Get the global orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        raise RuntimeError("AIOrchestrator not initialized. Call init_orchestrator first.")
    return _orchestrator


def init_orchestrator(
    openai_key: Optional[str] = None,
    anthropic_key: Optional[str] = None,
    config: Optional[OrchestrationConfig] = None
) -> AIOrchestrator:
    """Initialize the global orchestrator"""
    global _orchestrator
    _orchestrator = AIOrchestrator(
        config=config or OrchestrationConfig(),
        openai_key=openai_key,
        anthropic_key=anthropic_key
    )
    return _orchestrator
