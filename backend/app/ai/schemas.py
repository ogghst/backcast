"""Shared Pydantic schemas for AI specialist structured output."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SpecialistOutput(BaseModel):
    """Standard structured output for all specialists.

    Every specialist returns this schema by default. Specialists with
    domain-specific schemas (e.g. EVMMetricsRead, ImpactAnalysisResponse)
    override this via their ``structured_output_schema`` config.
    """

    summary: str = Field(
        description="Brief summary of what was accomplished, including any diagrams, useful to reply to the user request. Output in markdown format",
    )
    key_findings: list[str] = Field(
        default_factory=list,
        description="Most important discoveries or results. Output in markdown format",
    )
    open_questions: list[str] = Field(
        default_factory=list,
        description="Questions that need answers or further investigation. Output in markdown format",
    )
    delegation_notes: str = Field(
        default="",
        description="Context for follow-up work (IDs of created entities, partial results, references). Output in markdown format",
    )


__all__ = ["SpecialistOutput"]
