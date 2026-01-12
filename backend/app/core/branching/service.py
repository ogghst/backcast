"""Service for branchable entities (EVCS Core).

Extends the command pattern to provide business-level operations for
entities implementing BranchableProtocol (e.g. Projects).
"""

from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.branching.commands import (
    BranchableSoftDeleteCommand,
    CreateBranchCommand,
    MergeBranchCommand,
    RevertCommand,
    UpdateCommand,
)
from app.core.versioning.commands import CreateVersionCommand
from app.core.versioning.enums import BranchMode
from app.models.protocols import BranchableProtocol


class BranchableService[TBranchable: BranchableProtocol]:
    """Service for managing branchable entities."""

    def __init__(self, entity_class: type[TBranchable], session: AsyncSession) -> None:
        self.entity_class = entity_class
        self.session = session

    async def get_by_id(self, entity_id: UUID) -> TBranchable | None:
        """Get specific version by its version ID (primary key)."""
        return await self.session.get(self.entity_class, entity_id)

    async def get_current(
        self, root_id: UUID, branch: str = "main"
    ) -> TBranchable | None:
        """Get the current active version for a root entity on a specific branch."""
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
                    func.current_timestamp()
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
        """Create the initial version of an entity (new root)."""
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
        """
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
        - valid_time contains as_of
        - transaction_time contains as_of
        - deleted_at IS NULL OR deleted_at > as_of
        """
        from typing import Any, cast

        from sqlalchemy import func, or_

        return stmt.where(
            # Check as_of is within valid_time range
            cast(Any, self.entity_class).valid_time.op("@>")(as_of),
            # CRITICAL: Also check as_of >= lower bound (entity existed)
            func.lower(cast(Any, self.entity_class).valid_time) <= as_of,

            # TRANSACTION TIME: We use "Current Knowledge" semantics for lists.
            # We want the latest "truth" about the 'as_of' time.
            # So we check that the row has not been superseded (transaction_time upper bound is NULL).
            func.upper(cast(Any, self.entity_class).transaction_time).is_(None),

            # TEMPORAL DELETE CHECK: Entity visible if not deleted, or deleted AFTER as_of
            or_(
                cast(Any, self.entity_class).deleted_at.is_(None),
                cast(Any, self.entity_class).deleted_at > as_of,
            ),
        )

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
        class_name = self.entity_class.__name__.lower()
        if class_name.endswith("version"):
            class_name = class_name[:-7]
        root_field = f"{class_name}_id"

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
        class_name = self.entity_class.__name__.lower()
        if class_name.endswith("version"):
            class_name = class_name[:-7]
        root_field = f"{class_name}_id"

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
