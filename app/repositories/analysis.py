"""
Analysis Repository

Data access layer for Analysis and AIRequest entities.
Tracks all analysis operations and AI usage.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_

from app.models.models import Analysis, AIRequest
from app.repositories.base import BaseRepository


class AnalysisRepository(BaseRepository[Analysis]):
    """Repository for Analysis entity operations"""
    
    def __init__(self, db: Session):
        super().__init__(db, Analysis)
    
    # =========================================================================
    # ANALYSIS-SPECIFIC QUERIES
    # =========================================================================
    
    def get_by_user(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 50
    ) -> List[Analysis]:
        """Get all analyses for a user"""
        return self.db.query(Analysis).filter(
            Analysis.user_id == user_id
        ).order_by(desc(Analysis.created_at)).offset(skip).limit(limit).all()
    
    def get_by_resume(self, resume_id: int) -> List[Analysis]:
        """Get all analyses for a specific resume"""
        return self.db.query(Analysis).filter(
            Analysis.resume_id == resume_id
        ).order_by(desc(Analysis.created_at)).all()
    
    def get_by_job(self, job_id: int) -> List[Analysis]:
        """Get all analyses for a specific job description"""
        return self.db.query(Analysis).filter(
            Analysis.job_id == job_id
        ).order_by(desc(Analysis.created_at)).all()
    
    def get_by_resume_and_job(
        self,
        resume_id: int,
        job_id: int
    ) -> List[Analysis]:
        """Get analyses comparing specific resume to job"""
        return self.db.query(Analysis).filter(
            Analysis.resume_id == resume_id,
            Analysis.job_id == job_id
        ).order_by(desc(Analysis.created_at)).all()
    
    def get_latest_for_resume_job(
        self,
        resume_id: int,
        job_id: int
    ) -> Optional[Analysis]:
        """Get most recent analysis for resume-job pair"""
        return self.db.query(Analysis).filter(
            Analysis.resume_id == resume_id,
            Analysis.job_id == job_id
        ).order_by(desc(Analysis.created_at)).first()
    
    def get_by_type(
        self,
        user_id: int,
        analysis_type: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[Analysis]:
        """Get analyses by type (ats_check, match, etc.)"""
        return self.db.query(Analysis).filter(
            Analysis.user_id == user_id,
            Analysis.analysis_type == analysis_type
        ).order_by(desc(Analysis.created_at)).offset(skip).limit(limit).all()
    
    # =========================================================================
    # ANALYSIS CREATION
    # =========================================================================
    
    def create_analysis(
        self,
        user_id: int,
        analysis_type: str,
        results_json: Dict[str, Any],
        resume_id: Optional[int] = None,
        job_id: Optional[int] = None,
        processing_time_ms: Optional[int] = None
    ) -> Analysis:
        """
        Create a new analysis record.
        
        Args:
            user_id: User who ran the analysis
            analysis_type: Type of analysis (ats_check, match, skill_gap, etc.)
            results_json: Full analysis results
            resume_id: Optional associated resume
            job_id: Optional associated job
            processing_time_ms: Time taken to process
            
        Returns:
            Created Analysis instance
        """
        analysis_data = {
            "user_id": user_id,
            "analysis_type": analysis_type,
            "results_json": results_json,
            "resume_id": resume_id,
            "job_id": job_id,
            "processing_time_ms": processing_time_ms
        }
        return self.create(analysis_data)
    
    # =========================================================================
    # AI REQUEST TRACKING
    # =========================================================================
    
    def log_ai_request(
        self,
        user_id: int,
        request_type: str,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        cost_usd: float,
        latency_ms: int,
        success: bool = True,
        error_message: Optional[str] = None,
        analysis_id: Optional[int] = None
    ) -> AIRequest:
        """
        Log an AI API request for monitoring and cost tracking.
        
        Args:
            user_id: User who made the request
            request_type: Type of request (parse, analyze, chat, etc.)
            provider: AI provider (openai, anthropic)
            model: Model used
            prompt_tokens: Input tokens
            completion_tokens: Output tokens
            total_tokens: Total tokens
            cost_usd: Estimated cost
            latency_ms: Request latency
            success: Whether request succeeded
            error_message: Error if failed
            analysis_id: Associated analysis if any
            
        Returns:
            Created AIRequest instance
        """
        ai_request = AIRequest(
            user_id=user_id,
            request_type=request_type,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            success=success,
            error_message=error_message,
            analysis_id=analysis_id
        )
        self.db.add(ai_request)
        self.db.commit()
        self.db.refresh(ai_request)
        return ai_request
    
    def get_ai_requests_for_user(
        self,
        user_id: int,
        since: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[AIRequest]:
        """Get AI requests for a user"""
        query = self.db.query(AIRequest).filter(
            AIRequest.user_id == user_id
        )
        
        if since:
            query = query.filter(AIRequest.created_at >= since)
        
        return query.order_by(desc(AIRequest.created_at)).offset(skip).limit(limit).all()
    
    # =========================================================================
    # USAGE STATISTICS
    # =========================================================================
    
    def get_user_usage_today(self, user_id: int) -> Dict[str, Any]:
        """Get user's AI usage for today"""
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        result = self.db.query(
            func.count(AIRequest.id).label("request_count"),
            func.sum(AIRequest.total_tokens).label("total_tokens"),
            func.sum(AIRequest.cost_usd).label("total_cost")
        ).filter(
            AIRequest.user_id == user_id,
            AIRequest.created_at >= today_start
        ).first()
        
        return {
            "request_count": result.request_count or 0,
            "total_tokens": result.total_tokens or 0,
            "total_cost_usd": float(result.total_cost or 0)
        }
    
    def get_user_usage_this_month(self, user_id: int) -> Dict[str, Any]:
        """Get user's AI usage for this month"""
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        result = self.db.query(
            func.count(AIRequest.id).label("request_count"),
            func.sum(AIRequest.total_tokens).label("total_tokens"),
            func.sum(AIRequest.cost_usd).label("total_cost")
        ).filter(
            AIRequest.user_id == user_id,
            AIRequest.created_at >= month_start
        ).first()
        
        return {
            "request_count": result.request_count or 0,
            "total_tokens": result.total_tokens or 0,
            "total_cost_usd": float(result.total_cost or 0)
        }
    
    def get_analysis_stats(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive analysis statistics for a user"""
        total_analyses = self.db.query(func.count(Analysis.id)).filter(
            Analysis.user_id == user_id
        ).scalar() or 0
        
        # Breakdown by type
        type_breakdown = self.db.query(
            Analysis.analysis_type,
            func.count(Analysis.id).label("count")
        ).filter(
            Analysis.user_id == user_id
        ).group_by(Analysis.analysis_type).all()
        
        # Average processing time
        avg_processing = self.db.query(
            func.avg(Analysis.processing_time_ms)
        ).filter(
            Analysis.user_id == user_id
        ).scalar()
        
        # Recent activity (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_count = self.db.query(func.count(Analysis.id)).filter(
            Analysis.user_id == user_id,
            Analysis.created_at >= week_ago
        ).scalar() or 0
        
        return {
            "total_analyses": total_analyses,
            "by_type": {t: c for t, c in type_breakdown},
            "avg_processing_time_ms": int(avg_processing) if avg_processing else 0,
            "analyses_last_7_days": recent_count
        }
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Get global platform statistics (admin use)"""
        total_analyses = self.db.query(func.count(Analysis.id)).scalar() or 0
        total_ai_requests = self.db.query(func.count(AIRequest.id)).scalar() or 0
        
        total_cost = self.db.query(func.sum(AIRequest.cost_usd)).scalar() or 0
        total_tokens = self.db.query(func.sum(AIRequest.total_tokens)).scalar() or 0
        
        # Today's stats
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_analyses = self.db.query(func.count(Analysis.id)).filter(
            Analysis.created_at >= today_start
        ).scalar() or 0
        
        today_cost = self.db.query(func.sum(AIRequest.cost_usd)).filter(
            AIRequest.created_at >= today_start
        ).scalar() or 0
        
        return {
            "total_analyses": total_analyses,
            "total_ai_requests": total_ai_requests,
            "total_cost_usd": float(total_cost),
            "total_tokens": total_tokens,
            "today_analyses": today_analyses,
            "today_cost_usd": float(today_cost or 0)
        }
    
    # =========================================================================
    # RATE LIMITING HELPERS
    # =========================================================================
    
    def check_rate_limit(
        self,
        user_id: int,
        limit_type: str,
        max_requests: int,
        window_minutes: int
    ) -> Dict[str, Any]:
        """
        Check if user is within rate limits.
        
        Args:
            user_id: User to check
            limit_type: Type of limit (analysis, ai_request, etc.)
            max_requests: Maximum allowed requests
            window_minutes: Time window in minutes
            
        Returns:
            Dict with allowed status and remaining count
        """
        window_start = datetime.utcnow() - timedelta(minutes=window_minutes)
        
        if limit_type == "analysis":
            current_count = self.db.query(func.count(Analysis.id)).filter(
                Analysis.user_id == user_id,
                Analysis.created_at >= window_start
            ).scalar() or 0
        else:
            current_count = self.db.query(func.count(AIRequest.id)).filter(
                AIRequest.user_id == user_id,
                AIRequest.created_at >= window_start
            ).scalar() or 0
        
        remaining = max(0, max_requests - current_count)
        
        return {
            "allowed": current_count < max_requests,
            "current_count": current_count,
            "max_requests": max_requests,
            "remaining": remaining,
            "window_minutes": window_minutes,
            "resets_at": (window_start + timedelta(minutes=window_minutes)).isoformat()
        }
