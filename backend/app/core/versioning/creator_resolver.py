"""Shared creator-name + entity-timestamp resolution utility.

Batch-resolves and attaches `created_by_name` on versioned/branchable
entities (and any other ORM object exposing a `created_by` attribute)
from the latest version of the corresponding User row.

This is the shared replacement for the inline creator-lookup logic that
was duplicated across TemporalService.get_history,
BranchableService.get_history, ProjectService.get_projects and
DocumentService._populate_creator_names. Read paths (get_as_of / list)
that previously returned `created_by_name = null` now reuse this helper.

Also exposes `populate_entity_timestamps` which derives, in a single
batched query per entity type, the true `created_at`
(MIN(lower(transaction_time)) over all versions) and `updated_at`
(MAX(lower(transaction_time)) over all versions). The previous
single-version `created_at` derivation mislabeled the last-modification
time as creation; this corrects it.
"""

import re
from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime
from typing import Any, cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


def _root_field_name_for(entity_class: type[Any]) -> str | None:
    """Derive the root column name from an entity class name.

    Mirrors `_get_root_field_name` on TemporalService / BranchableService
    (CamelCase -> snake_case + `_id`). Returns None if the class lacks a
    `transaction_time` attribute (not a versioned entity).
    """
    if not hasattr(entity_class, "transaction_time"):
        return None
    name = entity_class.__name__
    if name.endswith("Version"):
        name = name[:-7]
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    snake_name = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
    return f"{snake_name}_id"


async def populate_entity_timestamps(
    session: AsyncSession, entities: Sequence[Any]
) -> None:
    """Batch-derive and set `created_at`/`updated_at` on versioned entities.

    For each entity type present, issues a single query computing:
    - created_at = MIN(lower(transaction_time)) over ALL versions of the
      root entity (true creation time, NOT the current version's bound).
    - updated_at = MAX(lower(transaction_time)) over all versions (last
      modification; includes soft-deletes which are the latest mod).

    Sets `created_at` only when `_created_at_is_settable(entity)` is True
    (skips e.g. ChangeOrder's read-only hybrid_property). `updated_at` is a
    plain schema field and is always settable. No-op for empty input or
    entities lacking the root attribute / transaction_time.

    Args:
        session: Active async DB session.
        entities: ORM versioned entities sharing the same root-field scheme.
    """
    if not entities:
        return

    # Group entities by their class so each type is one query.
    groups: dict[type[Any], list[Any]] = defaultdict(list)
    for entity in entities:
        groups[type(entity)].append(entity)

    for entity_class, members in groups.items():
        if not members:
            continue
        root_field_name = _root_field_name_for(entity_class)
        if root_field_name is None:
            continue
        root_col = getattr(entity_class, root_field_name, None)
        transaction_time_col = getattr(entity_class, "transaction_time", None)
        if root_col is None or transaction_time_col is None:
            continue

        # Collect the distinct root id values present on the members.
        root_ids: list[Any] = []
        for entity in members:
            rid = getattr(entity, root_field_name, None)
            if rid is not None:
                root_ids.append(rid)
        if not root_ids:
            continue

        entity_alias = cast(Any, entity_class)
        stmt = (
            select(
                getattr(entity_alias, root_field_name),
                func.min(func.lower(entity_alias.transaction_time)),
                func.max(func.lower(entity_alias.transaction_time)),
            )
            .where(getattr(entity_alias, root_field_name).in_(root_ids))
            .group_by(getattr(entity_alias, root_field_name))
        )
        result = await session.execute(stmt)
        # Stringify keys so str/UUID both match (created_by uses the same trick).
        timestamp_map: dict[str, tuple[Any, Any]] = {
            str(row[0]): (row[1], row[2]) for row in result.all()
        }

        for entity in members:
            rid = getattr(entity, root_field_name, None)
            if rid is None:
                continue
            pair = timestamp_map.get(str(rid))
            if pair is None:
                continue
            created_at, updated_at = pair
            if _created_at_is_settable(entity) and isinstance(created_at, datetime):
                entity.created_at = created_at
            if isinstance(updated_at, datetime):
                entity.updated_at = updated_at


def _created_at_is_settable(entity: Any) -> bool:
    """Return False when `created_at` is a read-only descriptor on the class.

    Some domain models (e.g. ChangeOrder) expose `created_at` as a read-only
    hybrid_property/property. Attempting to assign to it raises
    AttributeError, so callers must skip derivation for those.
    """
    import inspect

    for klass in type(entity).__mro__:
        descriptor = inspect.getattr_static(klass, "created_at", None)
        if descriptor is None:
            continue
        # A plain instance attribute on the instance is always settable; only
        # class-level descriptors (property/hybrid_property) can be read-only.
        if isinstance(descriptor, property):
            return descriptor.fset is not None
        # SQLAlchemy hybrid_property raises on set unless an extension_type setter exists.
        if type(descriptor).__name__ == "hybrid_property":
            return False
    return True


async def populate_creator_names(
    session: AsyncSession, entities: Sequence[Any]
) -> None:
    """Batch-resolve and set `created_by_name` on entities that have a `created_by`.

    Performs a single lookup keyed by each entity's `created_by`, resolving to the
    user's most recent `full_name`. Entities without a `created_by` attribute or
    with a null `created_by` are left untouched. Safe to call with an empty list.

    Args:
        session: Active async DB session.
        entities: ORM entities (or objects with a `created_by` attribute).
    """
    if not entities:
        return

    # Lazy import avoids a model import cycle at module load time.
    from app.models.domain.user import User

    ids: set[Any] = set()
    for entity in entities:
        created_by = getattr(entity, "created_by", None)
        if created_by is not None:
            ids.add(created_by)
    if not ids:
        return

    # Resolve the latest name per user_id (users are themselves versioned).
    user_alias = cast(Any, User)
    creator_subq = (
        select(user_alias.user_id, user_alias.full_name)
        .distinct(user_alias.user_id)
        .order_by(user_alias.user_id, user_alias.transaction_time.desc())
        .subquery("creator_lookup")
    )
    stmt = select(creator_subq.c.user_id, creator_subq.c.full_name).where(
        creator_subq.c.user_id.in_(list(ids))
    )
    result = await session.execute(stmt)
    # created_by is stored as PG_UUID; stringify keys so str/UUID both match.
    name_map: dict[str, str] = {str(row[0]): row[1] for row in result.all()}

    for entity in entities:
        created_by = getattr(entity, "created_by", None)
        if created_by is not None:
            entity.created_by_name = name_map.get(str(created_by))
