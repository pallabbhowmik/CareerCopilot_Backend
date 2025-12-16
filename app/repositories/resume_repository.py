"""
Resume Repository - Data access layer for resume operations
Handles resumes, versions, sections, bullets, skills
"""

from typing import Dict, List, Optional, Any
from uuid import UUID
from supabase import Client

from .supabase_client import get_supabase


class ResumeRepository:
    """Repository for resume operations"""
    
    def __init__(self, client: Optional[Client] = None):
        """
        Initialize resume repository
        
        Args:
            client: Optional Supabase client (uses service role by default)
        """
        self.client = client or get_supabase()
    
    # =====================================================
    # RESUMES
    # =====================================================
    
    def get_user_resumes(self, user_id: UUID) -> List[Dict[str, Any]]:
        """Get all active resumes for a user"""
        response = self.client.table("resumes") \
            .select("*") \
            .eq("user_id", str(user_id)) \
            .is_("deleted_at", "null") \
            .order("updated_at", desc=True) \
            .execute()
        
        return response.data or []
    
    def get_resume(self, resume_id: UUID) -> Optional[Dict[str, Any]]:
        """Get resume by ID"""
        response = self.client.table("resumes") \
            .select("*") \
            .eq("id", str(resume_id)) \
            .is_("deleted_at", "null") \
            .single() \
            .execute()
        
        return response.data if response.data else None
    
    def create_resume(
        self,
        user_id: UUID,
        name: str,
        is_active: bool = True
    ) -> UUID:
        """
        Create new resume
        
        Returns:
            Resume ID
        """
        response = self.client.table("resumes") \
            .insert({
                "user_id": str(user_id),
                "name": name,
                "is_active": is_active
            }) \
            .execute()
        
        return UUID(response.data[0]["id"])
    
    def update_resume(
        self,
        resume_id: UUID,
        name: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> None:
        """Update resume metadata"""
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if is_active is not None:
            update_data["is_active"] = is_active
        
        if update_data:
            self.client.table("resumes") \
                .update(update_data) \
                .eq("id", str(resume_id)) \
                .execute()
    
    def soft_delete_resume(self, resume_id: UUID) -> None:
        """Soft delete resume"""
        self.client.table("resumes") \
            .update({"deleted_at": "now()"}) \
            .eq("id", str(resume_id)) \
            .execute()
    
    # =====================================================
    # RESUME VERSIONS
    # =====================================================
    
    def get_current_version(self, resume_id: UUID) -> Optional[Dict[str, Any]]:
        """Get current (latest) version of a resume"""
        response = self.client.table("resume_versions") \
            .select("*") \
            .eq("resume_id", str(resume_id)) \
            .order("version_number", desc=True) \
            .limit(1) \
            .execute()
        
        return response.data[0] if response.data else None
    
    def get_version(self, version_id: UUID) -> Optional[Dict[str, Any]]:
        """Get specific resume version"""
        response = self.client.table("resume_versions") \
            .select("*") \
            .eq("id", str(version_id)) \
            .single() \
            .execute()
        
        return response.data if response.data else None
    
    def create_version(
        self,
        resume_id: UUID,
        version_number: int,
        contact_info: Dict[str, Any],
        summary: Optional[str] = None,
        ats_score: Optional[float] = None,
        match_percentage: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UUID:
        """
        Create new resume version
        
        Returns:
            Version ID
        """
        response = self.client.table("resume_versions") \
            .insert({
                "resume_id": str(resume_id),
                "version_number": version_number,
                "contact_info": contact_info,
                "summary": summary,
                "ats_score": ats_score,
                "match_percentage": match_percentage,
                "metadata": metadata or {}
            }) \
            .execute()
        
        return UUID(response.data[0]["id"])
    
    def list_versions(self, resume_id: UUID) -> List[Dict[str, Any]]:
        """List all versions of a resume"""
        response = self.client.table("resume_versions") \
            .select("*") \
            .eq("resume_id", str(resume_id)) \
            .order("version_number", desc=True) \
            .execute()
        
        return response.data or []
    
    # =====================================================
    # RESUME SECTIONS
    # =====================================================
    
    def get_version_sections(self, version_id: UUID) -> List[Dict[str, Any]]:
        """Get all sections for a resume version"""
        response = self.client.table("resume_sections") \
            .select("*, resume_bullets(*)") \
            .eq("resume_version_id", str(version_id)) \
            .order("section_order") \
            .execute()
        
        return response.data or []
    
    def create_section(
        self,
        resume_version_id: UUID,
        section_type: str,
        section_order: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UUID:
        """
        Create resume section
        
        Args:
            section_type: 'experience', 'education', 'skills', 'projects', 'custom'
        
        Returns:
            Section ID
        """
        response = self.client.table("resume_sections") \
            .insert({
                "resume_version_id": str(resume_version_id),
                "section_type": section_type,
                "section_order": section_order,
                "metadata": metadata or {}
            }) \
            .execute()
        
        return UUID(response.data[0]["id"])
    
    # =====================================================
    # RESUME BULLETS
    # =====================================================
    
    def create_bullet(
        self,
        section_id: UUID,
        bullet_text: str,
        bullet_order: int,
        signals: Optional[List[str]] = None,
        ai_generated: bool = False,
        ai_response_id: Optional[UUID] = None
    ) -> UUID:
        """
        Create resume bullet point
        
        Returns:
            Bullet ID
        """
        response = self.client.table("resume_bullets") \
            .insert({
                "section_id": str(section_id),
                "bullet_text": bullet_text,
                "bullet_order": bullet_order,
                "signals": signals or [],
                "ai_generated": ai_generated,
                "ai_response_id": str(ai_response_id) if ai_response_id else None
            }) \
            .execute()
        
        return UUID(response.data[0]["id"])
    
    def update_bullet(
        self,
        bullet_id: UUID,
        bullet_text: Optional[str] = None,
        bullet_order: Optional[int] = None,
        signals: Optional[List[str]] = None
    ) -> None:
        """Update bullet point"""
        update_data = {}
        if bullet_text is not None:
            update_data["bullet_text"] = bullet_text
        if bullet_order is not None:
            update_data["bullet_order"] = bullet_order
        if signals is not None:
            update_data["signals"] = signals
        
        if update_data:
            self.client.table("resume_bullets") \
                .update(update_data) \
                .eq("id", str(bullet_id)) \
                .execute()
    
    # =====================================================
    # SKILLS
    # =====================================================
    
    def get_resume_skills(self, version_id: UUID) -> List[Dict[str, Any]]:
        """Get all skills for a resume version"""
        response = self.client.table("resume_skills") \
            .select("*, skills(*)") \
            .eq("resume_version_id", str(version_id)) \
            .execute()
        
        return response.data or []
    
    def add_skill_to_resume(
        self,
        resume_version_id: UUID,
        skill_id: UUID,
        proficiency_level: int,
        evidence_count: int = 0
    ) -> UUID:
        """Link skill to resume version"""
        response = self.client.table("resume_skills") \
            .insert({
                "resume_version_id": str(resume_version_id),
                "skill_id": str(skill_id),
                "proficiency_level": proficiency_level,
                "evidence_count": evidence_count
            }) \
            .execute()
        
        return UUID(response.data[0]["id"])
    
    def search_skills(
        self, 
        query: str,
        category: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search skills by name
        
        Args:
            query: Search term
            category: Optional category filter
            limit: Maximum results
        
        Returns:
            List of matching skills
        """
        q = self.client.table("skills") \
            .select("*") \
            .ilike("name", f"%{query}%")
        
        if category:
            q = q.eq("category", category)
        
        response = q.limit(limit).execute()
        return response.data or []
    
    # =====================================================
    # FULL RESUME WITH RELATIONSHIPS
    # =====================================================
    
    def get_full_resume(self, resume_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get complete resume with all nested data
        Uses materialized view for performance
        """
        response = self.client.table("current_resumes") \
            .select("*") \
            .eq("resume_id", str(resume_id)) \
            .single() \
            .execute()
        
        return response.data if response.data else None
    
    def get_resume_with_job_match(
        self,
        user_id: UUID,
        job_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get resume with job matching analysis
        Uses RPC for complex join
        """
        response = self.client.rpc(
            "get_resume_with_job_match",
            {
                "p_user_id": str(user_id),
                "p_job_id": str(job_id)
            }
        ).execute()
        
        return response.data[0] if response.data else None
    
    def calculate_ats_score(
        self,
        resume_version_id: UUID,
        job_id: UUID
    ) -> float:
        """Calculate ATS score using deterministic algorithm"""
        response = self.client.rpc(
            "calculate_ats_score",
            {
                "p_resume_version_id": str(resume_version_id),
                "p_job_id": str(job_id)
            }
        ).execute()
        
        return float(response.data) if response.data else 0.0
