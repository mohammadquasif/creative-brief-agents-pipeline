"""End-to-end pipeline: Parser -> Validation gate -> Generator.

Monolithic but modular: this module wires the pieces together and owns the
order of operations, but contains no parsing / creative logic itself.
"""
from __future__ import annotations

from functools import lru_cache

from ..agents.generator import GeneratorAgent
from ..agents.parser import ParserAgent
from ..core.config import Settings, get_settings
from ..core.exceptions import InvalidBriefError
from ..llm.factory import get_provider
from ..schemas.generation import GenerationRequest, GenerationResponse, RunMeta
from .validation import ValidationService


class Pipeline:
    """Orchestrates the two agents with the validation gate in between."""

    def __init__(
        self,
        *,
        parser: ParserAgent,
        generator: GeneratorAgent,
        validator: ValidationService,
        provider_name: str,
    ) -> None:
        self.parser = parser
        self.generator = generator
        self.validator = validator
        self.provider_name = provider_name

    def run(self, request: GenerationRequest) -> GenerationResponse:
        """raw brief -> validated brief -> creative output (or a clear error)."""
        # Agent 1 — parse (output may be partial; validation decides).
        parsed = self.parser.parse(request.raw_brief)

        # Validation gate — retry / fallback / explicit error.
        result = self.validator.run(request.raw_brief, parsed, self.parser)
        if not result.valid or result.brief is None:
            raise InvalidBriefError(
                issues=result.issues,
                attempts=result.attempts,
                fallbacks_applied=result.fallbacks_applied,
                raw_brief=request.raw_brief,
            )

        # Agent 2 — generation (only ever sees a schema-valid brief).
        creative = self.generator.generate(result.brief)

        return GenerationResponse(
            validated_brief=result.brief,
            creative=creative,
            meta=RunMeta(
                provider=self.provider_name,
                validation_attempts=result.attempts,
                repair_passes=result.repair_passes,
                fallbacks_applied=result.fallbacks_applied,
            ),
        )


@lru_cache
def create_pipeline(settings: Settings | None = None) -> Pipeline:
    """Build (and cache) a fully-wired pipeline from configuration."""
    settings = settings or get_settings()
    provider = get_provider(settings)

    parser = ParserAgent(provider)
    generator = GeneratorAgent(provider)
    validator = ValidationService(max_attempts=settings.parser_retries + 1)

    return Pipeline(
        parser=parser,
        generator=generator,
        validator=validator,
        provider_name=provider.name,
    )
