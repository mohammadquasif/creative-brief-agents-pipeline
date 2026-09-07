"""Types describing validation problems (used for explicit error surfacing)."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ValidationIssue(BaseModel):
    """One field-level problem found while validating a structured brief."""

    field: str = Field(description="Schema field (or '*' when the payload is unusable).")
    message: str = Field(description="Human-readable explanation.")
    value: Any | None = Field(default=None, description="The offending input, if any.")

    @property
    def human(self) -> str:
        return f"{self.field}: {self.message}"
