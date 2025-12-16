"""
AI Orchestrator v2

The central orchestration layer that coordinates:
- Intelligence pipeline (3-layer system)
- AI Skills execution
- Prompt/Model registry
- Evaluation system
- Security gateway

This is the main entry point for all AI operations.
"""
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import asyncio
import json
import hashlib

from ..intelligence import (
    IntelligencePipeline,
    SignalEngine,
    InterpretationEngine
)
from ..intelligence.layer3_judgment import JudgmentEngine
from ..skills import AISkill, SkillInput, SkillOutput, ToneConstraint
from ..registry import (
    get_prompt_registry,
    get_model_registry,
    PromptVersion,
    ModelConfig,
    ModelTier
)
from ..evaluation import get_evaluation_engine, EvaluationReport
from ..security import get_security_gateway, SecurityScanResult


class OrchestratorMode(str, Enum):
    """Operating modes for the orchestrator"""
    PRODUCTION = "production"    # Full security, evaluation, logging
    DEVELOPMENT = "development"  # Relaxed security, verbose logging
    TESTING = "testing"          # No external calls, mocked responses


@dataclass
class OrchestratorConfig:
    """Configuration for the orchestrator"""
    mode: OrchestratorMode = OrchestratorMode.PRODUCTION
    
    # Feature flags
    enable_security: bool = True
    enable_evaluation: bool = True
    enable_logging: bool = True
    enable_caching: bool = True
    
    # Limits
    max_concurrent_skills: int = 5
    max_retries: int = 3
    timeout_seconds: float = 30.0
    
    # Model preferences
    default_model_tier: ModelTier = ModelTier.STANDARD
    fallback_enabled: bool = True


@dataclass
class OrchestratorRequest:
    """A request to the orchestrator"""
    request_id: str
    user_id: str
    
    # What to do
    operation: str  # "analyze", "skill", "feedback", etc.
    
    # Input
    input_data: Dict[str, Any]
    
    # Options
    tone: ToneConstraint = ToneConstraint.SUPPORTIVE
    model_tier: Optional[ModelTier] = None
    skip_security: bool = False
    
    # Context
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.request_id:
            self.request_id = hashlib.sha256(
                f"{self.user_id}{datetime.utcnow().isoformat()}".encode()
            ).hexdigest()[:16]


@dataclass
class OrchestratorResponse:
    """Response from the orchestrator"""
    request_id: str
    success: bool
    
    # Output
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    # Metadata
    processing_time_ms: float = 0
    model_used: Optional[str] = None
    tokens_used: Optional[int] = None
    
    # Evaluation
    evaluation: Optional[Dict[str, Any]] = None
    
    # Audit
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "processing_time_ms": self.processing_time_ms,
            "model_used": self.model_used,
            "evaluation": self.evaluation,
            "timestamp": self.timestamp.isoformat()
        }


class AIOrchestrator:
    """
    Central AI orchestration layer.
    
    Coordinates all AI components and provides a unified interface
    for AI operations.
    """
    
    def __init__(
        self,
        config: Optional[OrchestratorConfig] = None,
        ai_provider=None  # External AI provider (OpenAI, Anthropic, etc.)
    ):
        self.config = config or OrchestratorConfig()
        self.ai_provider = ai_provider
        
        # Initialize components
        self.intelligence_pipeline = IntelligencePipeline()
        self.prompt_registry = get_prompt_registry()
        self.model_registry = get_model_registry()
        self.evaluation_engine = get_evaluation_engine()
        self.security_gateway = get_security_gateway()
        
        # Registered skills
        self._skills: Dict[str, AISkill] = {}
        
        # Request log
        self._request_log: List[Dict[str, Any]] = []
        
        # Cache
        self._cache: Dict[str, Any] = {}
    
    def register_skill(self, skill: AISkill) -> None:
        """Register an AI skill"""
        self._skills[skill.name] = skill
    
    async def process(self, request: OrchestratorRequest) -> OrchestratorResponse:
        """
        Main entry point for all AI operations.
        
        Routes to appropriate handler based on operation type.
        """
        import time
        start_time = time.time()
        
        try:
            # Security check
            if self.config.enable_security and not request.skip_security:
                security_result = await self._security_check(request)
                if not security_result[0]:
                    return OrchestratorResponse(
                        request_id=request.request_id,
                        success=False,
                        error=security_result[1]
                    )
            
            # Route to handler
            if request.operation == "analyze":
                result = await self._handle_analyze(request)
            elif request.operation == "skill":
                result = await self._handle_skill(request)
            elif request.operation == "feedback":
                result = await self._handle_feedback(request)
            elif request.operation == "generate":
                result = await self._handle_generate(request)
            else:
                return OrchestratorResponse(
                    request_id=request.request_id,
                    success=False,
                    error=f"Unknown operation: {request.operation}"
                )
            
            # Evaluate output
            evaluation = None
            if self.config.enable_evaluation and result:
                evaluation = await self._evaluate_output(
                    result.get("output", ""),
                    request
                )
            
            processing_time = (time.time() - start_time) * 1000
            
            response = OrchestratorResponse(
                request_id=request.request_id,
                success=True,
                result=result,
                processing_time_ms=processing_time,
                model_used=result.get("model_used"),
                evaluation=evaluation
            )
            
            # Log request
            if self.config.enable_logging:
                self._log_request(request, response)
            
            return response
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            return OrchestratorResponse(
                request_id=request.request_id,
                success=False,
                error=str(e),
                processing_time_ms=processing_time
            )
    
    async def _security_check(
        self,
        request: OrchestratorRequest
    ) -> tuple[bool, Optional[str]]:
        """Run security checks on request"""
        input_text = json.dumps(request.input_data, default=str)
        
        allowed, sanitized, error = await self.security_gateway.process_input(
            request.user_id,
            input_text
        )
        
        return allowed, error
    
    async def _handle_analyze(
        self,
        request: OrchestratorRequest
    ) -> Dict[str, Any]:
        """Handle resume analysis request"""
        resume_data = request.input_data.get("resume", {})
        job_data = request.input_data.get("job", None)
        
        # Run intelligence pipeline
        output = await self.intelligence_pipeline.analyze(
            resume_data=resume_data,
            job_data=job_data,
            options={
                "tone": request.tone.value,
                "user_id": request.user_id
            }
        )
        
        return {
            "analysis": output.to_dict(),
            "priority_feedback": output.get_priority_feedback(),
            "signal_count": len(output.signals),
            "interpretation_count": len(output.interpretations),
            "judgment_count": len(output.judgments)
        }
    
    async def _handle_skill(
        self,
        request: OrchestratorRequest
    ) -> Dict[str, Any]:
        """Handle skill execution request"""
        skill_name = request.input_data.get("skill_name")
        
        if skill_name not in self._skills:
            raise ValueError(f"Unknown skill: {skill_name}")
        
        skill = self._skills[skill_name]
        
        # Build skill input
        skill_input = SkillInput(
            primary_content=request.input_data.get("content", ""),
            context=request.input_data.get("context", {}),
            tone=request.tone
        )
        
        # Execute skill
        output = await skill.execute(skill_input)
        
        return {
            "skill_output": output.to_dict(),
            "confidence": output.confidence,
            "reasoning": output.reasoning_trace
        }
    
    async def _handle_feedback(
        self,
        request: OrchestratorRequest
    ) -> Dict[str, Any]:
        """Handle feedback generation request"""
        # Get appropriate prompt
        prompt = self.prompt_registry.get_production_prompt("feedback_explainer")
        if not prompt:
            raise ValueError("Feedback prompt not available")
        
        # Select model
        model_tier = request.model_tier or self.config.default_model_tier
        model = self.model_registry.select_model(min_tier=model_tier)
        
        if not model:
            raise ValueError("No suitable model available")
        
        # Render prompt
        variables = {
            "feedback_items": json.dumps(request.input_data.get("feedback_items", [])),
            "context": request.input_data.get("context", "General feedback")
        }
        
        system_prompt, user_prompt = prompt.render(variables)
        
        # Call AI (would use ai_provider)
        output = await self._call_ai(model, system_prompt, user_prompt)
        
        return {
            "output": output,
            "model_used": model.model_id,
            "prompt_version": prompt.version
        }
    
    async def _handle_generate(
        self,
        request: OrchestratorRequest
    ) -> Dict[str, Any]:
        """Handle content generation request"""
        prompt_id = request.input_data.get("prompt_id")
        variables = request.input_data.get("variables", {})
        
        # Get prompt
        prompt = self.prompt_registry.get_production_prompt(prompt_id)
        if not prompt:
            raise ValueError(f"Prompt not available: {prompt_id}")
        
        # Select model
        model = self.model_registry.select_model(
            min_tier=prompt.min_model_tier
        )
        
        if not model:
            raise ValueError("No suitable model available")
        
        # Render and call
        system_prompt, user_prompt = prompt.render(variables)
        output = await self._call_ai(model, system_prompt, user_prompt)
        
        return {
            "output": output,
            "model_used": model.model_id,
            "prompt_id": prompt_id,
            "prompt_version": prompt.version
        }
    
    async def _call_ai(
        self,
        model: ModelConfig,
        system_prompt: str,
        user_prompt: str
    ) -> str:
        """Call AI provider"""
        if self.ai_provider:
            # Real AI call
            return await self.ai_provider.complete(
                model=model.model_id,
                system=system_prompt,
                user=user_prompt
            )
        
        # Mock response for testing
        return f"[Mock response for {model.model_id}]"
    
    async def _evaluate_output(
        self,
        output: str,
        request: OrchestratorRequest
    ) -> Dict[str, Any]:
        """Evaluate AI output"""
        if not output:
            return {}
        
        report = self.evaluation_engine.evaluate(
            output,
            context={
                "original_content": json.dumps(request.input_data),
                "operation": request.operation
            }
        )
        
        return report.to_dict()
    
    def _log_request(
        self,
        request: OrchestratorRequest,
        response: OrchestratorResponse
    ) -> None:
        """Log request for auditing"""
        self._request_log.append({
            "request_id": request.request_id,
            "user_id": request.user_id,
            "operation": request.operation,
            "success": response.success,
            "processing_time_ms": response.processing_time_ms,
            "model_used": response.model_used,
            "timestamp": response.timestamp.isoformat()
        })
    
    def get_request_log(
        self,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get request log for auditing"""
        log = self._request_log
        
        if user_id:
            log = [r for r in log if r["user_id"] == user_id]
        
        return log[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics"""
        total_requests = len(self._request_log)
        successful = sum(1 for r in self._request_log if r["success"])
        
        return {
            "total_requests": total_requests,
            "successful_requests": successful,
            "success_rate": successful / total_requests if total_requests > 0 else 0,
            "registered_skills": list(self._skills.keys()),
            "cache_size": len(self._cache),
            "mode": self.config.mode.value
        }


# Convenience function for creating orchestrator
def create_orchestrator(
    mode: OrchestratorMode = OrchestratorMode.PRODUCTION,
    ai_provider=None
) -> AIOrchestrator:
    """Create and configure an AI orchestrator"""
    config = OrchestratorConfig(mode=mode)
    
    # Adjust config based on mode
    if mode == OrchestratorMode.DEVELOPMENT:
        config.enable_security = False
        config.enable_evaluation = True
    elif mode == OrchestratorMode.TESTING:
        config.enable_security = False
        config.enable_evaluation = False
        config.enable_logging = False
    
    orchestrator = AIOrchestrator(config, ai_provider)
    
    # Register default skills
    from ..skills.bullet_analyzer import BulletQualityAnalyzer
    from ..skills.ats_explainer import ATSRiskExplainer
    from ..skills.skill_gap_reasoner import SkillGapReasoner
    from ..skills.section_rewriter import ResumeSectionRewriter
    from ..skills.career_advisor import CareerTransitionAdvisor
    
    orchestrator.register_skill(BulletQualityAnalyzer())
    orchestrator.register_skill(ATSRiskExplainer())
    orchestrator.register_skill(SkillGapReasoner())
    orchestrator.register_skill(ResumeSectionRewriter())
    orchestrator.register_skill(CareerTransitionAdvisor())
    
    return orchestrator
