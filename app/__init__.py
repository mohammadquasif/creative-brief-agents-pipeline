"""Monolithic modular 2-agent creative-brief pipeline (FastAPI).

Modules
-------
core      : config, logging, shared exceptions
schemas   : Pydantic contracts shared between agents / API
llm       : swappable "brain" abstraction (local heuristics | OpenAI)
agents    : Agent 1 (Parser) and Agent 2 (Generator)
services  : the validation gate + end-to-end pipeline orchestration
api       : HTTP layer
"""

__version__ = "0.1.0"
