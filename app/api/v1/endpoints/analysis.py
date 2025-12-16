from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.ai_advisor import generate_gap_analysis

router = APIRouter()

@router.post("/compare/{resume_id}/{job_id}")
async def compare_resume_job(
    resume_id: int, 
    job_id: int, 
    db: Session = Depends(get_db)
):
    # Fetch from DB
    # Mock logic
    analysis_result = await generate_gap_analysis(resume_id, job_id)
    return analysis_result
