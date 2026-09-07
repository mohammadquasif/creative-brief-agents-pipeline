"""Agent 2 — Generator.

Job: take a **validated** :class:`CreativeBrief` and produce short creative
output (ad concept + social caption + hashtags).

Guarantee: this agent only ever receives data that survived the validation
gate, so it can never accidentally build on a malformed or half-baked brief.
"""
from __future__ import annotations

from ..schemas.brief import CreativeBrief
from ..schemas.generation import CreativeOutput
from .base import BaseAgent


class GeneratorAgent(BaseAgent):
    """Agent 2 — creative output generation from a validated brief."""

    role = "Generator"

    def generate(self, brief: CreativeBrief) -> CreativeOutput:
        """Create the creative output and re-validate it into a schema object."""
        data = self.provider.generate_creative(brief)
        return CreativeOutput.model_validate(data)
