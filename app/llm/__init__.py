"""Swappable 'brain' for the agents.

Both agents talk to an :class:`LLMProvider`, never to a concrete SDK. That is
what lets the exact same validation/retry logic run against a deterministic
local heuristic *or* a real hosted model.
"""
from .base import LLMProvider
from .factory import get_provider

__all__ = ["LLMProvider", "get_provider"]
