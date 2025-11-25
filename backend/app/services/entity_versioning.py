"""Entity versioning utilities for CRUD operations.

This module provides helper functions for creating, updating, and soft-deleting
entities with version tracking.
"""

import uuid
from typing import Any, TypeVar

from sqlmodel import Session, SQLModel, select

from app.services.branch_filtering import apply_status_filters
from app.services.version_service import VersionService

T = TypeVar("T", bound=SQLModel)


def _resolve_identifier(
    entity: SQLModel, raw_identifier: str | uuid.UUID | None = None
) -> uuid.UUID:
    """Ensure entity has a stable identifier (entity_id)."""
    pk_column = list(entity.__class__.__table__.primary_key.columns)[0]  # type: ignore[attr-defined]
    pk_field_name = pk_column.name
    pk_value = getattr(entity, pk_field_name, None)

    identifier = getattr(entity, "entity_id", None) or raw_identifier or pk_value
    if identifier is None:
        identifier = uuid.uuid4()
    if not isinstance(identifier, uuid.UUID):
        identifier = uuid.UUID(str(identifier))
    if hasattr(entity, "entity_id"):
        entity.entity_id = identifier
    return identifier


def create_entity_with_version(
    session: Session,
    entity: T,
    entity_type: str,
    entity_id: str | None = None,
    branch: str | None = None,
) -> T:
    """Create a new entity with version=1 and status='active'.

    Args:
        session: Database session
        entity: Entity instance to create
        entity_type: Entity type name (e.g., 'project', 'user')
        entity_id: Entity ID (for version calculation, optional)
        branch: Branch name (only for branch-enabled entities)

    Returns:
        Created entity with version and status set
    """
    from app.models import BranchVersionMixin

    identifier = _resolve_identifier(entity, entity_id)
    is_branch_enabled = isinstance(entity, BranchVersionMixin)

    branch_value: str | None = branch
    if is_branch_enabled:
        branch_value = branch or getattr(entity, "branch", None) or "main"
        if hasattr(entity, "branch"):
            entity.branch = branch_value

    if identifier is not None:
        next_version = VersionService.get_next_version(
            session=session,
            entity_type=entity_type,
            entity_id=identifier,
            branch=branch_value,
        )
    else:
        next_version = 1

    # Set version and status
    if hasattr(entity, "version"):
        entity.version = next_version
    if hasattr(entity, "status"):
        entity.status = "active"

    session.add(entity)
    return entity


def update_entity_with_version(
    session: Session,
    entity_class: type[T],
    entity_id: Any,
    update_data: dict[str, Any],
    entity_type: str,
    branch: str | None = None,
) -> T:
    """Update an entity by creating a new version.

    This function:
    1. Gets the current active version
    2. Creates a new version with updated data
    3. Preserves the old version in the database

    Args:
        session: Database session
        entity_class: Entity model class
        entity_id: Entity ID (primary key)
        update_data: Dictionary of fields to update
        entity_type: Entity type name (e.g., 'project', 'user')
        branch: Branch name (only for branch-enabled entities)

    Returns:
        New version of the entity
    """
    pk_column = list(entity_class.__table__.primary_key.columns)[0]  # type: ignore[attr-defined]
    pk_field_name = pk_column.name
    pk_field = getattr(entity_class, pk_field_name)

    statement = select(entity_class).where(pk_field == entity_id)

    # Apply status filter (or branch filter for branch-enabled entities)
    from app.models import BranchVersionMixin

    is_branch_enabled = issubclass(entity_class, BranchVersionMixin)
    if is_branch_enabled:
        from app.services.branch_filtering import apply_branch_filters

        statement = apply_branch_filters(
            statement, entity_class, branch=branch or "main"
        )
    else:
        statement = apply_status_filters(statement, entity_class)

    current_entity = session.exec(statement).first()
    if not current_entity:
        raise ValueError(
            f"{entity_class.__name__} with {pk_field_name}={entity_id} not found"
        )

    identifier = getattr(current_entity, "entity_id", None) or entity_id
    next_version = VersionService.get_next_version(
        session=session,
        entity_type=entity_type,
        entity_id=identifier,
        branch=branch if is_branch_enabled else None,
    )

    if is_branch_enabled:
        entity_data = current_entity.model_dump()
        entity_data.update(update_data)
        entity_data.pop(pk_field_name, None)
        entity_data.pop("created_at", None)
        entity_data.pop("updated_at", None)
        entity_data["version"] = next_version
        entity_data["status"] = "active"
        if hasattr(entity_class, "entity_id"):
            entity_data["entity_id"] = identifier
        if hasattr(entity_class, "branch"):
            entity_data["branch"] = branch or current_entity.branch  # type: ignore[attr-defined]

        new_entity = entity_class(**entity_data)
        session.add(new_entity)
        return new_entity

    # Non-branch entities are updated in-place
    for key, value in update_data.items():
        if key in {"entity_id", pk_field_name, "version"}:
            continue
        if hasattr(current_entity, key):
            setattr(current_entity, key, value)
    if hasattr(current_entity, "version"):
        current_entity.version = next_version  # type: ignore[attr-defined]
    if hasattr(current_entity, "status"):
        current_entity.status = "active"  # type: ignore[attr-defined]

    session.add(current_entity)
    return current_entity


def soft_delete_entity(
    session: Session,
    entity_class: type[T],
    entity_id: Any,
    entity_type: str,
    branch: str | None = None,
) -> T:
    """Soft delete an entity by creating a new version with status='deleted'.

    Args:
        session: Database session
        entity_class: Entity model class
        entity_id: Entity ID (primary key)
        entity_type: Entity type name (e.g., 'project', 'user')
        branch: Branch name (only for branch-enabled entities)

    Returns:
        New version of the entity with status='deleted'
    """
    pk_column = list(entity_class.__table__.primary_key.columns)[0]  # type: ignore[attr-defined]
    pk_field_name = pk_column.name
    pk_field = getattr(entity_class, pk_field_name)

    # Get current active entity
    statement = select(entity_class).where(pk_field == entity_id)

    # Apply status filter (or branch filter for branch-enabled entities)
    from app.models import BranchVersionMixin

    is_branch_enabled = issubclass(entity_class, BranchVersionMixin)
    if is_branch_enabled:
        from app.services.branch_filtering import apply_branch_filters

        statement = apply_branch_filters(
            statement, entity_class, branch=branch or "main"
        )
    else:
        statement = apply_status_filters(statement, entity_class)

    current_entity = session.exec(statement).first()
    if not current_entity:
        raise ValueError(
            f"{entity_class.__name__} with {pk_field_name}={entity_id} not found"
        )

    identifier = getattr(current_entity, "entity_id", None) or entity_id
    next_version = VersionService.get_next_version(
        session=session,
        entity_type=entity_type,
        entity_id=identifier,
        branch=branch if is_branch_enabled else None,
    )

    if is_branch_enabled:
        entity_data = current_entity.model_dump()
        entity_data.pop(pk_field_name, None)
        entity_data.pop("created_at", None)
        entity_data.pop("updated_at", None)
        entity_data["version"] = next_version
        entity_data["status"] = "deleted"
        if hasattr(entity_class, "entity_id"):
            entity_data["entity_id"] = identifier
        if hasattr(entity_class, "branch"):
            entity_data["branch"] = branch or current_entity.branch  # type: ignore[attr-defined]

        deleted_entity = entity_class(**entity_data)
        session.add(deleted_entity)
        return deleted_entity

    # Non-branch entities: update status in place
    if hasattr(current_entity, "status"):
        current_entity.status = "deleted"  # type: ignore[attr-defined]
    if hasattr(current_entity, "version"):
        current_entity.version = next_version  # type: ignore[attr-defined]

    session.add(current_entity)
    return current_entity


def restore_entity(
    session: Session,
    entity_class: type[T],
    entity_id: Any,
    entity_type: str,
    branch: str | None = None,
) -> T:
    """Restore a soft-deleted entity by creating a new version with status='active'.

    Args:
        session: Database session
        entity_class: Entity model class
        entity_id: Entity ID (primary key)
        entity_type: Entity type name (e.g., 'project', 'user')
        branch: Branch name (only for branch-enabled entities)

    Returns:
        New version of the entity with status='active'

    Raises:
        ValueError: If entity not found or not deleted
    """
    pk_column = list(entity_class.__table__.primary_key.columns)[0]  # type: ignore[attr-defined]
    pk_field_name = pk_column.name
    pk_field = getattr(entity_class, pk_field_name)

    # For branch-enabled entities, we need to find by entity_id, not primary key
    # because soft delete creates a new version with a new primary key
    from app.models import BranchVersionMixin

    is_branch_enabled = issubclass(entity_class, BranchVersionMixin)

    if is_branch_enabled:
        branch_value = branch or "main"
        # First, find any version by primary key to get entity_id
        any_version = session.exec(
            select(entity_class).where(pk_field == entity_id)
        ).first()

        if not any_version:
            raise ValueError(
                f"{entity_class.__name__} with {pk_field_name}={entity_id} not found"
            )

        # Get entity_id from the found version
        identifier = getattr(any_version, "entity_id", None)
        if not identifier:
            raise ValueError(
                f"{entity_class.__name__} with {pk_field_name}={entity_id} has no entity_id"
            )

        # Query by entity_id and branch to find deleted version
        statement = (
            select(entity_class)
            .where(entity_class.entity_id == identifier)  # type: ignore[attr-defined]
            .where(entity_class.branch == branch_value)  # type: ignore[attr-defined]
            .order_by(entity_class.version.desc())  # type: ignore[attr-defined]
        )
        deleted_entity = session.exec(statement).first()
    else:
        # For non-branch entities, query by primary key
        statement = (
            select(entity_class)
            .where(pk_field == entity_id)
            .order_by(entity_class.version.desc())  # type: ignore[attr-defined]
        )
        deleted_entity = session.exec(statement).first()

    if not deleted_entity:
        raise ValueError(
            f"{entity_class.__name__} with {pk_field_name}={entity_id} not found"
        )

    # Check if it's actually deleted
    if hasattr(deleted_entity, "status") and deleted_entity.status != "deleted":  # type: ignore[attr-defined]
        raise ValueError(
            f"{entity_class.__name__} with {pk_field_name}={entity_id} is not deleted"
        )

    identifier = getattr(deleted_entity, "entity_id", None) or entity_id
    next_version = VersionService.get_next_version(
        session=session,
        entity_type=entity_type,
        entity_id=identifier,
        branch=branch if is_branch_enabled else None,
    )

    # For ChangeOrder, check if there's already an active version with the same change_order_number
    # This is needed because change_order_number has a unique constraint
    if entity_class.__name__ == "ChangeOrder":
        from app.models import ChangeOrder

        change_order_number = getattr(deleted_entity, "change_order_number", None)
        if change_order_number:
            active_co = session.exec(
                select(ChangeOrder)
                .where(ChangeOrder.change_order_number == change_order_number)
                .where(ChangeOrder.status == "active")
            ).first()
            if active_co:
                raise ValueError(
                    f"An active change order with number '{change_order_number}' already exists. "
                    "Cannot restore deleted change order with the same number."
                )

    if is_branch_enabled:
        entity_data = deleted_entity.model_dump()
        entity_data.pop(pk_field_name, None)
        entity_data.pop("created_at", None)
        entity_data.pop("updated_at", None)
        entity_data["version"] = next_version
        entity_data["status"] = "active"
        if hasattr(entity_class, "entity_id"):
            entity_data["entity_id"] = identifier
        if hasattr(entity_class, "branch"):
            entity_data["branch"] = branch or deleted_entity.branch  # type: ignore[attr-defined]

        restored_entity = entity_class(**entity_data)
        session.add(restored_entity)
        return restored_entity

    # Non-branch entities: create new version with active status
    entity_data = deleted_entity.model_dump()
    entity_data.pop(pk_field_name, None)
    entity_data.pop("created_at", None)
    entity_data.pop("updated_at", None)
    entity_data["version"] = next_version
    entity_data["status"] = "active"
    if hasattr(entity_class, "entity_id"):
        entity_data["entity_id"] = identifier

    restored_entity = entity_class(**entity_data)
    session.add(restored_entity)
    return restored_entity


def hard_delete_entity(
    session: Session,
    entity_class: type[T],
    entity_id: Any,
    entity_type: str,  # noqa: ARG001
    branch: str | None = None,
) -> None:
    """Permanently delete an entity and all its versions (hard delete).

    This function permanently removes all versions of an entity from the database.
    It should only be used for soft-deleted entities and requires admin privileges.

    Args:
        session: Database session
        entity_class: Entity model class
        entity_id: Entity ID (primary key)
        entity_type: Entity type name (e.g., 'project', 'user')
        branch: Branch name (only for branch-enabled entities)

    Raises:
        ValueError: If entity not found or not deleted
    """
    pk_column = list(entity_class.__table__.primary_key.columns)[0]  # type: ignore[attr-defined]
    pk_field_name = pk_column.name
    pk_field = getattr(entity_class, pk_field_name)

    # For branch-enabled entities, we need to find by entity_id
    from app.models import BranchVersionMixin

    is_branch_enabled = issubclass(entity_class, BranchVersionMixin)

    if is_branch_enabled:
        branch_value = branch or "main"
        # First, find any version by primary key to get entity_id
        any_version = session.exec(
            select(entity_class).where(pk_field == entity_id)
        ).first()

        if not any_version:
            raise ValueError(
                f"{entity_class.__name__} with {pk_field_name}={entity_id} not found"
            )

        # Get entity_id from the found version
        identifier = getattr(any_version, "entity_id", None)
        if not identifier:
            raise ValueError(
                f"{entity_class.__name__} with {pk_field_name}={entity_id} has no entity_id"
            )

        # Verify at least one version is deleted
        statement = (
            select(entity_class)
            .where(entity_class.entity_id == identifier)  # type: ignore[attr-defined]
            .where(entity_class.branch == branch_value)  # type: ignore[attr-defined]
            .order_by(entity_class.version.desc())  # type: ignore[attr-defined]
        )
        latest_version = session.exec(statement).first()

        if not latest_version:
            raise ValueError(
                f"{entity_class.__name__} with {pk_field_name}={entity_id} not found"
            )

        if hasattr(latest_version, "status") and latest_version.status != "deleted":  # type: ignore[attr-defined]
            raise ValueError(
                f"{entity_class.__name__} with {pk_field_name}={entity_id} is not deleted. "
                "Hard delete can only be performed on soft-deleted entities."
            )

        # Delete all versions for this entity_id and branch
        statement = (
            select(entity_class)
            .where(entity_class.entity_id == identifier)  # type: ignore[attr-defined]
            .where(entity_class.branch == branch_value)  # type: ignore[attr-defined]
        )
        all_versions = session.exec(statement).all()
        for version in all_versions:
            session.delete(version)
    else:
        # For non-branch entities, query by primary key
        statement = (
            select(entity_class)
            .where(pk_field == entity_id)
            .order_by(entity_class.version.desc())  # type: ignore[attr-defined]
        )
        latest_version = session.exec(statement).first()

        if not latest_version:
            raise ValueError(
                f"{entity_class.__name__} with {pk_field_name}={entity_id} not found"
            )

        # Verify it's deleted
        if hasattr(latest_version, "status") and latest_version.status != "deleted":  # type: ignore[attr-defined]
            raise ValueError(
                f"{entity_class.__name__} with {pk_field_name}={entity_id} is not deleted. "
                "Hard delete can only be performed on soft-deleted entities."
            )

        # Get entity_id to delete all versions
        identifier = getattr(latest_version, "entity_id", None) or entity_id

        # Delete all versions for this entity_id
        statement = select(entity_class).where(
            entity_class.entity_id == identifier  # type: ignore[attr-defined]
        )
        all_versions = session.exec(statement).all()
        for version in all_versions:
            session.delete(version)
