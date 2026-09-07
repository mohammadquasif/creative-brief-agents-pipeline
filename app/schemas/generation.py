"""Request / response contracts for the public API."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .brief import CreativeBrief


class GenerationRequest(BaseModel):
    """What a caller sends: one messy paragraph of brief."""

    raw_brief: str = Field(
        min_length=5,
        max_length=5000,
        description="Raw, unstructured creative brief text.",
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional extra business context (reserved for future use).",
    )


class CreativeOutput(BaseModel):
    """What Agent 2 produces from a validated brief."""

    ad_concept: str = Field(min_length=1, description="One-line ad concept.")
    social_caption: str = Field(min_length=1, description="Ready-to-post social caption.")
    hashtags: list[str] = Field(default_factory=list, description="Suggested hashtags.")


class RunMeta(BaseModel):
    """Transparent audit trail of how a run was validated."""

    provider: str = Field(description="Which 'brain' powered the agents.")
    validation_attempts: int = Field(default=1, description="How many validation passes ran.")
    repair_passes: int = Field(default=0, description="How many Agent-1 repair retries ran.")
    fallbacks_applied: list[str] = Field(
        default_factory=list,
        description="Which safe defaults were applied (explicit, never silent).",
    )


class GenerationResponse(BaseModel):
    """Successful response: validated brief + creative output + audit meta."""

    validated_brief: CreativeBrief
    creative: CreativeOutput
    meta: RunMeta
