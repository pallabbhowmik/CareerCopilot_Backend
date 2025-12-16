"""
Supabase Client Configuration
Manages connection pooling and client initialization
"""

import os
from typing import Optional
from supabase import create_client, Client
from functools import lru_cache

class SupabaseClient:
    """Singleton Supabase client with service role access"""
    
    _instance: Optional[Client] = None
    
    @classmethod
    @lru_cache(maxsize=1)
    def get_client(cls) -> Client:
        """
        Get or create Supabase client with service role key.
        Service role bypasses RLS - use carefully!
        """
        if cls._instance is None:
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            
            if not supabase_url or not supabase_key:
                raise ValueError(
                    "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set. "
                    "Service role key is required for AI Orchestrator to bypass RLS."
                )
            
            cls._instance = create_client(supabase_url, supabase_key)
        
        return cls._instance
    
    @classmethod
    def get_user_client(cls, user_token: str) -> Client:
        """
        Get Supabase client authenticated as specific user.
        This client respects RLS policies.
        
        Args:
            user_token: JWT token from Supabase Auth
        
        Returns:
            User-authenticated Supabase client
        """
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
        
        if not supabase_url or not supabase_anon_key:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")
        
        client = create_client(supabase_url, supabase_anon_key)
        client.auth.set_session(user_token, user_token)  # Set user context
        return client


# Convenience function for service role access
def get_supabase() -> Client:
    """Get service role Supabase client (bypasses RLS)"""
    return SupabaseClient.get_client()


# Convenience function for user-scoped access
def get_user_supabase(user_token: str) -> Client:
    """Get user-authenticated Supabase client (respects RLS)"""
    return SupabaseClient.get_user_client(user_token)
