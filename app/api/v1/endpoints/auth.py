from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import verify_supabase_token
from app.core.config import settings
from app.models.all_models import UserProfile
import uuid

router = APIRouter()

# We don't have a login endpoint in FastAPI anymore, but we keep this for Swagger UI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)

def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
) -> UserProfile:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        raise credentials_exception

    payload = verify_supabase_token(token)
    if not payload:
        raise credentials_exception
        
    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception
    
    # Fetch user profile using the user_id from Supabase Auth
    # Note: user_profiles.user_id matches auth.users.id (which is the 'sub' in JWT)
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise credentials_exception

    user = db.query(UserProfile).filter(UserProfile.user_id == user_uuid).first()
    
    if user is None:
        # If user exists in Auth but not in user_profiles, we might need to create it
        # But the trigger should have handled it.
        # If it's missing, it's an error state or race condition.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found"
        )
        
    return user

@router.get("/me")
def get_me(current_user: UserProfile = Depends(get_current_user)):
    return current_user


