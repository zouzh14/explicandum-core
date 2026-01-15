import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    MAIL_DOMAIN: str = os.getenv("MAIL_DOMAIN", "explicandum.io")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./explicandum.db")

    class Config:
        env_file = ".env"


settings = Settings()
