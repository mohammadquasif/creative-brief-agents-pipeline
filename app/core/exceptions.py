"""Domain exceptions raised inside the pipeline.

These are *explicit* error signals: nothing invalid ever silently flows
from Agent 1 to Agent 2.
"""
from __future__ import annotations

from ..schemas.validation import ValidationIssue


class BriefPipelineError(Exception):
    """Base class for all pipeline errors."""


class InvalidBriefError(BriefPipelineError):
    """Raised when Agent 1's output could not be validated.

    Happens only after every allowed repair attempt AND the fallback pass
    have been tried. Carries the machine-readable issues for the API to
    surface as a clear 422 response.
    """

    def __init__(
        self,
        *,
        issues: list[ValidationIssue],
        attempts: int,
        fallbacks_applied: list[str],
        raw_brief: str,
    ) -> None:
        self.issues = issues
        self.attempts = attempts
        self.fallbacks_applied = fallbacks_applied
        self.raw_brief = raw_brief
        super().__init__(self.summary)

    @property
    def summary(self) -> str:
        details = "; ".join(issue.human for issue in self.issues)
        return (
            f"Brief could not be validated after {self.attempts} attempt(s). "
            f"Refusing to pass bad data to the generator. Details: {details}"
        )


class ProviderError(BriefPipelineError):
    """Wraps failures from the underlying LLM / text provider."""
