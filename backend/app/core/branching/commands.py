"""Generic commands for branchable entities.

Moved from app.core.versioning.commands.
"""

from datetime import UTC, datetime
from typing import Any, TypeVar, cast
from uuid import UUID

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.versioning.commands import VersionedCommandABC
from app.core.versioning.exceptions import OverlappingVersionError
from app.models.protocols import BranchableProtocol

TBranchable = TypeVar("TBranchable", bound=BranchableProtocol)


class BranchCommandABC(VersionedCommandABC[TBranchable]):
    """ABC for branchable entity commands.

    Type parameter TBranchable must satisfy BranchableProtocol.
    """

    branch: str = "main"

    async def _get_current_on_branch(
        self, session: AsyncSession, branch: str
    ) -> TBranchable | None:
        """Get current version on specific branch.

        Uses open-ended valid_time check (upper IS NULL) for reliability,
        consistent with VersionedCommandABC._get_current().
        Excludes empty ranges to avoid selecting invalid versions.
        """
        stmt = (
            select(self.entity_class)
            .where(
                getattr(self.entity_class, self._root_field_name()) == self.root_id,
                cast(Any, self.entity_class).branch == branch,
                func.upper(cast(Any, self.entity_class).valid_time).is_(None),
                func.not_(
                    func.isempty(self.entity_class.valid_time)
                ),  # Exclude empty ranges
                cast(Any, self.entity_class).deleted_at.is_(None),
            )
            .order_by(cast(Any, self.entity_class).valid_time.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def _check_overlap(
        self,
        session: AsyncSession,
        start_time: datetime,
        branch: str,
        exclude_version_id: UUID | None = None,
    ) -> None:
        """Check for overlapping versions on the branch.

        Ensures no active version exists that would overlap with a new version
        starting at `start_time` and extending to infinity.
        """
        stmt = select(self.entity_class).where(
            getattr(self.entity_class, self._root_field_name()) == self.root_id,
            cast(Any, self.entity_class).branch == branch,
            cast(Any, self.entity_class).deleted_at.is_(None),
        )

        if exclude_version_id:
            stmt = stmt.where(cast(Any, self.entity_class).id != exclude_version_id)

        # Check for any version that ends after start_time or is open-ended
        stmt = stmt.where(
            or_(
                func.upper(cast(Any, self.entity_class).valid_time) > start_time,
                func.upper(cast(Any, self.entity_class).valid_time).is_(None),
            )
        )

        result = await session.execute(stmt.limit(1))
        existing = result.scalar_one_or_none()

        if existing:
            raise OverlappingVersionError(
                root_id=str(self.root_id),
                branch=branch,
                new_range=f"[{start_time.isoformat()}, NULL)",
                existing_range=getattr(existing, "valid_time", "unknown"),
            )


class CreateBranchCommand(BranchCommandABC[TBranchable]):
    """Create a new branch from existing branch."""

    def __init__(
        self,
        entity_class: type[TBranchable],
        root_id: UUID,
        actor_id: UUID,
        new_branch: str,
        from_branch: str = "main",
        control_date: datetime | None = None,
    ) -> None:
        super().__init__(entity_class, root_id, actor_id)
        self.new_branch = new_branch
        self.from_branch = from_branch
        self.control_date = control_date or datetime.now(UTC)

    async def execute(self, session: AsyncSession) -> TBranchable:
        """Clone current version to new branch.

        uses control_date for valid_time, and clock_timestamp() for transaction_time
        to ensure bitemporal correctness.
        """
        # 0. Check for overlaps on new branch
        await self._check_overlap(session, self.control_date, self.new_branch)

        # Get current version from source branch
        source = await self._get_current_on_branch(session, self.from_branch)
        if not source:
            raise ValueError(
                f"No active version on branch {self.from_branch} for {self.root_id}"
            )

        # Clone to new branch
        branched = cast(
            TBranchable, source.clone(branch=self.new_branch, parent_id=source.id)
        )
        session.add(branched)
        await session.flush()  # Get ID assigned

        # Set valid_time to control_date, transaction_time to clock_timestamp()
        tablename = str(getattr(self.entity_class, "__tablename__", ""))
        stmt = text(
            f"""
            UPDATE {tablename}
            SET
                valid_time = tstzrange(:control_date, NULL, '[]'),
                transaction_time = tstzrange(clock_timestamp(), NULL, '[]')
            WHERE id = :version_id
            """
        )
        await session.execute(
            stmt, {"control_date": self.control_date, "version_id": branched.id}
        )
        await session.flush()
        await session.refresh(branched)
        return branched


class UpdateCommand(BranchCommandABC[TBranchable]):
    """Update branchable entity on specific branch."""

    def __init__(
        self,
        entity_class: type[TBranchable],
        root_id: UUID,
        actor_id: UUID,
        updates: dict[str, Any],
        branch: str = "main",
        control_date: datetime | None = None,
    ) -> None:
        super().__init__(entity_class, root_id, actor_id)
        self.updates = updates
        self.branch = branch
        # CRITICAL FIX: Don't default control_date to datetime.now(UTC)
        # Keep it as None when not provided, to avoid creating unnecessary remainder versions
        self.control_date = control_date

    async def execute(self, session: AsyncSession) -> TBranchable:
        """Close current on branch and create new."""
        # CRITICAL FIX: Generate a single timestamp for the entire update operation
        # This ensures all temporal operations use consistent timestamps and avoids
        # creating empty ranges or duplicate current versions
        update_timestamp = datetime.now(UTC)

        # 1. Get current on branch
        # If not on a change order branch and entity doesn't exist there,
        # automatically fall back to main branch (for first edit in a CO branch)
        current = await self._get_current_on_branch(session, self.branch)
        if not current and self.branch != "main":
            # WBE doesn't exist on change order branch yet
            # Fall back to main branch to get the current version
            current = await self._get_current_on_branch(session, "main")
            if not current:
                raise ValueError(
                    f"No active version on main branch for {self.root_id}"
                )
            # The updates will create a new version on the change order branch
        elif not current:
            raise ValueError(
                f"No active version on branch {self.branch} for {self.root_id}"
            )

        # CRITICAL: Store current_id before any modifications for use in parent_id
        current_id = current.id

        if self.control_date:
            current_lower = cast(Any, current).valid_time.lower
            # NOTE: Allow control_date == current_lower for Time Machine mode
            if current_lower and self.control_date < current_lower:
                raise ValueError(
                    f"control_date ({self.control_date.isoformat()}) must be on or after "
                    f"valid_time lower bound ({current_lower.isoformat()})"
                )

            # SPLIT HISTORY: Only create remainder if there is an actual time gap
            # If control_date == current_lower, the new version completely replaces the old one
            # starting from the same time, so no "previous history" (remainder) is needed for this period.
            if self.control_date > current_lower:
                # EVCS FIX: Modify current row in-place to become the remainder
                # instead of creating a new row. This prevents duplicate rows with
                # identical data, which violates EVCS temporal patterns.
                tablename = str(getattr(self.entity_class, "__tablename__", ""))
                stmt_rem = text(
                    f"""
                    UPDATE {tablename}
                    SET
                        valid_time = tstzrange(:lower, :upper, '[)'),
                        transaction_time = tstzrange(:tx_lower, :tx_upper, '[)')
                    WHERE id = :version_id
                    """
                )
                await session.execute(
                    stmt_rem,
                    {
                        "lower": current_lower,
                        "upper": self.control_date,
                        "tx_lower": cast(Any, current).transaction_time.lower,
                        "tx_upper": update_timestamp,  # Close: remainder was corrected at this time
                        "version_id": current.id,
                    },
                )
                await session.flush()
                # Skip the _close_version call below since we already closed it
                current = None

        # 2. Clone and apply updates (Safe Clone via Core Select)
        # Fetch raw data to avoid ORM lazy-load triggers (MissingGreenlet)
        # If current was converted to remainder above, we need to refresh it first
        if current is None:
            current = await session.get(self.entity_class, current_id)
        # CRITICAL: Always set branch to self.branch to ensure new version is on correct branch
        # This is essential when current is from main but we're updating on a change order branch
        new_version = cast(
            TBranchable,
            current.clone(branch=self.branch, **self.updates, parent_id=current_id)
        )

        # 3. Close current (only if not already closed as remainder)
        if current is not None:
            await self._close_version(
                session, current, close_at_valid_time=self.control_date
            )

        # CRITICAL FIX: Use the same update_timestamp for both ranges to avoid empty ranges
        # When control_date is None (normal update), use update_timestamp for valid_time lower bound
        valid_time_lower = (
            self.control_date if self.control_date is not None else update_timestamp
        )

        # 0. Check for overlaps on current branch (excluding the version we just closed/are closing)
        # Note: We checked 'current' before closing, but _check_overlap logic looks for conflicts
        # with the NEW range [valid_time_lower, Infinity).
        # 'current' (now closed at valid_time_lower) will NOT overlap because upper=valid_time_lower.
        # But we pass exclude_version_id just to be safe and explicit.
        await self._check_overlap(
            session, valid_time_lower, self.branch, exclude_version_id=current_id
        )

        session.add(new_version)
        await session.flush()

        # 4. Set valid_time and transaction_time on new version via SQL
        # CRITICAL FIX: Use the same update_timestamp for both ranges to avoid empty ranges
        # When control_date is None (normal update), use update_timestamp for valid_time lower bound
        valid_time_lower = (
            self.control_date if self.control_date is not None else update_timestamp
        )

        tablename = str(getattr(self.entity_class, "__tablename__", ""))
        stmt = text(
            f"""
            UPDATE {tablename}
            SET
                valid_time = tstzrange(:control_date, NULL, '[]'),
                transaction_time = tstzrange(:update_timestamp, NULL, '[]')
            WHERE id = :version_id
            """
        )
        await session.execute(
            stmt,
            {
                "control_date": valid_time_lower,
                "update_timestamp": update_timestamp,
                "version_id": new_version.id,
            },
        )
        await session.flush()
        await session.refresh(new_version)

        return new_version


class MergeBranchCommand(BranchCommandABC[TBranchable]):
    """Merge source branch into target branch."""

    def __init__(
        self,
        entity_class: type[TBranchable],
        root_id: UUID,
        actor_id: UUID,
        source_branch: str,
        target_branch: str = "main",
        control_date: datetime | None = None,
    ) -> None:
        super().__init__(entity_class, root_id, actor_id)
        self.source_branch = source_branch
        self.target_branch = target_branch
        self.control_date = control_date

    async def execute(self, session: AsyncSession) -> TBranchable:
        """Merge source branch into target branch (overwrite strategy)."""
        # 1. Source
        source = await self._get_current_on_branch(session, self.source_branch)
        if not source:
            raise ValueError(
                f"Source branch {self.source_branch} not found or inactive."
            )

        # 2. Target
        # For now, enforce target existence. Later allows create-on-merge.
        target = await self._get_current_on_branch(session, self.target_branch)
        if not target:
            raise ValueError(
                f"Target branch {self.target_branch} not found or inactive."
            )

        # 3. Clone Source -> Target
        # Logic: New version on Target, content from Source, parent=Target.id
        merged = cast(
            TBranchable,
            source.clone(
                branch=self.target_branch,
                parent_id=target.id,
                merge_from_branch=self.source_branch,
            ),
        )

        # 4. Check for overlap on target branch BEFORE closing target
        # Use control_date if provided, otherwise current time
        merge_timestamp = self.control_date if self.control_date else datetime.now(UTC)
        # Exclude target version since it will be closed before the merged version is created
        await self._check_overlap(
            session, merge_timestamp, self.target_branch, exclude_version_id=target.id
        )

        # 5. Close Target
        await self._close_version(
            session, target, close_at_valid_time=merge_timestamp
        )
        session.add(merged)
        await session.flush()  # Get ID assigned

        # 6. Set valid_time and transaction_time on merged version via SQL
        tablename = str(getattr(self.entity_class, "__tablename__", ""))
        stmt = text(
            f"""
            UPDATE {tablename}
            SET
                valid_time = tstzrange(:merge_timestamp, NULL, '[]'),
                transaction_time = tstzrange(:merge_timestamp, NULL, '[]')
            WHERE id = :version_id
            """
        )
        await session.execute(
            stmt, {"merge_timestamp": merge_timestamp, "version_id": merged.id}
        )
        await session.flush()
        await session.refresh(merged)

        return merged


class RevertCommand(BranchCommandABC[TBranchable]):
    """Revert to previous version."""

    def __init__(
        self,
        entity_class: type[TBranchable],
        root_id: UUID,
        actor_id: UUID,
        branch: str = "main",
        to_version_id: UUID | None = None,
    ) -> None:
        super().__init__(entity_class, root_id, actor_id)
        self.branch = branch
        self.to_version_id = to_version_id

    async def execute(self, session: AsyncSession) -> TBranchable:
        """Revert logic implementation."""
        # 1. Get Current
        current = await self._get_current_on_branch(session, self.branch)
        if not current:
            raise ValueError(f"No active version on {self.branch} for {self.root_id}")

        # 2. Get Target Version
        target_version: TBranchable | None = None
        if self.to_version_id:
            target_version = await session.get(self.entity_class, self.to_version_id)
        elif current.parent_id:
            target_version = await session.get(self.entity_class, current.parent_id)

        if not target_version:
            raise ValueError(
                "Cannot revert: No target version specified or no parent found."
            )

        # 3. Clone Target -> New Head
        # Logic: Content from Target, but parent is Current (linear history)
        reverted = cast(
            TBranchable,
            target_version.clone(
                branch=self.branch,
                parent_id=current.id,
                merge_from_branch=None,
            ),
        )

        # 4. Check for overlap on current branch BEFORE closing current
        # Generate timestamp in Python to avoid empty ranges
        revert_timestamp = datetime.now(UTC)
        # Exclude current version since it will be closed before the new version is created
        await self._check_overlap(
            session, revert_timestamp, self.branch, exclude_version_id=current.id
        )

        # 5. Close Current
        await self._close_version(session, current)

        session.add(reverted)
        await session.flush()  # Get ID assigned

        # 6. Set valid_time and transaction_time on reverted version via SQL
        tablename = str(getattr(self.entity_class, "__tablename__", ""))
        stmt = text(
            f"""
            UPDATE {tablename}
            SET
                valid_time = tstzrange(:revert_timestamp, NULL, '[]'),
                transaction_time = tstzrange(:revert_timestamp, NULL, '[]')
            WHERE id = :version_id
            """
        )
        await session.execute(
            stmt, {"revert_timestamp": revert_timestamp, "version_id": reverted.id}
        )
        await session.flush()
        await session.refresh(reverted)

        return reverted


class BranchableSoftDeleteCommand(BranchCommandABC[TBranchable]):
    """Soft delete a branchable entity on a specific branch.

    Unlike the generic SoftDeleteCommand, this command is branch-aware
    and will only delete the current version on the specified branch.
    This is essential for entities that exist on multiple branches (e.g., Change Orders).
    """

    def __init__(
        self,
        entity_class: type[TBranchable],
        root_id: UUID,
        actor_id: UUID,
        branch: str = "main",
        control_date: datetime | None = None,
    ) -> None:
        super().__init__(entity_class, root_id, actor_id)
        self.branch = branch
        self.control_date = control_date or datetime.now(UTC)

    async def execute(self, session: AsyncSession) -> TBranchable:
        """Mark current version on specified branch as deleted."""
        current = await self._get_current_on_branch(session, self.branch)
        if not current:
            raise ValueError(
                f"No active version found on branch {self.branch} for {self.root_id}"
            )

        current.deleted_at = self.control_date
        current.deleted_by = self.actor_id
        await session.flush()
        return current
