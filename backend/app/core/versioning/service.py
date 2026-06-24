"""Generic TemporalService for versioned entities.

Implements the TemporalService pattern from ADR-005 for entities
following the VersionableProtocol.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.protocols import VersionableProtocol

if TYPE_CHECKING:
    from app.core.versioning.enums import BranchMode


class TemporalService[TVersionable: VersionableProtocol]:
    """Base service for versioned entities (VersionableProtocol).

    Provides common operations for entities with bitemporal tracking:
    - Get current version (as of now)
    - Time travel queries (as of specific timestamp)
    - Create new version
    - Update (creates new version)
    - Soft delete

    Inheritance Note:
        Subclasses (e.g., BranchService, WBEService) inherit all methods.
        Key inherited methods:
        - `soft_delete(entity_id, actor_id, control_date)` - Uses root_id (UUID)
        - `get_current_version(root_id, branch)` - Returns active version
        - `get_as_of(entity_id, as_of, branch)` - Time-travel query

        When calling inherited methods, use the entity's root_id field
        (e.g., branch_id, wbe_id), NOT composite keys like (name, project_id).

    Note: Temporal queries using TSTZRANGE operators need proper setup.
    Currently simplified for basic operations.
    """

    def __init__(self, entity_class: type[TVersionable], session: AsyncSession) -> None:
        self.entity_class = entity_class
        self.session = session

    def _get_root_field_name(self) -> str:
        """Derive the root column name from the entity class name.

        Handles:
        - Project -> project_id
        - CostElement -> cost_element_id
        - WBE -> wbe_id
        """
        import re

        name = self.entity_class.__name__
        if name.endswith("Version"):
            name = name[:-7]

        # CamelCase to snake_case
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        snake_name = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

        return f"{snake_name}_id"

    async def get_by_id(self, entity_id: UUID) -> TVersionable | None:
        """Get entity by ID (returns specific version by PK)."""
        return await self.session.get(self.entity_class, entity_id)

    async def get_all(self, skip: int = 0, limit: int = 100000) -> list[TVersionable]:
        """Get all entities (current versions) with pagination.

        Filters by upper(valid_time) IS NULL (open-ended) and deleted_at IS NULL.
        """
        from app.core.temporal_queries import is_current_version

        stmt = (
            select(self.entity_class)
            .where(
                is_current_version(
                    self.entity_class.valid_time, self.entity_class.deleted_at
                )
            )
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        entities = list(result.scalars().all())
        await self._populate_read_fields(entities)
        return entities

    async def get_as_of(
        self,
        entity_id: UUID,
        as_of: datetime | None = None,
        branch: str = "main",
        branch_mode: "BranchMode | None" = None,
    ) -> TVersionable | None:
        """Time travel or get current: Get entity as it was at specific timestamp.

        Implements bitemporal time travel by checking BOTH temporal dimensions:
        - valid_time: When the data was valid in the real world
        - transaction_time: When the data was recorded in the database

        Args:
            entity_id: Root entity ID
            as_of: Timestamp to query
            branch: Branch name (default: main)
            branch_mode: Resolution mode for branches
                - ISOLATED (default): Only return from specified branch
                - MERGED: Fall back to main if not found on branch

        Returns entity if:
        - as_of >= lower(valid_time) (entity existed at that time)
        - as_of < upper(valid_time) OR upper IS NULL (entity still valid)
        - as_of >= lower(transaction_time) (version was committed by then)
        - as_of < upper(transaction_time) OR upper IS NULL (version not superseded)
        - Entity not deleted
        - Entity on correct branch

        The @> operator alone is insufficient because it treats NULL upper bounds
        as infinity, matching ANY timestamp. We must also verify as_of >= lower bound.
        """

        from app.core.versioning.enums import BranchMode

        # Default to ISOLATED mode if not specified
        if branch_mode is None:
            branch_mode = BranchMode.ISOLATED

        # Try to get from requested branch
        result = await self._get_as_of_from_branch(entity_id, as_of, branch)

        # If found, or isolated mode, or already on main, return result
        if result is not None or branch_mode == BranchMode.ISOLATED or branch == "main":
            await self._populate_read_fields([result] if result is not None else [])
            return result

        # MERGED mode: Check if explicitly deleted on branch before falling back
        is_deleted_on_branch = await self._is_deleted_on_branch(
            entity_id, as_of, branch
        )
        if is_deleted_on_branch:
            # Respect branch deletion, don't fall back to main
            return None

        # Fall back to main branch
        result = await self._get_as_of_from_branch(entity_id, as_of, "main")
        await self._populate_read_fields([result] if result is not None else [])
        return result

    async def _populate_read_fields(self, entities: list[Any]) -> None:
        """Populate read-only computed fields on a batch of entities.

        Resolves `created_by_name` from the User table (batched) and derives
        `created_at` (true creation = MIN over all versions) plus `updated_at`
        (MAX over all versions) from the transaction_time ranges. Both are
        no-ops for entities that don't expose the relevant attributes.
        """
        from app.core.versioning.creator_resolver import (
            populate_creator_names,
            populate_entity_timestamps,
        )

        await populate_creator_names(self.session, entities)
        await populate_entity_timestamps(self.session, entities)

    async def _get_as_of_from_branch(
        self, entity_id: UUID, as_of: datetime | None, branch: str
    ) -> TVersionable | None:
        """Internal: Get entity from specific branch at timestamp.

        Uses Valid Time Travel semantics:
        - Only checks valid_time (when the fact was valid in the real world)
        - Does NOT check transaction_time (when recorded in database)

        This allows querying historical states and forward-looking scenarios
        (e.g., forecasts with future control_dates).
        """
        from typing import Any, cast

        root_field = self._get_root_field_name()

        stmt = select(self.entity_class).where(
            getattr(self.entity_class, root_field) == entity_id,
        )

        # Only filter by branch if the entity has a branch attribute
        if hasattr(self.entity_class, "branch"):
            stmt = stmt.where(cast(Any, self.entity_class).branch == branch)

        # Apply Valid Time Travel filter or Current Version filter
        if as_of:
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            from sqlalchemy import func

            stmt = stmt.where(
                func.upper(cast(Any, self.entity_class).valid_time).is_(None),
                func.not_(
                    func.isempty(self.entity_class.valid_time)
                ),  # Exclude empty ranges
                cast(Any, self.entity_class).deleted_at.is_(None),
            )
            # Order by valid_time DESC, then transaction_time DESC as tiebreaker
            # This ensures deterministic selection when multiple rows have the same valid_time
            # (e.g., during concurrent updates or corrections)
            stmt = stmt.order_by(
                cast(Any, self.entity_class).valid_time.desc(),
                cast(Any, self.entity_class).transaction_time.desc(),
            )

        stmt = stmt.limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def _apply_bitemporal_filter(self, stmt: Any, as_of: datetime) -> Any:
        """Apply standardized bitemporal WHERE clauses to a statement.

        Filters for:
        - valid_time contains as_of (time travel based on business validity)
        - deleted_at IS NULL OR deleted_at > as_of

        Note: Time travel queries are based on valid_time only. The transaction_time
        dimension is used for audit/correction tracking but does not filter list results.
        For overlapping valid_time ranges (corrections), the latest transaction_time
        version should be used - this is handled by DISTINCT ON in branch mode filter
        or by ordering in the specific service method.
        """
        from typing import Any, cast

        from sqlalchemy import cast as sql_cast
        from sqlalchemy import func, or_
        from sqlalchemy.dialects.postgresql import TIMESTAMP

        # CRITICAL FIX: Cast as_of to TIMESTAMP(timezone=True) to ensure proper timezone handling
        # when comparing with TSTZRANGE columns. Without this, PostgreSQL treats
        # the datetime as "timestamp without time zone" and comparison fails.
        as_of_tstz = sql_cast(as_of, TIMESTAMP(timezone=True))

        return stmt.where(
            # Check as_of is within valid_time range (time travel by business validity)
            cast(Any, self.entity_class).valid_time.op("@>")(as_of_tstz),
            # CRITICAL: Also check as_of >= lower bound (entity existed)
            func.lower(cast(Any, self.entity_class).valid_time) <= as_of_tstz,
            # TEMPORAL DELETE CHECK: Entity visible if not deleted, or deleted AFTER as_of
            or_(
                cast(Any, self.entity_class).deleted_at.is_(None),
                cast(Any, self.entity_class).deleted_at > as_of_tstz,
            ),
        )

    def _apply_branch_mode_filter(
        self,
        stmt: Any,
        branch: str,
        branch_mode: "BranchMode | None",
        as_of: datetime | None = None,
    ) -> Any:
        """Apply branch mode filtering （ISOLATED vs MERGE) to a statement.

        For ISOLATED mode: Filters to only the specified branch.
        For MERGED mode: Uses DISTINCT ON to merge main branch with specified branch,
        with branch taking precedence over main for entities that exist in both.

        Also handles deleted entities - entities deleted on current branch
        do NOT fall back to main branch.

        Args:
            stmt: SQLAlchemy statement to filter
            branch: Current branch name
            branch_mode: ISOLATED (isolated) or MERGED (composite)
            as_of: Optional timestamp for time-travel queries

        Returns:
            Filtered statement with DISTINCT ON applied for MERGED mode

        Note:
            This method is only applicable to entities that support branching
            (those with a 'branch' column). For non-branchable entities, it
            will apply ISOLATED filtering (branch == :branch).
        """
        from typing import Any, cast

        from sqlalchemy import case, or_, select

        # Check if entity supports branching (has 'branch' attribute)
        if not hasattr(self.entity_class, "branch"):
            # Non-branchable entity: apply simple branch filter (or no filter if always main)
            return stmt.where(cast(Any, self.entity_class).branch == branch)

        # Import BranchMode locally to avoid circular imports
        from app.core.versioning.enums import BranchMode

        if branch_mode is None:
            branch_mode = BranchMode.ISOLATED

        # Get root field name (e.g., "wbe_id", "project_id")
        root_field = self._get_root_field_name()

        if branch_mode == BranchMode.MERGED and branch != "main":
            # MERGED MODE: Use DISTINCT ON with branch precedence
            # Filter to include both current branch AND main
            stmt = stmt.where(cast(Any, self.entity_class).branch.in_([branch, "main"]))

            # Exclude main branch entities that were deleted on current branch
            deleted_root_ids_subq = (
                select(getattr(self.entity_class, root_field))
                .where(
                    cast(Any, self.entity_class).branch == branch,
                    cast(Any, self.entity_class).deleted_at.is_not(None),
                )
                .distinct()
            )

            # Exclude main branch entities that have a deleted version on current branch
            # Logic: Include entity if (it's on current branch) OR (root_id NOT in deleted list)
            stmt = stmt.where(
                or_(
                    cast(Any, self.entity_class).branch == branch,
                    ~getattr(self.entity_class, root_field).in_(
                        deleted_root_ids_subq.scalar_subquery()
                    ),
                ),
            )

            # Apply DISTINCT ON with branch precedence ordering
            # The CASE expression returns 0 for current branch, 1 for main
            # We want current branch (0) to come first, then main (1)
            stmt = stmt.order_by(
                getattr(self.entity_class, root_field),
                case((cast(Any, self.entity_class).branch == branch, 0), else_=1),
                # Then by valid_time descending (newest first)
                cast(Any, self.entity_class).valid_time.desc(),
                # Then by transaction_time descending as tiebreaker for deterministic ordering
                # when multiple rows have the same valid_time (e.g., concurrent updates/corrections)
                cast(Any, self.entity_class).transaction_time.desc(),
            )

            # Apply DISTINCT ON root_id
            stmt = stmt.distinct(getattr(self.entity_class, root_field))

            return stmt
        else:
            # ISOLATED MODE: Only query the specified branch (current behavior)
            return stmt.where(cast(Any, self.entity_class).branch == branch)

    def _apply_bitemporal_filter_for_time_travel(
        self, stmt: Any, as_of: datetime
    ) -> Any:
        """Apply bitemporal filter for single-entity time-travel queries.

        Uses System Time Travel semantics:
        - valid_time contains as_of
        - transaction_time contains as_of (not just open-ended)
        - deleted_at IS NULL OR deleted_at > as_of

        This differs from _apply_bitemporal_filter which uses Current Knowledge
        semantics (transaction_time.upper IS NULL) for list operations.
        """
        from typing import Any, cast

        from sqlalchemy import cast as sql_cast
        from sqlalchemy import func, or_
        from sqlalchemy.dialects.postgresql import TIMESTAMP

        # CRITICAL FIX: Cast as_of to TIMESTAMP(timezone=True) to ensure proper timezone handling
        # when comparing with TSTZRANGE columns. Without this, PostgreSQL treats
        # the datetime as "timestamp without time zone" and comparison fails.
        as_of_tstz = sql_cast(as_of, TIMESTAMP(timezone=True))

        return stmt.where(
            # Check as_of is within valid_time range
            cast(Any, self.entity_class).valid_time.op("@>")(as_of_tstz),
            # CRITICAL: Also check as_of >= lower bound (entity existed)
            func.lower(cast(Any, self.entity_class).valid_time) <= as_of_tstz,
            # TRANSACTION TIME: System Time Travel semantics for time-travel queries.
            # Check that as_of is within the transaction_time range, not just open-ended.
            # This allows querying historical versions that have been superseded.
            cast(Any, self.entity_class).transaction_time.op("@>")(as_of_tstz),
            # CRITICAL: Also check as_of >= lower bound (version existed)
            func.lower(cast(Any, self.entity_class).transaction_time) <= as_of_tstz,
            # TEMPORAL DELETE CHECK: Entity visible if not deleted, or deleted AFTER as_of
            or_(
                cast(Any, self.entity_class).deleted_at.is_(None),
                cast(Any, self.entity_class).deleted_at > as_of_tstz,
            ),
        )

    async def _is_deleted_on_branch(
        self, entity_id: UUID, as_of: datetime | None, branch: str
    ) -> bool:
        """Check if entity was explicitly deleted on branch at timestamp.

        CRITICAL: Must check temporal aspect - only returns True if deleted_at <= as_of.
        This prevents incorrect fallback prevention when entity is deleted AFTER the query time.
        """
        from typing import Any, cast

        from sqlalchemy import cast as sql_cast
        from sqlalchemy.dialects.postgresql import TIMESTAMP

        root_field = self._get_root_field_name()

        # Check for deleted version on this branch
        conditions = [
            getattr(self.entity_class, root_field) == entity_id,
            cast(Any, self.entity_class).deleted_at.is_not(None),  # IS deleted
        ]

        if as_of:
            as_of_tstz = sql_cast(as_of, TIMESTAMP(timezone=True))
            conditions.append(cast(Any, self.entity_class).deleted_at <= as_of_tstz)

        stmt = select(self.entity_class).where(*conditions)

        # Only filter by branch if the entity has a branch attribute
        if hasattr(self.entity_class, "branch"):
            stmt = stmt.where(cast(Any, self.entity_class).branch == branch)

        stmt = stmt.limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def create(
        self,
        actor_id: UUID,
        root_id: UUID | None = None,
        control_date: datetime | None = None,
        **fields: Any,
    ) -> TVersionable:
        """Create new versioned entity."""
        from uuid import uuid4

        from app.core.versioning.commands import CreateVersionCommand

        # Determine the expected root field name (e.g. user_id)
        root_field = self._get_root_field_name()

        # If root_id not explicitly passed, try to find it in fields (using domain name)
        if root_id is None:
            if root_field in fields:
                root_id = fields.pop(root_field)
            else:
                root_id = uuid4()

        # Inject domain-specific ID into fields for the model to use
        fields[root_field] = root_id

        # Ensure 'root_id' is NOT in fields.
        if "root_id" in fields:
            del fields["root_id"]

        cmd = CreateVersionCommand(
            entity_class=self.entity_class,
            root_id=root_id,
            actor_id=actor_id,
            control_date=control_date,
            **fields,
        )
        return await cmd.execute(self.session)

    async def update(
        self,
        entity_id: UUID,
        actor_id: UUID,
        control_date: datetime | None = None,
        **updates: Any,
    ) -> TVersionable:
        """Update entity (creates new version)."""
        from app.core.versioning.commands import UpdateVersionCommand

        cmd = UpdateVersionCommand(
            entity_class=self.entity_class,
            root_id=entity_id,
            actor_id=actor_id,
            control_date=control_date,
            **updates,
        )
        return await cmd.execute(self.session)

    async def soft_delete(
        self, entity_id: UUID, actor_id: UUID, control_date: datetime | None = None
    ) -> None:
        """Soft delete entity."""
        from app.core.versioning.commands import SoftDeleteCommand

        cmd = SoftDeleteCommand(
            entity_class=self.entity_class,
            root_id=entity_id,
            actor_id=actor_id,
            control_date=control_date,
        )
        await cmd.execute(self.session)

    async def get_history(self, root_id: UUID) -> list[TVersionable]:
        """Get all versions of an entity with joined creator name."""
        from typing import Any, cast

        # Introspect root field name (e.g. project_id, wbe_id, user_id, department_id)
        root_field = self._get_root_field_name()

        stmt = (
            select(self.entity_class)
            .where(
                getattr(self.entity_class, root_field) == root_id,
                cast(Any, self.entity_class).deleted_at.is_(None),
            )
            .order_by(cast(Any, self.entity_class).transaction_time.desc())
        )

        result = await self.session.execute(stmt)
        history = list(result.scalars().all())
        # Resolve created_by_name (batched) and derive created_at in one pass.
        await self._populate_read_fields(history)
        return history
