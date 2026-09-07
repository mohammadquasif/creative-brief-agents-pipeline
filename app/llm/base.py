"""Provider interface used by Agent 1 (Parser) and Agent 2 (Generator)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..schemas.brief import CreativeBrief
from ..schemas.validation import ValidationIssue


class LLMProvider(ABC):
    """Minimal contract a 'brain' must fulfil.

    The parser returns *plain dicts* of field -> value, deliberately omitting
    anything it is not confident about. The surrounding validation layer then
    decides what is acceptable (retry / fallback / explicit error).
    """

    name: str = "base"

    @abstractmethod
    def parse_brief(
        self,
        raw_brief: str,
        *,
        issues: list[ValidationIssue] | None = None,
    ) -> dict[str, Any]:
        """Extract structured brief fields from raw text.

        ``issues`` lists field-level problems from the previous validation
        attempt, so the provider can re-run focusing only on fixing those
        (this is the *retry* mechanism).
        """

    @abstractmethod
    def generate_creative(self, brief: CreativeBrief) -> dict[str, Any]:
        """Return a CreativeOutput-shaped dict for a *validated* brief."""

    def describe(self) -> str:
        return self.name
