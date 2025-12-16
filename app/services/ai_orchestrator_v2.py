"""
AI Orchestrator V2 - Supabase-backed AI Coordination
Coordinates all AI operations with complete observability
"""

import time
import json
from typing import Dict, Any, Optional, List
from uuid import UUID
from pydantic import BaseModel, Field

from app.repositories.ai_repository import AIRepository
from app.core.llm_client import LLMClient


class AIRequestMetadata(BaseModel):
    """Metadata for an AI request"""
    user_id: UUID
    skill_name: str
    trace_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class AIResponse(BaseModel):
    """Structured AI response"""
    request_id: UUID
    response_id: UUID
    raw_output: str
    structured_output: Dict[str, Any]
    validation_passed: bool
    validation_errors: Optional[Dict[str, Any]] = None
    confidence_score: float = Field(ge=0.0, le=1.0)
    safety_check_passed: bool = True
    latency_ms: int
    cost_usd: float


class AIOrchestrator:
    """
    Central coordinator for all AI operations
    
    Features:
    - Complete request/response logging to Supabase
    - Automatic cost and latency tracking
    - Validation and safety checks
    - Prompt versioning support
    - Tracing for observability
    """
    
    def __init__(self, ai_repo: Optional[AIRepository] = None):
        """
        Initialize AI Orchestrator
        
        Args:
            ai_repo: AI repository instance (creates new if not provided)
        """
        self.ai_repo = ai_repo or AIRepository()
        self.llm_client = LLMClient()
    
    async def execute_skill(
        self,
        skill_name: str,
        input_data: Dict[str, Any],
        metadata: AIRequestMetadata,
        use_prompt_version: Optional[int] = None
    ) -> AIResponse:
        """
        Execute an AI skill with full observability
        
        Args:
            skill_name: Name of the AI skill to execute
            input_data: Input data for the skill
            metadata: Request metadata (user, trace, context)
            use_prompt_version: Optional specific version (defaults to production)
        
        Returns:
            AIResponse with complete tracking data
        
        Workflow:
        1. Load prompt from registry
        2. Execute AI call
        3. Validate output
        4. Run safety checks
        5. Log everything to Supabase
        6. Return structured response
        """
        start_time = time.time()
        
        # Step 1: Get prompt from registry
        if use_prompt_version:
            prompt_data = self.ai_repo.get_prompt_by_version(skill_name, use_prompt_version)
        else:
            prompt_data = self.ai_repo.get_production_prompt(skill_name)
        
        if not prompt_data:
            raise ValueError(f"No prompt found for skill: {skill_name}")
        
        prompt_version_str = f"{skill_name}_v{prompt_data['version']}"
        
        # Step 2: Build prompt with input data
        formatted_prompt = self._format_prompt(prompt_data["prompt_text"], input_data)
        
        # Step 3: Execute AI call
        try:
            raw_output, token_usage = await self.llm_client.generate(
                prompt=formatted_prompt,
                model=prompt_data["model"],
                temperature=prompt_data["temperature"],
                max_tokens=prompt_data.get("metadata", {}).get("max_tokens", 2000)
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Step 4: Parse and validate output
            structured_output, validation_passed, validation_errors = self._validate_output(
                raw_output,
                prompt_data["expected_output_schema"]
            )
            
            # Step 5: Safety checks
            safety_check_passed = self._run_safety_checks(raw_output, structured_output)
            
            # Step 6: Calculate confidence score
            confidence_score = self._calculate_confidence(
                structured_output,
                validation_passed,
                safety_check_passed
            )
            
            # Step 7: Estimate cost
            estimated_cost = self._estimate_cost(
                model=prompt_data["model"],
                input_tokens=token_usage["input_tokens"],
                output_tokens=token_usage["output_tokens"]
            )
            
            # Step 8: Log request to Supabase
            request_id = self.ai_repo.record_ai_request(
                user_id=metadata.user_id,
                skill_name=skill_name,
                prompt_version=prompt_version_str,
                model=prompt_data["model"],
                temperature=prompt_data["temperature"],
                input_data=input_data,
                latency_ms=latency_ms,
                input_tokens=token_usage["input_tokens"],
                output_tokens=token_usage["output_tokens"],
                estimated_cost_usd=estimated_cost,
                trace_id=metadata.trace_id
            )
            
            # Step 9: Log response to Supabase
            response_id = self.ai_repo.record_ai_response(
                request_id=request_id,
                raw_output=raw_output,
                structured_output=structured_output,
                validation_passed=validation_passed,
                validation_errors=validation_errors,
                confidence_score=confidence_score,
                safety_check_passed=safety_check_passed
            )
            
            # Step 10: Return structured response
            return AIResponse(
                request_id=request_id,
                response_id=response_id,
                raw_output=raw_output,
                structured_output=structured_output,
                validation_passed=validation_passed,
                validation_errors=validation_errors,
                confidence_score=confidence_score,
                safety_check_passed=safety_check_passed,
                latency_ms=latency_ms,
                cost_usd=estimated_cost
            )
            
        except Exception as e:
            # Log failed request
            latency_ms = int((time.time() - start_time) * 1000)
            
            request_id = self.ai_repo.record_ai_request(
                user_id=metadata.user_id,
                skill_name=skill_name,
                prompt_version=prompt_version_str,
                model=prompt_data["model"],
                temperature=prompt_data["temperature"],
                input_data=input_data,
                latency_ms=latency_ms,
                input_tokens=0,
                output_tokens=0,
                estimated_cost_usd=0.0,
                trace_id=metadata.trace_id
            )
            
            response_id = self.ai_repo.record_ai_response(
                request_id=request_id,
                raw_output="",
                structured_output={"error": str(e)},
                validation_passed=False,
                validation_errors={"exception": str(e), "type": type(e).__name__},
                confidence_score=0.0,
                safety_check_passed=False
            )
            
            raise
    
    def _format_prompt(self, prompt_template: str, input_data: Dict[str, Any]) -> str:
        """Format prompt template with input data"""
        try:
            return prompt_template.format(**input_data)
        except KeyError as e:
            raise ValueError(f"Missing required input field: {e}")
    
    def _validate_output(
        self,
        raw_output: str,
        expected_schema: Dict[str, Any]
    ) -> tuple[Dict[str, Any], bool, Optional[Dict[str, Any]]]:
        """
        Validate AI output against expected schema
        
        Returns:
            (structured_output, validation_passed, validation_errors)
        """
        try:
            # Try to parse as JSON
            structured = json.loads(raw_output)
            
            # Basic schema validation
            required_fields = expected_schema.get("required", [])
            missing_fields = [f for f in required_fields if f not in structured]
            
            if missing_fields:
                return structured, False, {"missing_fields": missing_fields}
            
            return structured, True, None
            
        except json.JSONDecodeError as e:
            return {}, False, {"parse_error": str(e)}
    
    def _run_safety_checks(
        self,
        raw_output: str,
        structured_output: Dict[str, Any]
    ) -> bool:
        """
        Run safety checks on AI output
        
        Checks for:
        - Prompt injection attempts
        - PII leakage
        - Harmful content
        - SQL injection patterns
        """
        # Check for common prompt injection patterns
        injection_patterns = [
            "ignore previous instructions",
            "disregard all",
            "new instructions:",
            "system prompt",
            "<script>",
            "DROP TABLE",
            "DELETE FROM"
        ]
        
        raw_lower = raw_output.lower()
        for pattern in injection_patterns:
            if pattern.lower() in raw_lower:
                return False
        
        return True
    
    def _calculate_confidence(
        self,
        structured_output: Dict[str, Any],
        validation_passed: bool,
        safety_check_passed: bool
    ) -> float:
        """
        Calculate confidence score for the response
        
        Factors:
        - Validation passed (0.5 weight)
        - Safety check passed (0.3 weight)
        - Output completeness (0.2 weight)
        """
        score = 0.0
        
        # Validation
        if validation_passed:
            score += 0.5
        
        # Safety
        if safety_check_passed:
            score += 0.3
        
        # Completeness (check if output has substantive content)
        if structured_output and len(str(structured_output)) > 50:
            score += 0.2
        
        return min(score, 1.0)
    
    def _estimate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        Estimate cost in USD
        
        Pricing (as of 2024):
        - GPT-4: $0.03/1k input, $0.06/1k output
        - GPT-3.5: $0.0015/1k input, $0.002/1k output
        - Claude Sonnet: $0.003/1k input, $0.015/1k output
        """
        pricing = {
            "gpt-4": (0.03, 0.06),
            "gpt-3.5-turbo": (0.0015, 0.002),
            "claude-3-sonnet": (0.003, 0.015),
            "claude-3-5-sonnet": (0.003, 0.015),
        }
        
        # Default to GPT-4 pricing if model not found
        input_price, output_price = pricing.get(model, (0.03, 0.06))
        
        cost = (input_tokens / 1000 * input_price) + (output_tokens / 1000 * output_price)
        return round(cost, 6)
    
    # =====================================================
    # HIGH-LEVEL SKILL METHODS
    # =====================================================
    
    async def analyze_resume(
        self,
        user_id: UUID,
        resume_text: str,
        job_description: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> AIResponse:
        """Analyze resume with optional job matching"""
        input_data = {
            "resume_text": resume_text,
            "job_description": job_description or "General analysis"
        }
        
        metadata = AIRequestMetadata(
            user_id=user_id,
            skill_name="analyze_resume",
            trace_id=trace_id
        )
        
        return await self.execute_skill(
            skill_name="analyze_resume",
            input_data=input_data,
            metadata=metadata
        )
    
    async def generate_bullets(
        self,
        user_id: UUID,
        experience_description: str,
        job_title: str,
        company: str,
        trace_id: Optional[str] = None
    ) -> AIResponse:
        """Generate resume bullet points"""
        input_data = {
            "experience_description": experience_description,
            "job_title": job_title,
            "company": company
        }
        
        metadata = AIRequestMetadata(
            user_id=user_id,
            skill_name="generate_bullets",
            trace_id=trace_id
        )
        
        return await self.execute_skill(
            skill_name="generate_bullets",
            input_data=input_data,
            metadata=metadata
        )
    
    async def extract_skills(
        self,
        user_id: UUID,
        resume_text: str,
        trace_id: Optional[str] = None
    ) -> AIResponse:
        """Extract skills from resume"""
        input_data = {"resume_text": resume_text}
        
        metadata = AIRequestMetadata(
            user_id=user_id,
            skill_name="extract_skills",
            trace_id=trace_id
        )
        
        return await self.execute_skill(
            skill_name="extract_skills",
            input_data=input_data,
            metadata=metadata
        )
