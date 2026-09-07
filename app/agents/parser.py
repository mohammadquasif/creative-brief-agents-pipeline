"""Agent 1 — Parser.

Job: turn a raw, unstructured brief (a paragraph of text) into a structured
field dict. It does **not** guarantee a valid result — the validation layer
is responsible for that. This agent just knows how to extract and how to
"re-try" given the specific fields that failed validation.
"""
from __future__ import annotations

from typing import Any

from ..schemas.validation import ValidationIssue
from .base import BaseAgent


class ParserAgent(BaseAgent):
    """Agent 1 — structured field extraction from messy text."""

    role = "Parser"

    def parse(self, raw_brief: str) -> dict[str, Any]:
        """First extraction pass over the raw brief."""
        return self.provider.parse_brief(raw_brief)

    def repair(
        self,
        raw_brief: str,
        issues: list[ValidationIssue],
    ) -> dict[str, Any]:
        """Targeted re-extraction pass focusing only on the broken fields."""
        return self.provider.parse_brief(raw_brief, issues=issues)
