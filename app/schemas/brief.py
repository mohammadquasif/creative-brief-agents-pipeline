"""The validated creative brief — the contract between Agent 1 and Agent 2.

This schema *is* the validation gate: any dict produced by the Parser agent
must survive :meth:`CreativeBrief.model_validate` before the Generator is
allowed to see it.
"""
from __future__ import annotations

import re
from datetime import date
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class Tone(str, Enum):
    """Canonical brand tones. Synonyms in raw briefs are normalised here."""

    HYPE = "hype"
    LUXURY = "luxury"
    PLAYFUL = "playful"
    PROFESSIONAL = "professional"
    EMOTIONAL = "emotional"
    SUSTAINABLE = "sustainable"
    RETRO = "retro"
    MINIMAL = "minimal"
    EDGY = "edgy"


#: Informal phrases people write in briefs -> canonical tone.
#: Longer phrases must be checked first (we sort by length at use time).
TONE_SYNONYMS: dict[str, Tone] = {
    # hype
    "hype energy": Tone.HYPE,
    "hypebeast": Tone.HYPE,
    "hyped": Tone.HYPE,
    "energetic": Tone.HYPE,
    "exciting": Tone.HYPE,
    "excitement": Tone.HYPE,
    "streetwear": Tone.HYPE,
    "street": Tone.HYPE,
    "dope": Tone.HYPE,
    "fire": Tone.HYPE,
    "lit": Tone.HYPE,
    "buzz": Tone.HYPE,
    "hype": Tone.HYPE,
    # luxury
    "high end": Tone.LUXURY,
    "high-end": Tone.LUXURY,
    "luxury": Tone.LUXURY,
    "premium": Tone.LUXURY,
    "exclusive": Tone.LUXURY,
    "sophisticated": Tone.LUXURY,
    "elegant": Tone.LUXURY,
    "classy": Tone.LUXURY,
    "upscale": Tone.LUXURY,
    # playful
    "light hearted": Tone.PLAYFUL,
    "lighthearted": Tone.PLAYFUL,
    "playful": Tone.PLAYFUL,
    "fun": Tone.PLAYFUL,
    "quirky": Tone.PLAYFUL,
    "whimsical": Tone.PLAYFUL,
    "cheeky": Tone.PLAYFUL,
    "humorous": Tone.PLAYFUL,
    "humor": Tone.PLAYFUL,
    "funny": Tone.PLAYFUL,
    "cute": Tone.PLAYFUL,
    # professional
    "professional": Tone.PROFESSIONAL,
    "corporate": Tone.PROFESSIONAL,
    "business": Tone.PROFESSIONAL,
    "formal": Tone.PROFESSIONAL,
    "polished": Tone.PROFESSIONAL,
    "trustworthy": Tone.PROFESSIONAL,
    "credible": Tone.PROFESSIONAL,
    # emotional
    "emotional": Tone.EMOTIONAL,
    "heartfelt": Tone.EMOTIONAL,
    "heartwarming": Tone.EMOTIONAL,
    "inspiring": Tone.EMOTIONAL,
    "inspirational": Tone.EMOTIONAL,
    "moving": Tone.EMOTIONAL,
    "touching": Tone.EMOTIONAL,
    "warm": Tone.EMOTIONAL,
    "sentimental": Tone.EMOTIONAL,
    # sustainable
    "sustainable": Tone.SUSTAINABLE,
    "eco friendly": Tone.SUSTAINABLE,
    "eco-friendly": Tone.SUSTAINABLE,
    "environmentally": Tone.SUSTAINABLE,
    "eco": Tone.SUSTAINABLE,
    "green": Tone.SUSTAINABLE,
    "conscious": Tone.SUSTAINABLE,
    "organic": Tone.SUSTAINABLE,
    # retro
    "old school": Tone.RETRO,
    "old-school": Tone.RETRO,
    "retro": Tone.RETRO,
    "vintage": Tone.RETRO,
    "nostalgic": Tone.RETRO,
    "nostalgia": Tone.RETRO,
    "throwback": Tone.RETRO,
    "90s": Tone.RETRO,
    # minimal
    "minimalist": Tone.MINIMAL,
    "minimal": Tone.MINIMAL,
    "understated": Tone.MINIMAL,
    "simple": Tone.MINIMAL,
    # edgy
    "edgy": Tone.EDGY,
    "rebellious": Tone.EDGY,
    "disruptive": Tone.EDGY,
    "provocative": Tone.EDGY,
    "bold": Tone.EDGY,
    "raw": Tone.EDGY,
    "gritty": Tone.EDGY,
    "daring": Tone.EDGY,
}


class CreativeBrief(BaseModel):
    """Validated, structured representation of a creative brief."""

    campaign_name: str = Field(
        min_length=2, max_length=120, description="Short, human-friendly campaign title."
    )
    target_audience: str = Field(
        min_length=2, max_length=120, description="Who the creative is for."
    )
    key_message: str = Field(
        min_length=5, max_length=600, description="The core thing we want to communicate."
    )
    tone: Tone = Field(description="Canonical brand tone (synonyms auto-normalised).")
    deadline: date = Field(description="Date the campaign must be ready by (>= today).")

    # -- normalisers / business rules -------------------------------------
    @field_validator("tone", mode="before")
    @classmethod
    def _normalise_tone(cls, value: object) -> object:
        if isinstance(value, Tone):
            return value
        if not isinstance(value, str):
            raise ValueError("tone must be a string")
        token = value.strip().lower()
        for canonical in Tone:  # exact canonical values match fast
            if token == canonical.value:
                return canonical
        for phrase, canonical in sorted(
            TONE_SYNONYMS.items(), key=lambda kv: len(kv[0]), reverse=True
        ):
            if phrase in token:
                return canonical
        raise ValueError(
            f"tone {value!r} not recognised "
            f"(choose from {', '.join(t.value for t in Tone)})"
        )

    @field_validator("deadline")
    @classmethod
    def _deadline_must_be_actionable(cls, value: date) -> date:
        if value < date.today():
            raise ValueError(
                f"deadline {value.isoformat()} is in the past; "
                "it must be today or later"
            )
        return value

    @field_validator("campaign_name", "target_audience", "key_message")
    @classmethod
    def _normalise_text(cls, value: str) -> str:
        cleaned = re.sub(r"\s+", " ", value).strip()
        if not cleaned:
            raise ValueError("field must not be blank")
        return cleaned
