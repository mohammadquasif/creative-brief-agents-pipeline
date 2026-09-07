"""Agent 1 (Parser) behaviour against the local heuristic provider."""
from __future__ import annotations

from datetime import date, timedelta

from tests.conftest import SAMPLE_BRIEF


def test_parser_extracts_all_fields_from_sample(parser) -> None:
    data = parser.parse(SAMPLE_BRIEF)

    assert data["campaign_name"] == "Sneaker Drop Campaign"
    assert data["target_audience"] == "Gen Z"
    assert data["tone"] == "hype"
    assert len(data["key_message"]) >= 5
    assert "deadline" in data  # ISO string


def test_parser_resolves_relative_friday_deadline(parser) -> None:
    data = parser.parse(SAMPLE_BRIEF)
    deadline = date.fromisoformat(data["deadline"])

    assert deadline > date.today()
    assert deadline.weekday() == 4  # Friday


def test_parser_resolves_tomorrow_and_explicit_dates(parser) -> None:
    assert date.fromisoformat(
        parser.parse("Launch ad, deadline tomorrow.")["deadline"]
    ) == date.today() + timedelta(days=1)

    explicit = (date.today() + timedelta(days=30)).isoformat()
    parsed = parser.parse(f"New coffee ad ready by {explicit}.")
    assert parsed["deadline"] == explicit


def test_parser_maps_tone_synonyms(parser) -> None:
    assert parser.parse("Make it feel premium and high end.")["tone"] == "luxury"
    assert parser.parse("Keep it playful and fun.")["tone"] == "playful"


def test_parser_leaves_missing_fields_out(parser) -> None:
    # No product, audience, tone or date -> nothing confident to report.
    data = parser.parse("blah blah random filler nothing useful at all")
    assert data == {}
