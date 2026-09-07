"""Application settings, loaded from environment / .env file."""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    """Immutable settings snapshot for the service."""

    app_name: str = "Creative Brief Agent Pipeline"
    llm_provider: str = os.getenv("LLM_PROVIDER", "local").strip().lower()
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY") or None
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    parser_retries: int = int(os.getenv("PARSER_RETRIES", "2"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (cheap & process-wide singleton)."""
    return Settings()
