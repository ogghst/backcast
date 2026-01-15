"""Service for branchable entities (EVCS Core).

Extends the command pattern to provide business-level operations for
entities implementing BranchableProtocol (e.g. Projects).
"""

import re
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.branching.commands import (
    BranchableSoftDeleteCommand,
    CreateBranchCommand,
    MergeBranchCommand,
    RevertCommand,
    UpdateCommand,
)
from app.core.branching.exceptions import BranchLockedException
from app.core.versioning.commands import CreateVersionCommand
from app.core.versioning.enums import BranchMode
from app.models.protocols import BranchableProtocol


class BranchableService[TBranchable: BranchableProtocol]:
    """Service for managing branchable entities."""

    def __init__(self, entity_class: type[TBranchable], session: AsyncSession) -> None:
        self.entity_class = entity_class
        self.session = session

    def _get_root_field_name(self) -> str:
        """Derive the root column name from the entity class name.

        Handles:
        - Project -> project_id
        - CostElement -> cost_element_id
        - WBE -> wbe_id
        """
        name = self.entity_class.__name__
        if name.endswith("Version"):
            name = name[:-7]

        # CamelCase to snake_case
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        snake_name = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

        return f"{snake_name}_id"

    async def _check_branch_lock(
        self,
        root_id: UUID,
        branch: str,
        entity_id: UUID | None = None,
    ) -> None:
        """Check if branch is locked and raise exception if so.

        This method enforces branch locks at the service level, preventing
        modifications to entities on locked branches. Branches are typically
        locked during Change Order review/approval to prevent concurrent
        modifications while the change is being evaluated.

        Args:
            root_id: Root entity identifier (used to get entity and project_id)
            branch: Branch name to check
            entity_id: Optional entity ID for error messaging

        Raises:
            BranchLockedException: If the branch is locked

        Note:
            Main branch is never locked, so this check is skipped for branch="main".
        """
        # Main branch is never locked
        if branch == "main":
            return

        # Get the current entity to extract project_id
        entity = await self.get_current(root_id, branch)
        if entity is None:
            # Entity doesn't exist yet, no lock check needed
            return

        # Get project_id from entity (all branchable entities have project_id)
        project_id = getattr(entity, "project_id", None)
        if project_id is None:
            # Should not happen for properly configured entities
            return

        # Check if branch is locked using BranchService
        from app.services.branch_service import BranchService

        branch_service = BranchService(self.session)
        try:
            db_branch = await branch_service.get_by_name_and_project(branch, project_id)
            if db_branch.locked:
                entity_type = self.entity_class.__name__
                raise BranchLockedException(
                    branch=branch,
                    entity_type=entity_type,
                    entity_id=str(entity_id) if entity_id else str(root_id),
                )
        except NoResultFound:
            # Branch doesn't exist in database yet, allow operation
            # (This can happen during initial branch creation)
            pass

    async def _check_branch_lock_for_create(
        self,
        root_id: UUID,
        branch: str,
        data: dict[str, Any],
    ) -> None:
        """Check if branch is locked during entity creation.

        Similar to _check_branch_lock but extracts project_id from the
        data dictionary rather than from an existing entity.

        Args:
            root_id: Root entity identifier
            branch: Branch name to check
            data: Entity data dictionary (must contain project_id)

        Raises:
            BranchLockedException: If the branch is locked
        """
        # Main branch is never locked
        if branch == "main":
            return

        # Get project_id from data (all branchable entities require project_id)
        project_id = data.get("project_id")
        if project_id is None:
            # No project_id in data, can't check lock
            return

        # Check if branch is locked using BranchService
        from app.services.branch_service import BranchService

        branch_service = BranchService(self.session)
        try:
            db_branch = await branch_service.get_by_name_and_project(branch, project_id)
            if db_branch.locked:
                entity_type = self.entity_class.__name__
                raise BranchLockedException(
                    branch=branch,
                    entity_type=entity_type,
                    entity_id=str(root_id),
                )
        except NoResultFound:
            # Branch doesn't exist in database yet, allow operation
            pass

    async def get_by_id(self, entity_id: UUID) -> TBranchable | None:
        """Get specific version by its version ID (primary key)."""
        return await self.session.get(self.entity_class, entity_id)

    async def get_current(
        self, root_id: UUID, branch: str = "main"
    ) -> TBranchable | None:
        """Get the current active version for a root entity on a specific branch.

        Uses clock_timestamp() instead of current_timestamp() because within
        a transaction, current_timestamp() returns the transaction start time,
        which may be before the valid_time lower bound of recently created records.
        """
        # Helper to get root field name
        class_name = self.entity_class.__name__.lower()
        if class_name.endswith("version"):
            class_name = class_name[:-7]
        root_field = f"{class_name}_id"

        stmt = (
            select(self.entity_class)
            .where(
                getattr(self.entity_class, root_field) == root_id,
                cast(Any, self.entity_class).branch == branch,
                cast(Any, self.entity_class).valid_time.op("@>")(
                    func.clock_timestamp()
                ),
                cast(Any, self.entity_class).deleted_at.is_(None),
            )
            .order_by(cast(Any, self.entity_class).valid_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_root(
        self,
        root_id: UUID,
        actor_id: UUID,
        control_date: datetime | None = None,
        branch: str = "main",
        **data: Any,
    ) -> TBranchable:
        """Create the initial version of an entity (new root).

        Raises:
            BranchLockedException: If the branch is locked
        """
        # Check if branch is locked before allowing create
        await self._check_branch_lock_for_create(root_id, branch, data)

        # Ensure root_id field is in data
        class_name = self.entity_class.__name__.lower()
        if class_name.endswith("version"):
            class_name = class_name[:-7]
        root_field = f"{class_name}_id"

        data[root_field] = root_id

        cmd = CreateVersionCommand(
            entity_class=self.entity_class,
            root_id=root_id,
            actor_id=actor_id,
            control_date=control_date,
            branch=branch,
            **data,
        )
        return await cmd.execute(self.session)

    async def update(
        self,
        root_id: UUID,
        actor_id: UUID,
        branch: str,
        control_date: datetime | None = None,
        **updates: Any,
    ) -> TBranchable:
        """Update entity on a specific branch (creates new version)."""
        # Check if branch is locked before allowing update
        await self._check_branch_lock(root_id, branch, root_id)

        cmd = UpdateCommand(
            entity_class=self.entity_class,
            root_id=root_id,
            actor_id=actor_id,
            branch=branch,
            control_date=control_date,
            updates=updates,
        )
        return await cmd.execute(self.session)

    async def create_branch(
        self,
        root_id: UUID,
        actor_id: UUID,
        new_branch: str,
        from_branch: str = "main",
        control_date: datetime | None = None,
    ) -> TBranchable:
        """Create a new branch from an existing branch.

        Args:
            root_id: Root entity identifier
            actor_id: User creating the branch
            new_branch: Name of the new branch
            from_branch: Source branch to copy from (default: "main")
            control_date: Optional control date for valid_time (defaults to now)
        """
        cmd = CreateBranchCommand(
            entity_class=self.entity_class,
            root_id=root_id,
            actor_id=actor_id,
            new_branch=new_branch,
            from_branch=from_branch,
            control_date=control_date,
        )
        return await cmd.execute(self.session)

    async def merge_branch(
        self, root_id: UUID, actor_id: UUID, source_branch: str, target_branch: str
    ) -> TBranchable:
        """Merge source branch into target branch."""
        cmd = MergeBranchCommand(
            entity_class=self.entity_class,
            root_id=root_id,
            actor_id=actor_id,
            source_branch=source_branch,
            target_branch=target_branch,
        )
        return await cmd.execute(self.session)

    async def revert(
        self,
        root_id: UUID,
        actor_id: UUID,
        branch: str,
        to_version_id: UUID | None = None,
    ) -> TBranchable:
        """Revert branch to a previous state."""
        cmd = RevertCommand(
            entity_class=self.entity_class,
            root_id=root_id,
            actor_id=actor_id,
            branch=branch,
            to_version_id=to_version_id,
        )
        return await cmd.execute(self.session)

    async def soft_delete(
        self,
        root_id: UUID,
        actor_id: UUID,
        branch: str = "main",
        control_date: datetime | None = None,
    ) -> TBranchable:
        """Soft delete a branchable entity on a specific branch.

        Args:
            root_id: Root entity identifier
            actor_id: User performing the deletion
            branch: Branch to delete from (default: "main")
            control_date: Optional control date for deletion timestamp

        Returns:
            The deleted entity (marked with deleted_at)

        Raises:
            ValueError: If no active version found on the specified branch
            BranchLockedException: If the branch is locked
        """
        # Check if branch is locked before allowing delete
        await self._check_branch_lock(root_id, branch, root_id)

        cmd = BranchableSoftDeleteCommand(
            entity_class=self.entity_class,
            root_id=root_id,
            actor_id=actor_id,
            branch=branch,
            control_date=control_date,
        )
        return await cmd.execute(self.session)

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

        from sqlalchemy import func, or_

        return stmt.where(
            # Check as_of is within valid_time range (time travel by business validity)
            cast(Any, self.entity_class).valid_time.op("@>")(as_of),
            # CRITICAL: Also check as_of >= lower bound (entity existed)
            func.lower(cast(Any, self.entity_class).valid_time) <= as_of,

            # TEMPORAL DELETE CHECK: Entity visible if not deleted, or deleted AFTER as_of
            or_(
                cast(Any, self.entity_class).deleted_at.is_(None),
                cast(Any, self.entity_class).deleted_at > as_of,
            ),
        )

    def _apply_branch_mode_filter(
        self,
        stmt: Any,
        branch: str,
        branch_mode: BranchMode,
        as_of: datetime | None = None,
    ) -> Any:
        """Apply branch mode filtering (STRICT vs MERGE) to a statement.

        For STRICT mode: Filters to only the specified branch.
        For MERGE mode: Uses DISTINCT ON to merge main branch with specified branch,
        with branch taking precedence over main for entities that exist in both.

        Args:
            stmt: SQLAlchemy statement to filter
            branch: Current branch name
            branch_mode: STRICT (isolated) or MERGE (composite)
            as_of: Optional timestamp for time-travel queries

        Returns:
            Filtered statement with DISTINCT ON applied for MERGE mode
        """
        from typing import Any, cast

        from sqlalchemy import case, or_

        # Get root field name (e.g., "wbe_id", "project_id", "cost_element_id")
        root_field = self._get_root_field_name()

        if branch_mode == BranchMode.MERGE and branch != "main":
            # MERGE MODE: Use DISTINCT ON with branch precedence
            # Filter to include both current branch AND main
            stmt = stmt.where(cast(Any, self.entity_class).branch.in_([branch, "main"]))

            # Exclude main branch entities that were deleted on current branch
            # by adding a NOT EXISTS condition
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
                    cast(Any, self.entity_class).branch == branch,  # Include current branch
                    ~getattr(self.entity_class, root_field).in_(
                        deleted_root_ids_subq.scalar_subquery()
                    ),  # Exclude main if deleted on current branch
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
            )

            # Apply DISTINCT ON root_id
            stmt = stmt.distinct(getattr(self.entity_class, root_field))

            return stmt
        else:
            # STRICT MODE: Only query the specified branch (current behavior)
            return stmt.where(cast(Any, self.entity_class).branch == branch)

    async def get_as_of(
        self,
        entity_id: UUID,
        as_of: datetime,
        branch: str = "main",
        branch_mode: BranchMode | None = None,
    ) -> TBranchable | None:
        """Time travel: Get active version at specific timestamp on a branch.

        Args:
            entity_id: Root entity ID
            as_of: Timestamp to query
            branch: Branch name (default: main)
            branch_mode: Resolution mode (STRICT=only branch, MERGE=fallback to main)
        """
        # Helper to get root field name
        root_field = self._get_root_field_name()

        # Base conditions for ID and Time
        conditions = [
            getattr(self.entity_class, root_field) == entity_id,
            # Valid Time Coverage
            cast(Any, self.entity_class).valid_time.op("@>")(as_of),
            func.lower(cast(Any, self.entity_class).valid_time) <= as_of,
            # Transaction Time Coverage
            cast(Any, self.entity_class).transaction_time.op("@>")(as_of),
            func.lower(cast(Any, self.entity_class).transaction_time) <= as_of,
            # Deleted At Check
            func.coalesce(cast(Any, self.entity_class).deleted_at, datetime.max) > as_of,
        ]

        # Handle Branch Mode
        if branch_mode == BranchMode.MERGE and branch != "main":
            # Search in both branch and main, prioritizing the requested branch
            stmt = (
                select(self.entity_class)
                .where(
                    *conditions,
                    cast(Any, self.entity_class).branch.in_([branch, "main"]),
                )
                .order_by(
                    # Prioritize requested branch (0) over main (1)
                    case((cast(Any, self.entity_class).branch == branch, 0), else_=1),
                    # Then by valid time
                    cast(Any, self.entity_class).valid_time.desc(),
                )
                .limit(1)
            )
        else:
            # STRICT mode or already on main: exact branch match
            stmt = (
                select(self.entity_class)
                .where(
                    *conditions,
                    cast(Any, self.entity_class).branch == branch,
                )
                .limit(1)
            )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_history(self, root_id: UUID) -> list[TBranchable]:
        """Get all versions of an entity with joined creator name."""
        from app.models.domain.user import User

        # Helper to get root field name
        root_field = self._get_root_field_name()

        # Creator lookup subquery
        UserAlias = cast(Any, User)
        creator_subq = (
            select(UserAlias.user_id, UserAlias.full_name)
            .distinct(UserAlias.user_id)
            .order_by(UserAlias.user_id, UserAlias.transaction_time.desc())
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
            entity.created_by_name = row[1]
            history.append(entity)

        return history

    async def list_branches(
        self,
        root_id: UUID,
        as_of: datetime | None = None,
    ) -> list[str]:
        """Get all branch names for an entity.

        Args:
            root_id: The root entity ID
            as_of: Optional time travel timestamp

        Returns:
            List of distinct branch names where this entity exists

        Example:
            >>> branches = await service.list_branches(project_id)
            >>> print(branches)  # ['main', 'co-123', 'co-456']
        """
        root_field = self._get_root_field_name()

        # Build base statement
        stmt = select(self.entity_class.branch).where(
            getattr(self.entity_class, root_field) == root_id,
        )

        # Apply bitemporal filtering if as_of is provided
        if as_of:
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            # Current state: only non-deleted, currently valid versions
            stmt = stmt.where(
                cast(Any, self.entity_class).deleted_at.is_(None),
                func.upper(cast(Any, self.entity_class).valid_time).is_(None),
            )

        # Get distinct branch names
        stmt = stmt.distinct().order_by(self.entity_class.branch)
        result = await self.session.execute(stmt)
        return [row[0] for row in result.all()]

    async def _detect_merge_conflicts(
        self,
        root_id: UUID,
        source_branch: str,
        target_branch: str = "main",
    ) -> list[dict[str, Any]]:
        """Detect merge conflicts between source and target branches.

        A conflict occurs when both branches have modified the same entity
        since they diverged, and they have different values for any field.

        Args:
            root_id: Root entity ID
            source_branch: Source branch name (e.g., "co-123")
            target_branch: Target branch name (default: "main")

        Returns:
            List of conflict dictionaries. Empty if no conflicts.

        Raises:
            ValueError: If source or target branch doesn't have a current version
        """
        from typing import Any

        # Get current versions on both branches
        source = await self.get_current(root_id=root_id, branch=source_branch)
        if not source:
            raise ValueError(f"No current version on source branch '{source_branch}'")

        target = await self.get_current(root_id=root_id, branch=target_branch)
        if not target:
            raise ValueError(f"No current version on target branch '{target_branch}'")

        # Find the divergence point by walking parent chains
        # The divergence point is the common ancestor where branches split
        source_ancestors: set[UUID] = set()
        current = source
        while current.parent_id:
            source_ancestors.add(current.parent_id)
            parent = await self.session.get(self.entity_class, current.parent_id)
            if not parent:
                break
            current = cast(Any, parent)

        # Find common ancestor in target's parent chain
        target_ancestors: list[UUID] = []
        current = target
        while current.parent_id:
            target_ancestors.append(current.parent_id)
            if current.parent_id in source_ancestors:
                # Found common ancestor
                divergence_point_id = current.parent_id
                break
            parent = await self.session.get(self.entity_class, current.parent_id)
            if not parent:
                break
            current = cast(Any, parent)
        else:
            # No common ancestor found (shouldn't happen in normal workflow)
            # Assume no conflict if they're completely unrelated
            return []

        # Get the divergence point version
        divergence_point = await self.session.get(self.entity_class, divergence_point_id)
        if not divergence_point:
            return []

        # Check if both branches modified since divergence
        # If source branch was created directly from divergence (no intermediate changes),
        # and target hasn't changed since divergence, no conflict
        if source.parent_id == divergence_point_id and target.parent_id == divergence_point_id:
            # Both point to same parent - check if they diverged from same state
            # This is a "new branch with changes" vs "unchanged target" scenario
            # No conflict if target is the divergence point (hasn't been modified)
            return []

        # Compare fields to detect conflicts
        # Fields to compare: exclude system fields
        system_fields = {
            "id",
            "valid_time",
            "transaction_time",
            "deleted_at",
            "created_by",
            "deleted_by",
            "branch",
            "parent_id",
            "merge_from_branch",
            self._get_root_field_name(),  # e.g., "project_id"
        }

        conflicts: list[dict[str, Any]] = []

        # Get all columns for the entity
        for column in self.entity_class.__table__.columns:
            field_name = column.name

            if field_name in system_fields:
                continue

            source_value = getattr(source, field_name, None)
            target_value = getattr(target, field_name, None)
            divergence_value = getattr(divergence_point, field_name, None)

            # Conflict if:
            # 1. Source value differs from divergence (source modified the field)
            # 2. Target value differs from divergence (target modified the field)
            # 3. Source and target have different values
            if (
                source_value != divergence_value
                and target_value != divergence_value
                and source_value != target_value
            ):
                conflicts.append({
                    "entity_type": self.entity_class.__name__,
                    "entity_id": str(root_id),
                    "field": field_name,
                    "source_branch": source_branch,
                    "target_branch": target_branch,
                    "source_value": str(source_value) if source_value is not None else None,
                    "target_value": str(target_value) if target_value is not None else None,
                })

        return conflicts

    async def compare_branches(
        self,
        root_id: UUID,
        branch_a: str,
        branch_b: str,
        as_of: datetime | None = None,
    ) -> dict[str, TBranchable | None]:
        """Compare entity state between two branches.

        Args:
            root_id: The root entity ID
            branch_a: First branch name
            branch_b: Second branch name
            as_of: Optional time travel timestamp

        Returns:
            Dict with 'branch_a' and 'branch_b' keys containing current versions.
            Returns None for branches where the entity doesn't exist.

        Example:
            >>> comparison = await service.compare_branches(
            ...     project_id, "main", "co-123"
            ... )
            >>> print(comparison['branch_a'].name)
            >>> print(comparison['branch_b'].name)
        """
        # Get version from branch_a
        if as_of:
            version_a = await self.get_as_of(
                entity_id=root_id,
                as_of=as_of,
                branch=branch_a,
                branch_mode=BranchMode.STRICT,
            )
        else:
            version_a = await self.get_current(root_id=root_id, branch=branch_a)

        # Get version from branch_b
        if as_of:
            version_b = await self.get_as_of(
                entity_id=root_id,
                as_of=as_of,
                branch=branch_b,
                branch_mode=BranchMode.STRICT,
            )
        else:
            version_b = await self.get_current(root_id=root_id, branch=branch_b)

        return {
            "branch_a": version_a,
            "branch_b": version_b,
        }
