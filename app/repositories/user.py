"""
User Repository

Data access layer for User and UserProfile entities.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.models import User, UserProfile
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User entity operations"""
    
    def __init__(self, db: Session):
        super().__init__(db, User)
    
    # =========================================================================
    # USER-SPECIFIC QUERIES
    # =========================================================================
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address"""
        return self.db.query(User).filter(
            User.email == email,
            User.is_deleted == False
        ).first()
    
    def get_by_firebase_uid(self, firebase_uid: str) -> Optional[User]:
        """Get user by Firebase UID"""
        return self.db.query(User).filter(
            User.firebase_uid == firebase_uid,
            User.is_deleted == False
        ).first()
    
    def email_exists(self, email: str) -> bool:
        """Check if email is already registered"""
        return self.db.query(User).filter(
            User.email == email
        ).first() is not None
    
    def get_active_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all active (non-deleted, verified) users"""
        return self.db.query(User).filter(
            User.is_deleted == False
        ).offset(skip).limit(limit).all()
    
    def search_users(
        self,
        query: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[User]:
        """Search users by name or email"""
        search_pattern = f"%{query}%"
        return self.db.query(User).filter(
            User.is_deleted == False,
            (User.name.ilike(search_pattern) | User.email.ilike(search_pattern))
        ).offset(skip).limit(limit).all()
    
    # =========================================================================
    # USER CREATION & AUTHENTICATION
    # =========================================================================
    
    def create_user(
        self,
        email: str,
        firebase_uid: str,
        name: Optional[str] = None
    ) -> User:
        """
        Create a new user with Firebase authentication.
        
        Args:
            email: User's email address
            firebase_uid: Firebase authentication UID
            name: Optional display name
            
        Returns:
            Created User instance
        """
        user_data = {
            "email": email,
            "firebase_uid": firebase_uid,
            "name": name or email.split("@")[0]
        }
        return self.create(user_data)
    
    def update_last_login(self, user_id: int) -> Optional[User]:
        """Update user's last login timestamp"""
        return self.update(user_id, {"last_login": datetime.utcnow()})
    
    # =========================================================================
    # USER PROFILE
    # =========================================================================
    
    def get_profile(self, user_id: int) -> Optional[UserProfile]:
        """Get user profile by user ID"""
        return self.db.query(UserProfile).filter(
            UserProfile.user_id == user_id
        ).first()
    
    def create_profile(
        self,
        user_id: int,
        profile_data: Dict[str, Any]
    ) -> UserProfile:
        """Create user profile"""
        profile_data["user_id"] = user_id
        profile = UserProfile(**profile_data)
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile
    
    def update_profile(
        self,
        user_id: int,
        profile_data: Dict[str, Any]
    ) -> Optional[UserProfile]:
        """Update user profile"""
        profile = self.get_profile(user_id)
        if not profile:
            return self.create_profile(user_id, profile_data)
        
        for field, value in profile_data.items():
            if hasattr(profile, field):
                setattr(profile, field, value)
        
        profile.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(profile)
        return profile
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user activity statistics"""
        from app.models.models import Resume, Analysis
        
        user = self.get_by_id(user_id)
        if not user:
            return {}
        
        resume_count = self.db.query(func.count(Resume.id)).filter(
            Resume.user_id == user_id,
            Resume.is_deleted == False
        ).scalar()
        
        analysis_count = self.db.query(func.count(Analysis.id)).filter(
            Analysis.user_id == user_id
        ).scalar()
        
        return {
            "user_id": user_id,
            "resumes_created": resume_count or 0,
            "analyses_run": analysis_count or 0,
            "member_since": user.created_at.isoformat() if user.created_at else None,
            "last_active": user.last_login.isoformat() if user.last_login else None
        }
