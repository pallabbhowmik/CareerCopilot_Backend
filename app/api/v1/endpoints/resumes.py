from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.services.resume_parser import parse_resume_file
from app.services.ats_explainability import calculate_ats_readiness
from app.models.all_models import Resume, User
from app.schemas.resume import ResumeInDB, ResumeUpdate, ResumeUploadResponse
from app.api.v1.endpoints.auth import get_current_user
import os
import aiofiles

router = APIRouter()

UPLOAD_DIR = "uploads/resumes"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.options("/upload")
async def upload_options():
    """Handle CORS preflight for upload endpoint"""
    return {"status": "ok"}

@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload and parse a resume (PDF/DOCX).
    Returns structured data and ATS readiness analysis.
    """
    # Validate file type
    if not file.filename.endswith(('.pdf', '.docx', '.doc')):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported")
    
    # Parse resume
    try:
        parsed_data = await parse_resume_file(file)
    except ValueError as e:
        print(f"ValueError in parse_resume_file: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Unexpected error in parse_resume_file: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Error processing resume: {str(e)}")
    
    # Save file
    file_path = f"{UPLOAD_DIR}/{current_user.id}_{file.filename}"
    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)
    
    # Calculate ATS readiness
    ats_readiness = calculate_ats_readiness(parsed_data)
    
    # Save to database
    db_resume = Resume(
        user_id=current_user.id,
        title=file.filename.rsplit('.', 1)[0],
        content_raw=parsed_data.get("raw_text", ""),
        content_structured=parsed_data,
        heatmap_data=ats_readiness,
        strength_score=ats_readiness.get("overall_score", 0),
        file_path=file_path
    )
    db.add(db_resume)
    db.commit()
    db.refresh(db_resume)
    
    # Prepare response with next steps
    next_steps = []
    if ats_readiness.get("parsing_success_score", 0) < 80:
        next_steps.append("Improve formatting for better ATS compatibility")
    if len(parsed_data.get("skills", [])) < 5:
        next_steps.append("Add more relevant skills to your resume")
    if not parsed_data.get("summary"):
        next_steps.append("Consider adding a professional summary")
    
    return ResumeUploadResponse(
        id=db_resume.id,
        title=db_resume.title,
        parsed_sections=parsed_data,
        ats_readiness=ats_readiness,
        next_steps=next_steps if next_steps else ["Your resume looks good! Review the analysis for detailed insights."]
    )

@router.get("/", response_model=List[ResumeInDB])
def get_resumes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all resumes for the current user."""
    return db.query(Resume).filter(Resume.user_id == current_user.id).all()

@router.get("/{resume_id}", response_model=ResumeInDB)
def get_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific resume."""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()
    
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    return resume

@router.put("/{resume_id}", response_model=ResumeInDB)
def update_resume(
    resume_id: int,
    resume_update: ResumeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a resume."""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()
    
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    # Update fields
    for field, value in resume_update.dict(exclude_unset=True).items():
        setattr(resume, field, value)
    
    # Recalculate ATS readiness if content changed
    if resume_update.content_structured:
        ats_readiness = calculate_ats_readiness(resume.content_structured)
        resume.heatmap_data = ats_readiness
        resume.strength_score = ats_readiness.get("overall_score", 0)
    
    db.commit()
    db.refresh(resume)
    return resume

@router.delete("/{resume_id}")
def delete_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a resume."""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()
    
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    # Delete file if exists
    if resume.file_path and os.path.exists(resume.file_path):
        os.remove(resume.file_path)
    
    db.delete(resume)
    db.commit()
    
    return {"message": "Resume deleted successfully"}

@router.post("/{resume_id}/duplicate", response_model=ResumeInDB)
def duplicate_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a duplicate/variant of an existing resume."""
    original = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()
    
    if not original:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    # Create duplicate
    duplicate = Resume(
        user_id=current_user.id,
        template_id=original.template_id,
        title=f"{original.title} (Copy)",
        content_raw=original.content_raw,
        content_structured=original.content_structured,
        style_config=original.style_config,
        heatmap_data=original.heatmap_data,
        bullet_feedback=original.bullet_feedback,
        strength_score=original.strength_score,
        variant_group_id=original.variant_group_id or str(original.id),
        version=original.version + 1,
        parent_resume_id=original.id
    )
    
    db.add(duplicate)
    db.commit()
    db.refresh(duplicate)
    
    return duplicate

