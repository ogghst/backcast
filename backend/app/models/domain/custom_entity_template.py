"""Custom Entity Template — admin-defined field-template registry (Versionable, NOT Branchable, org-scoped).

Groups typed custom field definitions for a target entity type (PROJECT|WBS_ELEMENT|
WORK_PACKAGE|CHANGE_ORDER), owned by an organizational unit. Mirrors CostElementType
structurally (EntityBase + VersionableMixin). field_definitions is a DICT keyed by
field code (NOT a list) — required by the raw-INSERT JSONB guard in the versioning
commands (isinstance(values[col], dict)).
"""

from typing import Any
from uuid import UUID

from sqlalchemy import Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base.base import EntityBase
from app.models.mixins import VersionableMixin


class CustomEntityTemplate(EntityBase, VersionableMixin):
    """Admin-defined custom entity template (Versionable, org-scoped)."""

    __tablename__ = "custom_entity_templates"

    custom_entity_template_id: Mapped[UUID] = mapped_column(
        PG_UUID, nullable=False, index=True
    )
    organizational_unit_id: Mapped[UUID] = mapped_column(
        PG_UUID,
        nullable=False,
        index=True,
        # NOTE: No DB-level FK — organizational_unit_id is a root ID (Backcast convention).
    )
    target_entity_type: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    field_definitions: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    __table_args__ = (
        # C1: exactly one current (open valid_time, non-deleted) version per template root.
        Index(
            "ix_custom_entity_templates_current",
            "custom_entity_template_id",
            unique=True,
            postgresql_where=text("upper(valid_time) IS NULL AND deleted_at IS NULL"),
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<CustomEntityTemplate(id={self.id}, "
            f"custom_entity_template_id={self.custom_entity_template_id}, "
            f"target_entity_type={self.target_entity_type}, code={self.code})>"
        )
