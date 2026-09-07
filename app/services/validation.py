"""The validation gate between Agent 1 and Agent 2.

This is where the requirement "don't let bad data silently flow through" is
enforced. The strategy is an explicit escalation ladder:

    1. VALIDATE   -> try to coerce the Parser's output into CreativeBrief
    2. RETRY      -> if it fails, ask the Parser to re-extract (repair pass),
                     feeding it the exact field-level errors it made.
    3. FALLBACK   -> if retries are exhausted, apply *safe, recorded* defaults
                     for non-critical gaps (each is tracked so it is never
                     silent).
    4. SURFACE    -> if it is STILL invalid (e.g. no usable deadline), return
                     a ValidationResult with the concrete issues so the caller
                     can return a clear error instead of forwarding bad data.

We never fabricate business-critical facts (like a deadline). Missing critical
fields fail loudly.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from pydantic import ValidationError
from pydantic_core import PydanticUndefined

from ..agents.parser import ParserAgent
from ..schemas.brief import CreativeBrief, Tone
from ..schemas.validation import ValidationIssue

logger = logging.getLogger(__name__)

#: Safe defaults applied ONLY as a last-resort fallback (all recorded).
_FALLBACKS: dict[str, str] = {
    "tone": Tone.PROFESSIONAL.value,
    "target_audience": "General consumers",
    "campaign_name": "Untitled Campaign",
    "key_message": "Something fresh is on the way — stay tuned.",
}


@dataclass
class ValidationResult:
    """Outcome of running a parsed brief through the validation gate."""

    valid: bool
    brief: CreativeBrief | None
    issues: list[ValidationIssue]
    attempts: int = 1
    repair_passes: int = 0
    fallbacks_applied: list[str] = field(default_factory=list)


class ValidationService:
    """Runs Parser output through validate -> retry -> fallback -> verdict."""

    def __init__(
        self,
        *,
        brief_model: type[CreativeBrief] = CreativeBrief,
        max_attempts: int = 3,
    ) -> None:
        self.brief_model = brief_model
        self.max_attempts = max(1, max_attempts)  # first parse counts as attempt 1

    # ------------------------------------------------------------------ #
    def run(
        self,
        raw_brief: str,
        parsed: dict,
        parser: ParserAgent,
    ) -> ValidationResult:
        """Validate ``parsed``; orchestrate repair + fallback as needed."""
        attempts, repair_passes = 1, 0
        issues = self._issues_for(parsed)

        # --- RETRY: give the parser up to (max_attempts - 1) repair passes.
        # Repair MERGES over the previous result: fields that were already
        # extracted correctly are kept, and only the broken fields are re-derived.
        while issues and attempts < self.max_attempts:
            repaired = parser.repair(raw_brief, issues)
            attempts += 1
            repair_passes += 1
            merged = {**parsed, **repaired}
            if merged == parsed:  # no progress -> retrying won't help
                parsed = merged
                break
            parsed = merged
            issues = self._issues_for(parsed)

        # --- FALLBACK: apply recorded safe defaults for any remaining gaps.
        fallbacks: list[str] = []
        if issues:
            parsed, fallbacks = self._apply_defaults(parsed)
            attempts += 1
            issues = self._issues_for(parsed)

        if issues:
            logger.warning(
                "Validation failed after %d attempt(s): %s",
                attempts,
                "; ".join(i.human for i in issues),
            )
            return ValidationResult(
                valid=False,
                brief=None,
                issues=issues,
                attempts=attempts,
                repair_passes=repair_passes,
                fallbacks_applied=fallbacks,
            )

        brief = self.brief_model.model_validate(parsed)
        return ValidationResult(
            valid=True,
            brief=brief,
            issues=[],
            attempts=attempts,
            repair_passes=repair_passes,
            fallbacks_applied=fallbacks,
        )

    # ------------------------------------------------------------------ #
    def _issues_for(self, data: dict) -> list[ValidationIssue]:
        """Coerce ``data`` into the schema; flatten failures into issues."""
        if not data:
            return [
                ValidationIssue(
                    field="*",
                    message="Parser returned no structured data at all.",
                )
            ]
        try:
            self.brief_model.model_validate(data)
            return []
        except ValidationError as exc:
            issues: list[ValidationIssue] = []
            for err in exc.errors():
                loc = err.get("loc") or ()
                field_name = ".".join(str(part) for part in loc) or "*"
                raw_input = err.get("input")
                # Never let Pydantic's internal Undefined sentinel reach the API.
                if raw_input is None or raw_input is PydanticUndefined:
                    raw_input = None
                issues.append(
                    ValidationIssue(
                        field=field_name,
                        message=err.get("msg", "invalid value"),
                        value=raw_input,
                    )
                )
            return issues

    # ------------------------------------------------------------------ #
    @staticmethod
    def _apply_defaults(data: dict) -> tuple[dict, list[str]]:
        """Fill missing/empty non-critical fields with recorded defaults.

        ``deadline`` is intentionally NOT defaulted: inventing a business
        deadline would be dangerous, so its absence is surfaced as an error.
        """
        applied: list[str] = []
        out = dict(data)

        for field_name, default in _FALLBACKS.items():
            current = out.get(field_name)
            usable = isinstance(current, str) and len(current.strip()) >= 2
            if not usable:
                out[field_name] = default
                applied.append(f"{field_name} defaulted to {default!r}")

        return out, applied
