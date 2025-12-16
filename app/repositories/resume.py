"""
Resume Repository

Data access layer for Resume, ResumeSection, and ResumeBullet entities.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc

from app.models.models import Resume, ResumeSection, ResumeBullet
from app.repositories.base import BaseRepository


class ResumeRepository(BaseRepository[Resume]):
    """Repository for Resume entity operations"""
    
    def __init__(self, db: Session):
        super().__init__(db, Resume)
    
    # =========================================================================
    # RESUME-SPECIFIC QUERIES
    # =========================================================================
    
    def get_by_user(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 50
    ) -> List[Resume]:
        """Get all resumes for a user"""
        return self.db.query(Resume).filter(
            Resume.user_id == user_id,
            Resume.is_deleted == False
        ).order_by(desc(Resume.updated_at)).offset(skip).limit(limit).all()
    
    def get_latest_for_user(self, user_id: int) -> Optional[Resume]:
        """Get the most recently updated resume for a user"""
        return self.db.query(Resume).filter(
            Resume.user_id == user_id,
            Resume.is_deleted == False
        ).order_by(desc(Resume.updated_at)).first()
    
    def get_with_sections(self, resume_id: int) -> Optional[Resume]:
        """Get resume with all sections eagerly loaded"""
        return self.db.query(Resume).options(
            joinedload(Resume.sections).joinedload(ResumeSection.bullets)
        ).filter(
            Resume.id == resume_id,
            Resume.is_deleted == False
        ).first()
    
    def get_by_uuid_with_sections(self, uuid_str: str) -> Optional[Resume]:
        """Get resume by UUID with all sections"""
        return self.db.query(Resume).options(
            joinedload(Resume.sections).joinedload(ResumeSection.bullets)
        ).filter(
            Resume.uuid == uuid_str,
            Resume.is_deleted == False
        ).first()
    
    # =========================================================================
    # RESUME CREATION
    # =========================================================================
    
    def create_resume(
        self,
        user_id: int,
        title: str,
        raw_text: Optional[str] = None,
        parsed_json: Optional[Dict[str, Any]] = None,
        file_name: Optional[str] = None,
        file_type: Optional[str] = None
    ) -> Resume:
        """
        Create a new resume.
        
        Args:
            user_id: Owner user ID
            title: Resume title/name
            raw_text: Original text content
            parsed_json: Parsed structured data
            file_name: Original file name
            file_type: File MIME type
            
        Returns:
            Created Resume instance
        """
        resume_data = {
            "user_id": user_id,
            "title": title,
            "raw_text": raw_text,
            "parsed_json": parsed_json,
            "file_name": file_name,
            "file_type": file_type,
            "version": 1
        }
        return self.create(resume_data)
    
    def create_new_version(self, resume_id: int) -> Optional[Resume]:
        """
        Create a new version of an existing resume.
        
        Copies the resume data with incremented version number.
        """
        original = self.get_by_id(resume_id)
        if not original:
            return None
        
        new_resume = Resume(
            user_id=original.user_id,
            title=f"{original.title} (v{original.version + 1})",
            raw_text=original.raw_text,
            parsed_json=original.parsed_json,
            file_name=original.file_name,
            file_type=original.file_type,
            version=original.version + 1,
            parent_version_id=original.id
        )
        
        self.db.add(new_resume)
        self.db.commit()
        self.db.refresh(new_resume)
        return new_resume
    
    # =========================================================================
    # SECTION MANAGEMENT
    # =========================================================================
    
    def add_section(
        self,
        resume_id: int,
        section_type: str,
        title: str,
        content: Optional[str] = None,
        order: int = 0
    ) -> ResumeSection:
        """Add a section to a resume"""
        section = ResumeSection(
            resume_id=resume_id,
            section_type=section_type,
            title=title,
            content=content,
            order=order
        )
        self.db.add(section)
        self.db.commit()
        self.db.refresh(section)
        return section
    
    def get_sections(self, resume_id: int) -> List[ResumeSection]:
        """Get all sections for a resume, ordered"""
        return self.db.query(ResumeSection).filter(
            ResumeSection.resume_id == resume_id
        ).order_by(ResumeSection.order).all()
    
    def update_section(
        self,
        section_id: int,
        update_data: Dict[str, Any]
    ) -> Optional[ResumeSection]:
        """Update a resume section"""
        section = self.db.query(ResumeSection).filter(
            ResumeSection.id == section_id
        ).first()
        
        if not section:
            return None
        
        for field, value in update_data.items():
            if hasattr(section, field):
                setattr(section, field, value)
        
        section.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(section)
        return section
    
    def delete_section(self, section_id: int) -> bool:
        """Delete a resume section"""
        section = self.db.query(ResumeSection).filter(
            ResumeSection.id == section_id
        ).first()
        
        if not section:
            return False
        
        self.db.delete(section)
        self.db.commit()
        return True
    
    # =========================================================================
    # BULLET MANAGEMENT
    # =========================================================================
    
    def add_bullet(
        self,
        section_id: int,
        text: str,
        order: int = 0,
        strength_score: Optional[int] = None,
        improvement_suggestions: Optional[List[str]] = None
    ) -> ResumeBullet:
        """Add a bullet point to a section"""
        bullet = ResumeBullet(
            section_id=section_id,
            text=text,
            order=order,
            strength_score=strength_score,
            improvement_suggestions=improvement_suggestions
        )
        self.db.add(bullet)
        self.db.commit()
        self.db.refresh(bullet)
        return bullet
    
    def get_bullets(self, section_id: int) -> List[ResumeBullet]:
        """Get all bullets for a section, ordered"""
        return self.db.query(ResumeBullet).filter(
            ResumeBullet.section_id == section_id
        ).order_by(ResumeBullet.order).all()
    
    def update_bullet(
        self,
        bullet_id: int,
        update_data: Dict[str, Any]
    ) -> Optional[ResumeBullet]:
        """Update a bullet point"""
        bullet = self.db.query(ResumeBullet).filter(
            ResumeBullet.id == bullet_id
        ).first()
        
        if not bullet:
            return None
        
        for field, value in update_data.items():
            if hasattr(bullet, field):
                setattr(bullet, field, value)
        
        bullet.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(bullet)
        return bullet
    
    def delete_bullet(self, bullet_id: int) -> bool:
        """Delete a bullet point"""
        bullet = self.db.query(ResumeBullet).filter(
            ResumeBullet.id == bullet_id
        ).first()
        
        if not bullet:
            return False
        
        self.db.delete(bullet)
        self.db.commit()
        return True
    
    # =========================================================================
    # SEARCH & ANALYTICS
    # =========================================================================
    
    def search_resumes(
        self,
        user_id: int,
        query: str,
        skip: int = 0,
        limit: int = 20
    ) -> List[Resume]:
        """Search user's resumes by title or content"""
        search_pattern = f"%{query}%"
        return self.db.query(Resume).filter(
            Resume.user_id == user_id,
            Resume.is_deleted == False,
            (Resume.title.ilike(search_pattern) | Resume.raw_text.ilike(search_pattern))
        ).order_by(desc(Resume.updated_at)).offset(skip).limit(limit).all()
    
    def get_resume_count(self, user_id: int) -> int:
        """Get total resume count for a user"""
        return self.db.query(func.count(Resume.id)).filter(
            Resume.user_id == user_id,
            Resume.is_deleted == False
        ).scalar() or 0
    
    def get_version_history(self, resume_id: int) -> List[Resume]:
        """Get all versions of a resume"""
        resume = self.get_by_id(resume_id)
        if not resume:
            return []
        
        # Find the root resume
        root_id = resume.parent_version_id or resume.id
        
        # Get all versions
        return self.db.query(Resume).filter(
            (Resume.id == root_id) | (Resume.parent_version_id == root_id),
            Resume.is_deleted == False
        ).order_by(Resume.version).all()
