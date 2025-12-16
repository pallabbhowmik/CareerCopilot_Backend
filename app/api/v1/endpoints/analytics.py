from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.analytics import analytics_service

router = APIRouter()

@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    # Mock user_id = 1
    return analytics_service.get_user_stats(db, user_id=1)

@router.get("/ab-test")
def get_ab_test(db: Session = Depends(get_db)):
    # Mock user_id = 1
    return analytics_service.get_ab_test_results(db, user_id=1)
