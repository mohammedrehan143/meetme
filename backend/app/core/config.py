from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    APP_NAME: str = "MEETME"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./meetme.db"
    SUPABASE_URL: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    
    # AI Providers
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_WHISPER_MODEL: str = "whisper-large-v3"
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = "gemini-1.5-pro"
    
    # Email Provider
    RESEND_API_KEY: Optional[str] = os.getenv("RESEND_API_KEY", "")
    RESEND_FROM_EMAIL: str = "MEETME <onboarding@resend.dev>"
    
    # Defaults
    DEFAULT_WORKSPACE_ID: str = "ws-demo-001"
    DEFAULT_USER_ID: str = "usr-alex-001"
    
    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
