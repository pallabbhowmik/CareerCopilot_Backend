from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List

class Settings(BaseSettings):
    PROJECT_NAME: str = "CareerCopilot AI"
    API_V1_STR: str = "/api/v1"
    
    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "careercopilot"
    DATABASE_URL: Optional[str] = None

    # Security
    SECRET_KEY: str = "YOUR_SUPER_SECRET_KEY_CHANGE_IN_PROD"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]  # Allow all origins (configure specific origins in production)

    # AI
    OPENAI_API_KEY: Optional[str] = None

    # Supabase (Optional - for Auth/Storage)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    SUPABASE_JWT_SECRET: Optional[str] = None
    # Alias used elsewhere in the codebase (preferred name)
    SUPABASE_ANON_KEY: Optional[str] = None

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.DATABASE_URL:
            # Default local PostgreSQL connection
            self.DATABASE_URL = f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
        # Add SSL mode for Supabase if connecting to supabase.co
        if "supabase.co" in self.DATABASE_URL and "sslmode" not in self.DATABASE_URL:
            separator = "&" if "?" in self.DATABASE_URL else "?"
            self.DATABASE_URL = f"{self.DATABASE_URL}{separator}sslmode=require"

settings = Settings()
