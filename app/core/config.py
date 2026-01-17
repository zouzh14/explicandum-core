import os
import secrets
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    # JWT Configuration - SECURITY: SECRET_KEY must be set in production
    SECRET_KEY: str = Field(
        ..., description="JWT secret key - must be set in production environment"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # API Keys
    GEMINI_API_KEY: str = Field(..., description="Google Gemini API key")
    DEEPSEEK_API_KEY: str = Field(default="", description="DeepSeek API key")
    RESEND_API_KEY: str = Field(default="", description="Resend email service API key")

    # Configuration
    MAIL_DOMAIN: str = Field(
        default="explicandum.io", description="Mail domain for verification emails"
    )
    DATABASE_URL: str = Field(
        default="sqlite:///./explicandum.db", description="Database connection URL"
    )
    SKIP_EMAIL_SENDING: bool = Field(
        default=False, description="Skip actual email sending in development"
    )

    # Security Settings
    RATE_LIMIT_PER_MINUTE: int = Field(
        default=60, description="API rate limit per minute"
    )
    MAX_LOGIN_ATTEMPTS: int = Field(
        default=5, description="Maximum login attempts before lockout"
    )
    ACCOUNT_LOCKOUT_MINUTES: int = Field(
        default=15, description="Account lockout duration in minutes"
    )

    @validator("SECRET_KEY")
    def validate_secret_key(cls, v):
        if not v or v == "your-secret-key-for-jwt-change-it-in-prod":
            raise ValueError(
                "SECURITY: SECRET_KEY must be set to a secure value. "
                "Generate one with: python3 -c \"import secrets; print('SECRET_KEY=\\\"' + secrets.token_urlsafe(32) + '\\\"')\""
            )
        if len(v) < 32:
            raise ValueError(
                "SECRET_KEY must be at least 32 characters long for security"
            )
        return v

    @validator("GEMINI_API_KEY")
    def validate_gemini_key(cls, v):
        if not v or v == "your_gemini_api_key_here":
            raise ValueError("GEMINI_API_KEY must be set to a valid API key")
        return v

    class Config:
        env_file = ".env"


settings = Settings()
