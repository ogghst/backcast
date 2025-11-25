"""Service for retrieving version history of entities."""

import uuid
from typing import Any

from sqlmodel import Session, select

from app.models import BranchVersionMixin
from app.services.version_service import ENTITY_TYPE_MAP


def get_version_history(
    session: Session,
    entity_type: str,
    entity_id: uuid.UUID,
    branch: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Get version history for an entity.

    Args:
        session: Database session
        entity_type: Entity type name (e.g., 'project', 'wbe')
        entity_id: Entity ID (entity_id field, not primary key)
        branch: Branch name (only for branch-enabled entities)
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of version records with metadata
    """
    if entity_type not in ENTITY_TYPE_MAP:
        raise ValueError(f"Unknown entity type: {entity_type}")

    model_class = ENTITY_TYPE_MAP[entity_type]
    is_branch_enabled = issubclass(model_class, BranchVersionMixin)

    # Build query
    statement = select(model_class).where(
        model_class.entity_id == entity_id  # type: ignore[attr-defined]
    )

    if is_branch_enabled:
        branch_value = branch or "main"
        statement = statement.where(
            model_class.branch == branch_value  # type: ignore[attr-defined]
        )

    # Order by version descending (newest first)
    statement = statement.order_by(
        model_class.version.desc()  # type: ignore[attr-defined]
    )

    # Apply pagination
    statement = statement.offset(skip).limit(limit)

    versions = session.exec(statement).all()

    # Convert to dict with metadata
    result = []
    for version in versions:
        version_dict = version.model_dump()
        # Include key metadata fields
        result.append(
            {
                "version": version_dict.get("version"),
                "status": version_dict.get("status"),
                "branch": version_dict.get("branch") if is_branch_enabled else None,
                "created_at": version_dict.get("created_at"),
                "updated_at": version_dict.get("updated_at"),
                "data": version_dict,  # Full entity data
            }
        )

    return result
