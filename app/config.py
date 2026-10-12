from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BASE_DIR / "instance" / "smart_banking_training.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4o-mini"
    llm_provider: str = "openrouter"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    app_secret_key: str = ""
    banking_api_token: str = ""
    banking_api_url: str = "http://127.0.0.1:8000"
    database_url: str = f"sqlite:///{DEFAULT_DB_PATH.as_posix()}"
    confirmation_expiry_minutes: int = Field(default=10, gt=0)
    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = Field(default=8000, gt=0, le=65535)
    log_level: str = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


def reload_settings() -> Settings:
    get_settings.cache_clear()
    global settings
    settings = get_settings()
    return settings
