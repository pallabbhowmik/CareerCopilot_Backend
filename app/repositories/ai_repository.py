"""
AI Repository - Data access layer for AI system tables
Handles prompts, requests, responses, evaluations
"""

from typing import Dict, List, Optional, Any
from uuid import UUID
from datetime import datetime
from supabase import Client

from .supabase_client import get_supabase


class AIRepository:
    """Repository for AI system operations"""
    
    def __init__(self, client: Optional[Client] = None):
        """
        Initialize AI repository
        
        Args:
            client: Optional Supabase client (uses service role by default)
        """
        self.client = client or get_supabase()
    
    # =====================================================
    # PROMPT REGISTRY
    # =====================================================
    
    def get_production_prompt(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """
        Get current production prompt for a skill
        
        Args:
            skill_name: Name of the AI skill
        
        Returns:
            Prompt data or None if not found
        """
        response = self.client.table("ai_prompts") \
            .select("*") \
            .eq("skill_name", skill_name) \
            .eq("status", "production") \
            .order("version", desc=True) \
            .limit(1) \
            .execute()
        
        return response.data[0] if response.data else None
    
    def get_prompt_by_version(self, skill_name: str, version: int) -> Optional[Dict[str, Any]]:
        """Get specific prompt version"""
        response = self.client.table("ai_prompts") \
            .select("*") \
            .eq("skill_name", skill_name) \
            .eq("version", version) \
            .single() \
            .execute()
        
        return response.data if response.data else None
    
    def list_prompts(
        self, 
        skill_name: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List prompts with optional filters
        
        Args:
            skill_name: Filter by skill
            status: Filter by status (draft/testing/production/retired)
        
        Returns:
            List of prompts
        """
        query = self.client.table("ai_prompts").select("*")
        
        if skill_name:
            query = query.eq("skill_name", skill_name)
        if status:
            query = query.eq("status", status)
        
        response = query.order("created_at", desc=True).execute()
        return response.data or []
    
    # =====================================================
    # REQUEST/RESPONSE LOGGING
    # =====================================================
    
    def record_ai_request(
        self,
        user_id: UUID,
        skill_name: str,
        prompt_version: str,
        model: str,
        temperature: float,
        input_data: Dict[str, Any],
        latency_ms: int,
        input_tokens: int,
        output_tokens: int,
        estimated_cost_usd: float,
        trace_id: Optional[str] = None
    ) -> UUID:
        """
        Record AI request using stored procedure
        
        Returns:
            Request ID
        """
        response = self.client.rpc(
            "record_ai_request",
            {
                "p_user_id": str(user_id),
                "p_skill_name": skill_name,
                "p_prompt_version": prompt_version,
                "p_model": model,
                "p_temperature": temperature,
                "p_input_data": input_data,
                "p_latency_ms": latency_ms,
                "p_input_tokens": input_tokens,
                "p_output_tokens": output_tokens,
                "p_estimated_cost_usd": estimated_cost_usd,
                "p_trace_id": trace_id
            }
        ).execute()
        
        return UUID(response.data)
    
    def record_ai_response(
        self,
        request_id: UUID,
        raw_output: str,
        structured_output: Dict[str, Any],
        validation_passed: bool,
        validation_errors: Optional[Dict[str, Any]],
        confidence_score: float,
        safety_check_passed: bool
    ) -> UUID:
        """
        Record AI response using stored procedure
        
        Returns:
            Response ID
        """
        response = self.client.rpc(
            "record_ai_response",
            {
                "p_request_id": str(request_id),
                "p_raw_output": raw_output,
                "p_structured_output": structured_output,
                "p_validation_passed": validation_passed,
                "p_validation_errors": validation_errors,
                "p_confidence_score": confidence_score,
                "p_safety_check_passed": safety_check_passed
            }
        ).execute()
        
        return UUID(response.data)
    
    def get_request_with_response(self, request_id: UUID) -> Optional[Dict[str, Any]]:
        """Get AI request with its response"""
        response = self.client.table("ai_requests") \
            .select("*, ai_responses(*)") \
            .eq("id", str(request_id)) \
            .single() \
            .execute()
        
        return response.data if response.data else None
    
    # =====================================================
    # EVALUATIONS
    # =====================================================
    
    def create_evaluation(
        self,
        response_id: UUID,
        evaluator_type: str,
        helpfulness_score: float,
        safety_score: float,
        consistency_score: float,
        evaluator_notes: Optional[str] = None
    ) -> UUID:
        """
        Create evaluation for an AI response
        
        Args:
            response_id: ID of the response being evaluated
            evaluator_type: 'human' or 'ai'
            helpfulness_score: 0.0-1.0
            safety_score: 0.0-1.0
            consistency_score: 0.0-1.0
            evaluator_notes: Optional notes
        
        Returns:
            Evaluation ID
        """
        response = self.client.table("ai_evaluations") \
            .insert({
                "response_id": str(response_id),
                "evaluator_type": evaluator_type,
                "helpfulness_score": helpfulness_score,
                "safety_score": safety_score,
                "consistency_score": consistency_score,
                "evaluator_notes": evaluator_notes
            }) \
            .execute()
        
        return UUID(response.data[0]["id"])
    
    def get_evaluations_for_response(self, response_id: UUID) -> List[Dict[str, Any]]:
        """Get all evaluations for a response"""
        response = self.client.table("ai_evaluations") \
            .select("*") \
            .eq("response_id", str(response_id)) \
            .execute()
        
        return response.data or []
    
    # =====================================================
    # PROMPT CANDIDATES (AUTO-IMPROVEMENT)
    # =====================================================
    
    def create_prompt_candidate(
        self,
        skill_name: str,
        current_prompt_id: UUID,
        new_prompt_text: str,
        change_rationale: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UUID:
        """
        Create new prompt candidate for testing
        
        Returns:
            Candidate ID
        """
        response = self.client.table("prompt_candidates") \
            .insert({
                "skill_name": skill_name,
                "current_prompt_id": str(current_prompt_id),
                "new_prompt_text": new_prompt_text,
                "change_rationale": change_rationale,
                "status": "testing",
                "metadata": metadata or {}
            }) \
            .execute()
        
        return UUID(response.data[0]["id"])
    
    def update_candidate_test_results(
        self,
        candidate_id: UUID,
        test_run_count: int,
        avg_score: float,
        vs_current_delta: float
    ) -> None:
        """Update candidate with test results"""
        self.client.table("prompt_candidates") \
            .update({
                "test_run_count": test_run_count,
                "avg_score": avg_score,
                "vs_current_delta": vs_current_delta,
                "status": "validated" if test_run_count >= 100 else "testing"
            }) \
            .eq("id", str(candidate_id)) \
            .execute()
    
    def get_promotable_candidates(self) -> List[Dict[str, Any]]:
        """Get candidates ready for production promotion"""
        response = self.client.rpc("get_promotable_prompt_candidates").execute()
        return response.data or []
    
    def promote_candidate_to_production(
        self, 
        candidate_id: UUID,
        admin_user_id: UUID
    ) -> UUID:
        """
        Promote candidate to production (ADMIN ONLY)
        
        Returns:
            New production prompt ID
        """
        response = self.client.rpc(
            "promote_prompt_to_production",
            {
                "p_candidate_id": str(candidate_id),
                "p_admin_user_id": str(admin_user_id)
            }
        ).execute()
        
        return UUID(response.data)
    
    # =====================================================
    # EXPLANATIONS
    # =====================================================
    
    def create_explanation(
        self,
        resume_version_id: UUID,
        section_type: str,
        explanation_text: str,
        deterministic_signals: List[str],
        confidence_level: str,
        ai_response_id: Optional[UUID] = None
    ) -> UUID:
        """
        Create explanation for a resume section
        
        Args:
            resume_version_id: Resume version being explained
            section_type: Type of section (bullets/summary/etc)
            explanation_text: Human-readable explanation
            deterministic_signals: List of signals that justify the explanation
            confidence_level: 'high', 'medium', 'low'
            ai_response_id: Optional link to AI response
        
        Returns:
            Explanation ID
        """
        response = self.client.table("explanations") \
            .insert({
                "resume_version_id": str(resume_version_id),
                "section_type": section_type,
                "explanation_text": explanation_text,
                "deterministic_signals": deterministic_signals,
                "confidence_level": confidence_level,
                "ai_response_id": str(ai_response_id) if ai_response_id else None
            }) \
            .execute()
        
        return UUID(response.data[0]["id"])
    
    def get_explanations_for_resume(
        self, 
        resume_version_id: UUID
    ) -> List[Dict[str, Any]]:
        """Get all explanations for a resume version"""
        response = self.client.table("explanations") \
            .select("*") \
            .eq("resume_version_id", str(resume_version_id)) \
            .order("created_at", desc=True) \
            .execute()
        
        return response.data or []
    
    # =====================================================
    # OBSERVABILITY
    # =====================================================
    
    def get_ai_request_summary(
        self,
        user_id: Optional[UUID] = None,
        skill_name: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get AI request summary for observability dashboard
        
        Returns:
            List of daily summaries with costs and metrics
        """
        query = self.client.table("ai_request_summary").select("*")
        
        if user_id:
            query = query.eq("user_id", str(user_id))
        if skill_name:
            query = query.eq("skill_name", skill_name)
        if start_date:
            query = query.gte("request_date", start_date.isoformat())
        if end_date:
            query = query.lte("request_date", end_date.isoformat())
        
        response = query.order("request_date", desc=True).execute()
        return response.data or []
    
    def get_prompt_performance(self, skill_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get prompt performance metrics"""
        query = self.client.table("prompt_performance").select("*")
        
        if skill_name:
            query = query.eq("skill_name", skill_name)
        
        response = query.order("avg_helpfulness", desc=True).execute()
        return response.data or []
