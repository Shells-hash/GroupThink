from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    secret_key: str = "dev-secret-change-in-production"
    anthropic_api_key: str = ""
    database_url: str = "sqlite:///./groupthink.db"
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 7
    ai_context_window: int = 20

    # Gmail — used for sending password reset emails
    gmail_user: str = ""
    gmail_app_password: str = ""

    # Google OAuth — from Google Cloud Console
    google_client_id: str = ""
    google_client_secret: str = ""

    # Public base URL — used to build reset links in emails
    base_url: str = "http://localhost:8000"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
