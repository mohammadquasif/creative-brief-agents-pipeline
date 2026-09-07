"""Shared base for agents: each agent is a thin wrapper over a provider."""
from __future__ import annotations

from ..llm.base import LLMProvider


class BaseAgent:
    """An agent owns a provider and a single job in the pipeline."""

    role: str = "base"

    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    @property
    def name(self) -> str:
        return f"{self.role}Agent({self.provider.name})"

    def __repr__(self) -> str:  # nice logs / traces
        return self.name
