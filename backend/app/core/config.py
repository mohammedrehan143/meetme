from pydantic_settings import BaseSettings
from typing import Optional, List
import os

class Settings(BaseSettings):
    APP_NAME: str = "MEETME"
    APP_ENV: str = os.getenv("APP_ENV", "production")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
    PORT: int = int(os.getenv("PORT", 8000))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    
    # Database (Supabase PostgreSQL / Asyncpg or local SQLite)
    DATABASE_URL: str = os.getenv("DATABASE_URL", os.getenv("SUPABASE_DB_URL", "sqlite+aiosqlite:///./meetme.db"))
    SUPABASE_URL: Optional[str] = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    SUPABASE_ANON_KEY: Optional[str] = os.getenv("SUPABASE_ANON_KEY", "")
    
    # CORS (Vercel Frontend URL support)
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")
    
    # AI Providers
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    GROQ_WHISPER_MODEL: str = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3")
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
    
    # Native Gmail SMTP Configuration
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    SMTP_EMAIL: str = os.getenv("SMTP_EMAIL", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "MEETME Autonomous Platform")
    SMTP_TIMEOUT: int = int(os.getenv("SMTP_TIMEOUT", 15))
    APP_FRONTEND_URL: str = os.getenv("APP_FRONTEND_URL", "http://localhost:3000")
    
    # Defaults
    DEFAULT_WORKSPACE_ID: str = "ws-demo-001"
    DEFAULT_USER_ID: str = "usr-alex-001"
    
    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
