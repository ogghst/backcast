"""WBEService extending TemporalService for branchable entities.

Provides WBE-specific operations with parent-child project relationship.
"""

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.versioning.commands import (
    CreateVersionCommand,
    SoftDeleteCommand,
    UpdateVersionCommand,
)
from app.core.versioning.service import TemporalService
from app.models.domain.wbe import WBE
from app.models.schemas.wbe import WBECreate, WBEUpdate


class WBEService(TemporalService[WBE]):  # type: ignore[type-var]
    """Service for WBE entity operations.

    Extends TemporalService with WBE-specific methods including
    project filtering and hierarchical queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(WBE, session)

    async def get_wbe(self, wbe_id: UUID) -> WBE | None:
        """Get WBE by root wbe_id (current version in main branch)."""
        return await self.get_current_version(wbe_id)

    async def get_wbes(
        self, skip: int = 0, limit: int = 100, branch: str = "main"
    ) -> list[WBE]:
        """Get all WBEs with pagination (filtered by branch)."""
        from typing import Any, cast

        from sqlalchemy import func

        stmt = (
            select(WBE)
            .where(
                WBE.branch == branch,
                func.upper(cast(Any, WBE).valid_time).is_(None),
                cast(Any, WBE).deleted_at.is_(None),
            )
            .order_by(cast(Any, WBE).valid_time.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_project(self, project_id: UUID, branch: str = "main") -> list[WBE]:
        """Get all WBEs for a specific project (current versions)."""
        from typing import Any, cast

        from sqlalchemy import func

        stmt = (
            select(WBE)
            .where(
                WBE.project_id == project_id,
                WBE.branch == branch,
                func.upper(cast(Any, WBE).valid_time).is_(None),
                cast(Any, WBE).deleted_at.is_(None),
            )
            .order_by(WBE.code)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_code(
        self, code: str, project_id: UUID, branch: str = "main"
    ) -> WBE | None:
        """Get WBE by code within a project (current version)."""
        from typing import Any, cast

        from sqlalchemy import func

        stmt = (
            select(WBE)
            .where(
                WBE.code == code,
                WBE.project_id == project_id,
                WBE.branch == branch,
                func.upper(cast(Any, WBE).valid_time).is_(None),
                cast(Any, WBE).deleted_at.is_(None),
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_wbe(self, wbe_in: WBECreate, actor_id: UUID) -> WBE:
        """Create new WBE using CreateVersionCommand."""
        wbe_data = wbe_in.model_dump()

        # Generate root wbe_id
        root_id = uuid4()
        wbe_data["wbe_id"] = root_id

        cmd = CreateVersionCommand(
            entity_class=WBE,  # type: ignore[type-var]
            root_id=root_id,
            actor_id=actor_id,
            **wbe_data,
        )
        return await cmd.execute(self.session)

    async def update_wbe(self, wbe_id: UUID, wbe_in: WBEUpdate, actor_id: UUID) -> WBE:
        """Update WBE using UpdateVersionCommand."""
        update_data = wbe_in.model_dump(exclude_unset=True)

        cmd = UpdateVersionCommand(
            entity_class=WBE,  # type: ignore[type-var]
            root_id=wbe_id,
            actor_id=actor_id,
            **update_data,
        )
        return await cmd.execute(self.session)

    async def delete_wbe(self, wbe_id: UUID, actor_id: UUID) -> WBE:
        """Soft delete WBE using SoftDeleteCommand."""
        cmd = SoftDeleteCommand(
            entity_class=WBE,  # type: ignore[type-var]
            root_id=wbe_id,
            actor_id=actor_id,
        )
        return await cmd.execute(self.session)

    async def get_wbe_history(self, wbe_id: UUID) -> list[WBE]:
        """Get all versions of a WBE by root wbe_id (with creator name)."""
        return await self.get_history(wbe_id)
