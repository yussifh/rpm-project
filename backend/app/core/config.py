"""
Centralized application configuration.

Design decision: all environment-dependent values (secrets, DB URLs, CORS
origins) are read ONCE here via pydantic-settings and injected everywhere
else through the `settings` singleton. No module should call os.getenv()
directly — this keeps configuration a single source of truth and makes
testing (overriding settings) straightforward.
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- App metadata ---
    PROJECT_NAME: str = "AI-Integrated Remote Patient Monitoring System"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # --- Database ---
    DATABASE_URL: str

    # --- Redis ---
    REDIS_URL: str = "redis://redis:6379/0"

    # --- JWT / Security ---
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- CORS ---
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:5173"]

    # --- AI Health Assistant (LLM backend) ---
    # Unset in an environment with no network egress (e.g. this dev
    # sandbox) — the assistant endpoint returns 503 rather than crashing
    # when this is empty (see AssistantUnavailableError / assistant_service.py).
    ANTHROPIC_API_KEY: str | None = None
    ASSISTANT_MODEL: str = "claude-3-5-sonnet-20241022"
    ASSISTANT_MAX_TOKENS: int = 600

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings accessor.

    Using lru_cache means Settings() is constructed only once per process,
    avoiding repeated environment parsing while still being test-friendly
    (get_settings.cache_clear() can reset it in unit tests).
    """
    return Settings()


settings = get_settings()
