"""
Job Repository

Data access layer for JobDescription entities.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.models import JobDescription
from app.repositories.base import BaseRepository


class JobRepository(BaseRepository[JobDescription]):
    """Repository for JobDescription entity operations"""
    
    def __init__(self, db: Session):
        super().__init__(db, JobDescription)
    
    # =========================================================================
    # JOB-SPECIFIC QUERIES
    # =========================================================================
    
    def get_by_user(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 50
    ) -> List[JobDescription]:
        """Get all job descriptions for a user"""
        return self.db.query(JobDescription).filter(
            JobDescription.user_id == user_id,
            JobDescription.is_deleted == False
        ).order_by(desc(JobDescription.updated_at)).offset(skip).limit(limit).all()
    
    def get_recent_for_user(
        self,
        user_id: int,
        limit: int = 10
    ) -> List[JobDescription]:
        """Get most recent job descriptions for a user"""
        return self.db.query(JobDescription).filter(
            JobDescription.user_id == user_id,
            JobDescription.is_deleted == False
        ).order_by(desc(JobDescription.created_at)).limit(limit).all()
    
    def get_by_company(
        self,
        user_id: int,
        company: str
    ) -> List[JobDescription]:
        """Get job descriptions by company name"""
        return self.db.query(JobDescription).filter(
            JobDescription.user_id == user_id,
            JobDescription.company.ilike(f"%{company}%"),
            JobDescription.is_deleted == False
        ).all()
    
    # =========================================================================
    # JOB CREATION
    # =========================================================================
    
    def create_job(
        self,
        user_id: int,
        title: str,
        company: str,
        raw_text: str,
        parsed_json: Optional[Dict[str, Any]] = None,
        url: Optional[str] = None,
        location: Optional[str] = None,
        salary_range: Optional[str] = None,
        job_type: Optional[str] = None
    ) -> JobDescription:
        """
        Create a new job description.
        
        Args:
            user_id: Owner user ID
            title: Job title
            company: Company name
            raw_text: Original job posting text
            parsed_json: Parsed structured data
            url: Job posting URL
            location: Job location
            salary_range: Salary range if available
            job_type: Full-time, Part-time, Contract, etc.
            
        Returns:
            Created JobDescription instance
        """
        job_data = {
            "user_id": user_id,
            "title": title,
            "company": company,
            "raw_text": raw_text,
            "parsed_json": parsed_json,
            "url": url,
            "location": location,
            "salary_range": salary_range,
            "job_type": job_type
        }
        return self.create(job_data)
    
    def create_or_update_from_url(
        self,
        user_id: int,
        url: str,
        job_data: Dict[str, Any]
    ) -> JobDescription:
        """
        Create or update a job description based on URL.
        
        If a job with the same URL exists for the user, update it.
        Otherwise, create a new one.
        """
        existing = self.db.query(JobDescription).filter(
            JobDescription.user_id == user_id,
            JobDescription.url == url,
            JobDescription.is_deleted == False
        ).first()
        
        if existing:
            for field, value in job_data.items():
                if hasattr(existing, field):
                    setattr(existing, field, value)
            existing.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(existing)
            return existing
        
        job_data["user_id"] = user_id
        job_data["url"] = url
        return self.create(job_data)
    
    # =========================================================================
    # SEARCH & FILTER
    # =========================================================================
    
    def search_jobs(
        self,
        user_id: int,
        query: str,
        skip: int = 0,
        limit: int = 20
    ) -> List[JobDescription]:
        """Search user's job descriptions"""
        search_pattern = f"%{query}%"
        return self.db.query(JobDescription).filter(
            JobDescription.user_id == user_id,
            JobDescription.is_deleted == False,
            (
                JobDescription.title.ilike(search_pattern) |
                JobDescription.company.ilike(search_pattern) |
                JobDescription.raw_text.ilike(search_pattern)
            )
        ).order_by(desc(JobDescription.updated_at)).offset(skip).limit(limit).all()
    
    def filter_by_criteria(
        self,
        user_id: int,
        job_type: Optional[str] = None,
        location: Optional[str] = None,
        company: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[JobDescription]:
        """Filter job descriptions by multiple criteria"""
        query = self.db.query(JobDescription).filter(
            JobDescription.user_id == user_id,
            JobDescription.is_deleted == False
        )
        
        if job_type:
            query = query.filter(JobDescription.job_type == job_type)
        
        if location:
            query = query.filter(JobDescription.location.ilike(f"%{location}%"))
        
        if company:
            query = query.filter(JobDescription.company.ilike(f"%{company}%"))
        
        return query.order_by(desc(JobDescription.updated_at)).offset(skip).limit(limit).all()
    
    def get_job_count(self, user_id: int) -> int:
        """Get total job description count for a user"""
        return self.db.query(func.count(JobDescription.id)).filter(
            JobDescription.user_id == user_id,
            JobDescription.is_deleted == False
        ).scalar() or 0
    
    # =========================================================================
    # SKILLS EXTRACTION
    # =========================================================================
    
    def get_skills_from_jobs(
        self,
        user_id: int,
        limit: int = 10
    ) -> List[str]:
        """
        Get aggregated skills from user's recent job descriptions.
        
        Useful for understanding what skills the user is targeting.
        """
        jobs = self.get_recent_for_user(user_id, limit)
        all_skills = []
        
        for job in jobs:
            if job.parsed_json and "required_skills" in job.parsed_json:
                all_skills.extend(job.parsed_json["required_skills"])
        
        # Return unique skills, most common first
        from collections import Counter
        skill_counts = Counter(all_skills)
        return [skill for skill, _ in skill_counts.most_common(50)]
    
    def get_common_requirements(
        self,
        user_id: int,
        limit: int = 10
    ) -> Dict[str, int]:
        """
        Get common requirements across user's target jobs.
        
        Returns frequency count of requirements.
        """
        jobs = self.get_recent_for_user(user_id, limit)
        requirements = []
        
        for job in jobs:
            if job.parsed_json and "requirements" in job.parsed_json:
                for req in job.parsed_json["requirements"]:
                    if isinstance(req, dict):
                        requirements.append(req.get("text", ""))
                    else:
                        requirements.append(str(req))
        
        from collections import Counter
        return dict(Counter(requirements).most_common(20))
