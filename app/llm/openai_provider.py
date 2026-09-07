"""Optional OpenAI-backed provider.

Only active when ``LLM_PROVIDER=openai`` (and ``OPENAI_API_KEY`` is set).
Requires the optional dependency: ``pip install -r requirements-optional.txt``.

The parser prompt demands strict JSON with the exact fields of
:class:`CreativeBrief`; the shared validation layer still verifies the result,
so a bad model output is handled the same way as a bad local parse.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from ..core.exceptions import ProviderError
from ..schemas.brief import CreativeBrief
from ..schemas.validation import ValidationIssue
from .base import LLMProvider

logger = logging.getLogger(__name__)

_SCHEMA_HINT = (
    'Return ONLY a JSON object with optional keys: "campaign_name", '
    '"target_audience", "key_message", "tone" (one of: '
    "hype, luxury, playful, professional, emotional, sustainable, retro, minimal, edgy), "
    '"deadline" (ISO date YYYY-MM-DD). Omit any field you are not confident about.'
)


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - env dependent
            raise ProviderError(
                "The 'openai' package is not installed. "
                "Run: pip install -r requirements-optional.txt"
            ) from exc
        self.model = model
        self._client = OpenAI(api_key=api_key)

    def _chat_json(self, system: str, user: str) -> dict[str, Any]:
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
            data = json.loads(content)
            if not isinstance(data, dict):
                raise ValueError("expected a JSON object")
            return data
        except Exception as exc:  # network / auth / parse failures
            raise ProviderError(f"OpenAI call failed: {exc}") from exc

    def parse_brief(
        self,
        raw_brief: str,
        *,
        issues: list[ValidationIssue] | None = None,
    ) -> dict[str, Any]:
        user = raw_brief
        if issues:
            problems = "\n".join(f"- {i.field}: {i.message}" for i in issues)
            user += (
                "\n\nA previous extraction failed validation on these fields. "
                f"Re-read the brief and fix ONLY these fields:\n{problems}"
            )
        return self._chat_json(
            system=(
                "You are a strict structured-data extraction engine for "
                "marketing creative briefs. Extract the fields listed below, "
                "resolve relative deadlines like 'friday' to the next "
                "occurrence as an ISO date. Be conservative: never invent "
                "facts that are not supported by the brief. " + _SCHEMA_HINT
            ),
            user=user,
        )

    def generate_creative(self, brief: CreativeBrief) -> dict[str, Any]:
        return self._chat_json(
            system=(
                "You are a top-tier creative copywriter. Produce a short "
                "creative output from the validated brief. Return ONLY JSON "
                'with keys: "ad_concept" (one-liner), "social_caption" '
                '(short caption for social), "hashtags" (list of strings).'
            ),
            user=brief.model_dump_json(),
        )
