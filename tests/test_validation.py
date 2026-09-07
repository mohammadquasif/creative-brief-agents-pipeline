"""The validation gate: retry -> fallback -> explicit error."""
from __future__ import annotations

from datetime import date, timedelta

from tests.conftest import SAMPLE_BRIEF


def _run(validator, parser, raw_brief: str):
    parsed = parser.parse(raw_brief)
    return validator.run(raw_brief, parsed, parser)


def test_sample_brief_passes_first_attempt(validator, parser) -> None:
    result = _run(validator, parser, SAMPLE_BRIEF)

    assert result.valid is True
    assert result.brief is not None
    assert result.attempts == 1
    assert result.repair_passes == 0
    assert result.fallbacks_applied == []


def test_missing_tone_and_audience_are_filled_by_fallback(validator, parser) -> None:
    future = (date.today() + timedelta(days=60)).isoformat()
    raw = f"Need an ad for the perfume launch by {future}."

    result = _run(validator, parser, raw)

    assert result.valid is True
    assert result.brief is not None
    assert result.brief.tone.value == "professional"  # safe default
    assert result.brief.target_audience == "General consumers"
    assert result.fallbacks_applied  # recorded, never silent
    assert any("tone defaulted" in note for note in result.fallbacks_applied)


def test_unusable_brief_surfaces_clear_error(validator, parser) -> None:
    result = _run(validator, parser, "blah blah random filler nothing useful at all")

    assert result.valid is False
    assert result.brief is None
    assert result.issues  # concrete, machine-readable issues
    assert any(issue.field == "deadline" for issue in result.issues)


def test_past_deadline_is_rejected(validator, parser) -> None:
    past = (date.today() - timedelta(days=5)).isoformat()
    raw = f"Fragrance campaign by {past}, tone luxury."

    result = _run(validator, parser, raw)

    # Repair can't make yesterday become tomorrow -> explicit failure.
    assert result.valid is False
    assert any(issue.field == "deadline" for issue in result.issues)
