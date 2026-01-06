"""Generic commands for branchable entities.

Moved from app.core.versioning.commands.
"""

from typing import Any, TypeVar, cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.versioning.commands import VersionedCommandABC
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
        """Get current version on specific branch."""
        stmt = (
            select(self.entity_class)
            .where(
                getattr(self.entity_class, self._root_field_name()) == self.root_id,
                cast(Any, self.entity_class).branch == branch,
                cast(Any, self.entity_class).valid_time.op("@>")(
                    func.current_timestamp()
                ),
                cast(Any, self.entity_class).deleted_at.is_(None),
            )
            .order_by(cast(Any, self.entity_class).valid_time.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


class CreateBranchCommand(BranchCommandABC[TBranchable]):
    """Create a new branch from existing branch."""

    def __init__(
        self,
        entity_class: type[TBranchable],
        root_id: UUID,
        actor_id: UUID,
        new_branch: str,
        from_branch: str = "main",
    ) -> None:
        super().__init__(entity_class, root_id, actor_id)
        self.new_branch = new_branch
        self.from_branch = from_branch

    async def execute(self, session: AsyncSession) -> TBranchable:
        """Clone current version to new branch."""
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
        await session.flush()
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
    ) -> None:
        super().__init__(entity_class, root_id, actor_id)
        self.updates = updates
        self.branch = branch

    async def execute(self, session: AsyncSession) -> TBranchable:
        """Close current on branch and create new."""
        # 1. Get current on branch
        current = await self._get_current_on_branch(session, self.branch)
        if not current:
            raise ValueError(
                f"No active version on branch {self.branch} for {self.root_id}"
            )
        # 2. Clone and apply updates (Safe Clone via Core Select)
        # Fetch raw data to avoid ORM lazy-load triggers (MissingGreenlet)
        new_version = cast(
            TBranchable, current.clone(**self.updates, parent_id=current.id)
        )

        # 3. Close current
        await self._close_version(session, current)

        session.add(new_version)
        await session.flush()
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
    ) -> None:
        super().__init__(entity_class, root_id, actor_id)
        self.source_branch = source_branch
        self.target_branch = target_branch

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

        # 4. Close Target
        await self._close_version(session, target)

        session.add(merged)
        await session.flush()
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

        # 4. Close Current
        await self._close_version(session, current)

        session.add(reverted)
        await session.flush()
        return reverted
