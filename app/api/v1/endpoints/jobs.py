from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.all_models import JobDescription, UserProfile
from app.api.v1.endpoints.auth import get_current_user
from app.services.job_analyzer import analyze_job_text

router = APIRouter()

class JobCreate(BaseModel):
    text: str
    url: str | None = None

@router.post("/analyze")
async def analyze_job(
    job_in: JobCreate, 
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    # 1. Analyze text
    structured_reqs = await analyze_job_text(job_in.text)
    
    # 2. Save to DB
    db_job = JobDescription(
        user_id=current_user.user_id,
        title="Detected Job Title", # In real app, extract this
        company="Detected Company",
        content_raw=job_in.text,
        requirements_structured=structured_reqs,
        url=job_in.url
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    
    return db_job
