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
        description=(
            "Brief summary of what was accomplished, including any diagrams, useful "
            "to reply to the user request. When entities were created or resolved, "
            "record the concrete identifiers: the created-entity code/name AND the "
            'resolved project (e.g. "Created WBE DESIGN-001 on project QAE001"). '
            "Output in markdown format."
        ),
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
        description=(
            "Context for follow-up work: IDs of created entities (code/name), the "
            "resolved project, partial results, references. When an entity was "
            "created or a project/identity resolved, record its exact code/name and "
            "project here so downstream steps and the supervisor's final answer can "
            "cite it without re-deriving or re-disambiguating. Output in markdown format."
        ),
    )


__all__ = ["SpecialistOutput"]
