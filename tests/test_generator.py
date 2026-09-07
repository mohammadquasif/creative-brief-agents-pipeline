"""Agent 2 (Generator) only ever sees schema-valid briefs."""
from __future__ import annotations

from datetime import date, timedelta

from app.schemas.brief import CreativeBrief
from app.schemas.generation import CreativeOutput


def _brief(**overrides) -> CreativeBrief:
    base = dict(
        campaign_name="Sneaker Drop Campaign",
        target_audience="Gen Z",
        key_message="The sneaker drop is live — get yours before it's gone.",
        tone="hype",
        deadline=date.today() + timedelta(days=7),
    )
    base.update(overrides)
    return CreativeBrief(**base)


def test_generator_produces_full_creative_output(generator) -> None:
    out = generator.generate(_brief())

    assert isinstance(out, CreativeOutput)
    assert out.ad_concept.strip()
    assert out.social_caption.strip()
    assert out.hashtags
    assert all(tag.startswith("#") for tag in out.hashtags)


def test_generator_tone_is_reflected(generator) -> None:
    hype = generator.generate(_brief())
    luxury = generator.generate(
        _brief(
            campaign_name="Aurelle Fragrance Launch",
            target_audience="Affluent professionals",
            tone="luxury",
            key_message="Introducing Aurelle — quietly refined.",
        )
    )
    assert hype.ad_concept != luxury.ad_concept
    assert luxury.hashtags  # tone-aware hashtags present
