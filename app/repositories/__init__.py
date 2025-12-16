"""
Repository Layer

Abstracts data access from business logic.
All database operations go through repositories.
"""
from .base import BaseRepository
from .user import UserRepository
from .resume import ResumeRepository
from .job import JobRepository
from .analysis import AnalysisRepository

# Supabase repositories (new AI platform)
from .supabase_client import get_supabase, get_user_supabase, SupabaseClient
from .ai_repository import AIRepository
from .resume_repository import ResumeRepository as SupabaseResumeRepository

__all__ = [
    "BaseRepository",
    "UserRepository",
    "ResumeRepository",
    "JobRepository",
    "AnalysisRepository",
    # Supabase
    "get_supabase",
    "get_user_supabase",
    "SupabaseClient",
    "AIRepository",
    "SupabaseResumeRepository",
]
