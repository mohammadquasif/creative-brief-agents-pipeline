"""Shared fixtures for tests (all use the deterministic 'local' provider)."""
from __future__ import annotations

import pytest

from app.agents.generator import GeneratorAgent
from app.agents.parser import ParserAgent
from app.llm.local import LocalHeuristicProvider
from app.services.validation import ValidationService

#: The sample brief from the brief.
SAMPLE_BRIEF = (
    "Need something for the new sneaker drop targeting gen z, "
    "kinda hype energy, has to be ready by friday."
)


@pytest.fixture
def parser() -> ParserAgent:
    return ParserAgent(LocalHeuristicProvider())


@pytest.fixture
def generator() -> GeneratorAgent:
    return GeneratorAgent(LocalHeuristicProvider())


@pytest.fixture
def validator() -> ValidationService:
    return ValidationService(max_attempts=3)
