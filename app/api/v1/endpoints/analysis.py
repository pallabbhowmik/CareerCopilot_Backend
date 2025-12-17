from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, List
from uuid import UUID
from app.db.session import get_db
from app.models.all_models import Resume, JobDescription, Analysis, UserProfile
from app.api.v1.endpoints.auth import get_current_user
from app.services.llm_engine import ai_service
from app.services.ats_explainability import calculate_ats_readiness

router = APIRouter()

class JobDescriptionCreate(BaseModel):
    title: str
    company: str
    content_raw: str
    url: str = None

class BulletImproveRequest(BaseModel):
    bullet: str
    role: str = None
    company: str = None

class BulletImproveResponse(BaseModel):
    original: str
    improved: str
    explanation: str
    score_before: int
    score_after: int
    improvements: List[str] = []

@router.post("/job-description")
async def create_job_description(
    job_desc: JobDescriptionCreate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Save a job description for analysis.
    """
    db_job = JobDescription(
        user_id=current_user.user_id,
        title=job_desc.title,
        company=job_desc.company,
        content_raw=job_desc.content_raw,
        url=job_desc.url
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    
    return db_job

@router.post("/compare/{resume_id}/{job_id}")
async def compare_resume_job(
    resume_id: int, 
    job_id: int, 
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Compare a resume against a job description.
    Returns gap analysis and recommendations.
    """
    # Fetch resume
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.user_id
    ).first()
    
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    # Fetch job description
    job_desc = db.query(JobDescription).filter(JobDescription.id == job_id).first()
    if not job_desc:
        raise HTTPException(status_code=404, detail="Job description not found")
    
    # Perform AI analysis
    match_analysis = await ai_service.analyze_job_match(
        resume.content_structured,
        job_desc.content_raw
    )
    
    # Calculate ATS readiness against this specific JD
    ats_analysis = calculate_ats_readiness(
        resume.content_structured,
        {"required_skills": match_analysis.get("missing_skills", [])}
    )
    
    # Save analysis to database
    db_analysis = Analysis(
        user_id=current_user.user_id,
        resume_id=resume_id,
        job_description_id=job_id,
        score_data=match_analysis,
        gap_analysis=ats_analysis,
        recommendations=match_analysis.get("recommendations", [])
    )
    db.add(db_analysis)
    db.commit()
    db.refresh(db_analysis)
    
    return {
        "analysis_id": db_analysis.id,
        "match_score": match_analysis.get("match_score", 0),
        "matching_skills": match_analysis.get("matching_skills", []),
        "missing_skills": match_analysis.get("missing_skills", []),
        "experience_fit": match_analysis.get("experience_fit", ""),
        "recommendations": match_analysis.get("recommendations", []),
        "ats_readiness": ats_analysis,
        "confidence": match_analysis.get("confidence", "medium")
    }

@router.post("/improve-bullet", response_model=BulletImproveResponse)
async def improve_bullet_point(
    request: BulletImproveRequest,
    current_user: UserProfile = Depends(get_current_user)
):
    """
    AI-powered bullet point improvement.
    Returns improved version with explanation.
    """
    context = {
        "role": request.role or "Professional",
        "company": request.company or "Company"
    }
    
    result = await ai_service.improve_bullet_point(request.bullet, context)
    
    return BulletImproveResponse(
        original=result["original"],
        improved=result["improved"],
        explanation=result["explanation"],
        score_before=result.get("score_before", 50),
        score_after=result.get("score_after", 50),
        improvements=result.get("improvements", [])
    )

@router.get("/resume/{resume_id}/ats-readiness")
async def get_ats_readiness(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get detailed ATS readiness analysis for a resume.
    """
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.user_id
    ).first()
    
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    if not resume.content_structured:
        raise HTTPException(status_code=400, detail="Resume has no structured content")
    
    # Calculate fresh ATS readiness
    ats_analysis = calculate_ats_readiness(resume.content_structured)
    
    # Update resume with latest analysis
    resume.heatmap_data = ats_analysis
    resume.strength_score = ats_analysis.get("overall_score", 0)
    db.commit()
    
    return ats_analysis

@router.get("/history")
async def get_analysis_history(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get user's analysis history.
    """
    analyses = db.query(Analysis).filter(
        Analysis.user_id == current_user.user_id
    ).order_by(Analysis.created_at.desc()).limit(20).all()
    
    return analyses

