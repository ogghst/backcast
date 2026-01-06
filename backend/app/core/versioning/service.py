"""Generic TemporalService for versioned entities.

Implements the TemporalService pattern from ADR-005 for entities
following the VersionableProtocol.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.protocols import VersionableProtocol


class TemporalService[TVersionable: VersionableProtocol]:
    """Base service for versioned entities (VersionableProtocol).

    Provides common operations for entities with bitemporal tracking:
    - Get current version (as of now)
    - Time travel queries (as of specific timestamp)
    - Create new version
    - Update (creates new version)
    - Soft delete

    Note: Temporal queries using TSTZRANGE operators need proper setup.
    Currently simplified for basic operations.
    """

    def __init__(self, entity_class: type[TVersionable], session: AsyncSession) -> None:
        self.entity_class = entity_class
        self.session = session

    async def get_by_id(self, entity_id: UUID) -> TVersionable | None:
        """Get entity by ID (returns specific version by PK)."""
        return await self.session.get(self.entity_class, entity_id)

    async def get_current_version(
        self, root_id: UUID, branch: str = "main"
    ) -> TVersionable | None:
        """Get current active version of entity by its root ID.

        Filters by:
        - Root ID (e.g., project_id, wbe_id)
        - Branch (default: main)
        - Validity (valid_time unclosed)
        - Not deleted
        """
        from typing import Any, cast

        from sqlalchemy import func

        # Introspect root field name (e.g. project_id, wbe_id)
        root_field = f"{self.entity_class.__name__.lower()}_id"
        if self.entity_class.__name__.lower().endswith("version"):
            root_field = f"{self.entity_class.__name__.lower()[:-7]}_id"

        stmt = (
            select(self.entity_class)
            .where(
                getattr(self.entity_class, root_field) == root_id,
                self.entity_class.branch == branch,
                func.upper(cast(Any, self.entity_class).valid_time).is_(None),
                cast(Any, self.entity_class).deleted_at.is_(None),
            )
            .order_by(cast(Any, self.entity_class).valid_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[TVersionable]:
        """Get all entities (current versions) with pagination.

        Filters by upper(valid_time) IS NULL (open-ended) and deleted_at IS NULL.
        """
        from typing import Any, cast

        from sqlalchemy import func

        stmt = (
            select(self.entity_class)
            .where(
                # CRITICAL FIX: Use upper(valid_time) IS NULL instead of @> operator
                # The @> operator can match recently-closed versions if query runs
                # at the exact same microsecond as the close operation
                func.upper(cast(Any, self.entity_class).valid_time).is_(None),
                cast(Any, self.entity_class).deleted_at.is_(None),
            )
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_as_of(self, entity_id: UUID, as_of: datetime) -> TVersionable | None:
        """Time travel: Get entity as it was at specific timestamp.

        Finds version where valid_time @> as_of for the given entity_id.
        """
        from typing import Any, cast

        # We need to query by the root ID (entity_id passed here is assumed to be the root ID in this context?)
        # Wait, get_by_id usually takes the PK. But for time travel we often query by the Cluster/Root ID.
        # In this system, 'entity_id' in get_by_id is usually the PK (specific version).
        # But 'get_as_of' usually implies "Get the state of Entity X at time T".
        # If Entity X is defined by a Root ID (e.g. user_id), then we query by that.
        # If the caller passes a specific version ID, that doesn't make sense for "as of".
        # We will assume entity_id refers to the ROOT ID for time travel queries if the entity is versioned.
        # However, TemporalService is generic.
        # Let's check how VersionedCommandABC derives the root field: _root_field_name().

        # We can recycle the _root_field_name logic or just assume standard 'id' if simple temporal?
        # No, EVCS implies Root ID vs Version ID.
        # Let's try to detect the root field dynamically or require it.
        # For now, we'll try to guess based on class name like Command does.

        root_field = f"{self.entity_class.__name__.lower()}_id"
        if self.entity_class.__name__.lower().endswith("version"):
            root_field = f"{self.entity_class.__name__.lower()[:-7]}_id"

        # Verify field exists, else fallback to 'id'? No, that would be wrong for versioning.
        if not hasattr(self.entity_class, root_field):
            # If no root ID field found, maybe it's not a root-versioned entity?
            # But VersionableProtocol implies it.
            # We will proceed with the guessed field.
            pass

        stmt = (
            select(self.entity_class)
            .where(
                getattr(self.entity_class, root_field) == entity_id,
                cast(Any, self.entity_class).valid_time.op("@>")(as_of),
                cast(Any, self.entity_class).deleted_at.is_(
                    None
                ),  # Usually we want to see if it existed then?
                # If we want "as of", we want the version valid at that time.
                # If it was deleted at that time, we might return None or the deleted version?
                # Usually "deleted_at" is metadata. If valid_time covers 'as_of', it returns the record.
                # If the record says "I am deleted", then it's deleted.
                # But typically deleted_at is SET when soft-deleted, effectively closing validity?
                # Implementation detail: soft_delete usually closes valid_time?
                # Command soft_delete: "Mark current version as deleted." -> It sets deleted_at.
                # It does NOT verify if valid_time is closed.
                # So we should probably check deleted_at.
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self, actor_id: UUID, root_id: UUID | None = None, **fields: Any
    ) -> TVersionable:
        """Create new versioned entity."""
        from uuid import uuid4

        from app.core.versioning.commands import CreateVersionCommand

        # Determine the expected root field name (e.g. user_id)
        # Introspection to find root field again
        root_field = f"{self.entity_class.__name__.lower()}_id"
        if self.entity_class.__name__.lower().endswith("version"):
            root_field = f"{self.entity_class.__name__.lower()[:-7]}_id"

        # If root_id not explicitly passed, try to find it in fields (using domain name)
        if root_id is None:
            if root_field in fields:
                root_id = fields.pop(root_field)
            else:
                root_id = uuid4()

        # Ensure the domain-specific root ID field is NOT in fields if we already extracted it,
        # but wait, the Command.execute -> entity_class(**fields) MIGHT need it if it's a field on the model!
        # Re-reading: CreateVersionCommand.__init__(..., root_id, **fields).
        # It stores fields.
        # It DOES NOT inject root_id back into fields.
        # So fields MUST contain 'user_id': root_id if the User model has user_id column.
        # BUT we cannot pass 'root_id': ... to CreateVersionCommand if it's a kwarg conflict.
        # The kwarg conflict was because test passed 'root_id'.
        # 'user_id' != 'root_id'.
        # If we pass `user_id` in fields, command init works.
        # If we pass `root_id` in fields, command init FAILS (conflict).

        # So:
        # 1. We have 'root_id' (UUID).
        # 2. We need to ensure 'fields' has the DOMAIN SPECIFIC field (e.g. 'user_id': root_id).
        # 3. We need to ensure 'fields' does NOT have 'root_id' key.

        # Inject domain-specific ID into fields for the model to use
        fields[root_field] = root_id

        # Usage: CreateVersionCommand(..., root_id=root_id, **fields)
        # If fields has 'user_id', it's fine.
        # If fields has 'root_id', it conflicts.
        # Ensure 'root_id' is NOT in fields. (Arguments named 'root_id' shouldn't exist on domain models ideally, but the test passed it).
        if "root_id" in fields:
            del fields["root_id"]

        cmd = CreateVersionCommand(
            entity_class=self.entity_class, root_id=root_id, actor_id=actor_id, **fields
        )
        return await cmd.execute(self.session)



    async def update(
        self, entity_id: UUID, actor_id: UUID, **updates: Any
    ) -> TVersionable:
        """Update entity (creates new version)."""
        from app.core.versioning.commands import UpdateVersionCommand

        cmd = UpdateVersionCommand(
            entity_class=self.entity_class,
            root_id=entity_id,
            actor_id=actor_id,
            **updates,
        )
        return await cmd.execute(self.session)

    async def soft_delete(self, entity_id: UUID, actor_id: UUID) -> None:
        """Soft delete entity."""
        from app.core.versioning.commands import SoftDeleteCommand

        cmd = SoftDeleteCommand(
            entity_class=self.entity_class,
            root_id=entity_id,
            actor_id=actor_id,
        )
        await cmd.execute(self.session)

    async def get_history(self, root_id: UUID) -> list[TVersionable]:
        """Get all versions of an entity with joined creator name."""
        from typing import Any, cast

        from app.models.domain.user import User

        # Introspect root field name (e.g. project_id, wbe_id, user_id, department_id)
        root_field = f"{self.entity_class.__name__.lower()}_id"
        if self.entity_class.__name__.lower().endswith("version"):
            root_field = f"{self.entity_class.__name__.lower()[:-7]}_id"

        # Create a subquery to get a unique (latest) name for each user_id
        # ensuring we don't multiply rows if the user entity itself has multiple versions.
        # We assume the most recent version (by transaction_time) has the correct name.
        User = cast(Any, User)  # Cast for type checker to allow table access if needed
        creator_subq = (
            select(User.user_id, User.full_name)
            .distinct(User.user_id)
            .order_by(User.user_id, User.transaction_time.desc())
            .subquery("creator_lookup")
        )

        stmt = (
            select(self.entity_class, creator_subq.c.full_name.label("created_by_name"))
            .outerjoin(
                creator_subq,
                cast(Any, self.entity_class).created_by == creator_subq.c.user_id,
            )
            .where(
                getattr(self.entity_class, root_field) == root_id,
                cast(Any, self.entity_class).deleted_at.is_(None),
            )
            .order_by(cast(Any, self.entity_class).transaction_time.desc())
        )

        result = await self.session.execute(stmt)
        history = []
        for row in result.all():
            entity = row[0]
            # Attach the joined name to the entity object
            entity.created_by_name = row[1]
            history.append(entity)

        return history
