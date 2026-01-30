"""
Configuration management for the Voice AI Diagnostic Agent.
Loads settings from environment variables with sensible defaults.
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = "SEARS Voice AI Diagnostic Agent"
    debug: bool = False
    environment: str = "development"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    base_url: str = "http://localhost:8000"
    
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/sears_voice_ai"
    
    # Twilio
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    
    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_realtime_model: str = "gpt-4o-realtime-preview"
    openai_voice: str = "alloy"  # Options: alloy, echo, fable, onyx, nova, shimmer
    
    # SendGrid (for email)
    sendgrid_api_key: str = ""
    sendgrid_from_email: str = "noreply@searshomeservices.com"
    
    # Image Upload
    upload_url_expiry_hours: int = 24
    max_image_size_mb: int = 10
    
    # Redis (for session management)
    redis_url: str = "redis://localhost:6379"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience access
settings = get_settings()
