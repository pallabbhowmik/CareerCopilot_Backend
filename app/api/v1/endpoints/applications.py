from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.db.session import get_db
from app.models.all_models import Application, User
from app.api.v1.endpoints.auth import get_current_user

router = APIRouter()

class ApplicationCreate(BaseModel):
    resume_id: int
    company: str
    job_title: str
    job_url: Optional[str] = None
    notes: Optional[str] = None

class ApplicationUpdate(BaseModel):
    status: Optional[str] = None
    response_received: Optional[bool] = None
    interview_scheduled: Optional[bool] = None
    notes: Optional[str] = None

class ApplicationResponse(BaseModel):
    id: int
    resume_id: int
    company: str
    job_title: str
    job_url: Optional[str]
    status: str
    response_received: bool
    interview_scheduled: bool
    notes: Optional[str]
    applied_at: datetime
    
    class Config:
        from_attributes = True

@router.post("/", response_model=ApplicationResponse)
def create_application(
    app_data: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Track a new job application."""
    db_app = Application(
        user_id=current_user.id,
        resume_id=app_data.resume_id,
        company=app_data.company,
        job_title=app_data.job_title,
        job_url=app_data.job_url,
        notes=app_data.notes,
        status="applied"
    )
    db.add(db_app)
    db.commit()
    db.refresh(db_app)
    return db_app

@router.get("/", response_model=List[ApplicationResponse])
def get_applications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status: Optional[str] = None
):
    """Get all job applications for the current user."""
    query = db.query(Application).filter(Application.user_id == current_user.id)
    
    if status:
        query = query.filter(Application.status == status)
    
    return query.order_by(Application.applied_at.desc()).all()

@router.get("/{application_id}", response_model=ApplicationResponse)
def get_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific application."""
    app = db.query(Application).filter(
        Application.id == application_id,
        Application.user_id == current_user.id
    ).first()
    
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    return app

@router.put("/{application_id}", response_model=ApplicationResponse)
def update_application(
    application_id: int,
    app_update: ApplicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an application status."""
    app = db.query(Application).filter(
        Application.id == application_id,
        Application.user_id == current_user.id
    ).first()
    
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    for field, value in app_update.dict(exclude_unset=True).items():
        setattr(app, field, value)
    
    db.commit()
    db.refresh(app)
    return app

@router.get("/stats/summary")
def get_application_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get application statistics."""
    apps = db.query(Application).filter(Application.user_id == current_user.id).all()
    
    total = len(apps)
    by_status = {}
    for app in apps:
        status = app.status
        by_status[status] = by_status.get(status, 0) + 1
    
    response_rate = sum(1 for app in apps if app.response_received) / total if total > 0 else 0
    interview_rate = sum(1 for app in apps if app.interview_scheduled) / total if total > 0 else 0
    
    return {
        "total_applications": total,
        "by_status": by_status,
        "response_rate": round(response_rate * 100, 1),
        "interview_rate": round(interview_rate * 100, 1)
    }
