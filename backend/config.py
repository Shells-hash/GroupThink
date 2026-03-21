from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    secret_key: str = "dev-secret-change-in-production"
    database_url: str = "sqlite:///./groupthink.db"
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 7
    ai_context_window: int = 20

    # ── AI Provider ──────────────────────────────────────────────────────────
    # Options: "anthropic" | "groq" | "together" | "ollama"
    model_provider: str = "anthropic"

    # Anthropic (Claude)
    anthropic_api_key: str = ""

    # Groq (Llama via groq.com — free tier available)
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_fast_model: str = "llama-3.1-8b-instant"

    # Together AI (Llama 405B etc.)
    together_api_key: str = ""
    together_model: str = "meta-llama/Llama-3.3-70B-Instruct-Turbo"
    together_fast_model: str = "meta-llama/Llama-3.1-8B-Instruct-Turbo"

    # Ollama (local — run `ollama pull llama3.2` first)
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "llama3.2"

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
