"""Build the right provider from configuration."""
from __future__ import annotations

from ..core.config import Settings
from ..core.exceptions import ProviderError
from .base import LLMProvider


def get_provider(settings: Settings) -> LLMProvider:
    """Instantiate the configured provider (``local`` by default)."""
    name = settings.llm_provider

    if name == "local":
        from .local import LocalHeuristicProvider

        return LocalHeuristicProvider()

    if name == "openai":
        if not settings.openai_api_key:
            raise ProviderError(
                "LLM_PROVIDER=openai but OPENAI_API_KEY is not set "
                "(see .env.example)"
            )
        from .openai_provider import OpenAIProvider

        return OpenAIProvider(api_key=settings.openai_api_key, model=settings.openai_model)

    raise ProviderError(
        f"Unknown LLM_PROVIDER {name!r}. Choose from: 'local', 'openai'."
    )
