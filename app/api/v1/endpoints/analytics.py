from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.analytics import analytics_service
from app.models.all_models import UserProfile
from app.api.v1.endpoints.auth import get_current_user

router = APIRouter()

@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    return analytics_service.get_user_stats(db, user_id=current_user.user_id)

@router.get("/ab-test")
def get_ab_test(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    return analytics_service.get_ab_test_results(db, user_id=current_user.user_id)
