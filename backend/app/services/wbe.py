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

    async def get_by_parent(
        self,
        project_id: UUID | None = None,
        parent_wbe_id: UUID | None = None,
        branch: str = "main",
    ) -> list[WBE]:
        """Get WBEs filtered by parent_wbe_id.
        
        Args:
            project_id: Optional project filter
            parent_wbe_id: Parent WBE ID. None means root WBEs (parent_wbe_id IS NULL)
            branch: Branch name
            
        Returns:
            List of WBEs matching the parent filter
        """
        from typing import Any, cast

        from sqlalchemy import func

        # Build base query
        conditions = [
            WBE.branch == branch,
            func.upper(cast(Any, WBE).valid_time).is_(None),
            cast(Any, WBE).deleted_at.is_(None),
        ]

        # Add project filter if provided
        if project_id:
            conditions.append(WBE.project_id == project_id)

        # Add parent filter
        if parent_wbe_id is None:
            # Query for root WBEs (parent_wbe_id IS NULL)
            conditions.append(cast(Any, WBE).parent_wbe_id.is_(None))
        else:
            # Query for children of specific parent
            conditions.append(WBE.parent_wbe_id == parent_wbe_id)

        stmt = select(WBE).where(*conditions).order_by(WBE.code)
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
        """Soft delete WBE with cascade to children.
        
        Deletes the WBE and all its descendants recursively.
        Returns the root WBE that was deleted.
        
        Args:
            wbe_id: Root WBE ID to delete
            actor_id: User performing the delete
            
        Returns:
            The deleted WBE (root)
            
        Raises:
            ValueError: If WBE not found
        """
        from typing import Any, cast

        from sqlalchemy import func

        # First, check if WBE exists and get current children count
        wbe = await self.get_wbe(wbe_id)
        if not wbe:
            raise ValueError(f"WBE with id {wbe_id} not found")

        # Get all descendants (direct children + nested)
        descendants = await self._get_all_descendants(wbe_id, wbe.branch)
        
        # Soft-delete all descendants first (bottom-up to avoid FK issues)
        for descendant in reversed(descendants):  # Reverse to delete deepest first
            cmd = SoftDeleteCommand(
                entity_class=WBE,  # type: ignore[type-var]
                root_id=descendant.wbe_id,
                actor_id=actor_id,
            )
            await cmd.execute(self.session)
        
        # Finally, soft-delete the root WBE itself
        cmd = SoftDeleteCommand(
            entity_class=WBE,  # type: ignore[type-var]
            root_id=wbe_id,
            actor_id=actor_id,
        )
        return await cmd.execute(self.session)

    async def _get_all_descendants(
        self, parent_wbe_id: UUID, branch: str = "main"
    ) -> list[WBE]:
        """Recursively get all descendants of a WBE using recursive CTE.
        
        Args:
            parent_wbe_id: Root WBE ID to get descendants for
            branch: Branch name
            
        Returns:
            List of all descendant WBEs (ordered depth-first)
        """
        from typing import Any, cast

        from sqlalchemy import func, literal_column, select
        from sqlalchemy.orm import aliased

        # Build recursive CTE to get all descendants
        # Base case: direct children
        wbe_cte = (
            select(
                WBE.id,
                WBE.wbe_id,
                WBE.code,
                WBE.name,
                WBE.parent_wbe_id,
                literal_column("1").label("depth"),  # Depth 1 = direct children
            )
            .where(
                WBE.parent_wbe_id == parent_wbe_id,
                WBE.branch == branch,
                func.upper(cast(Any, WBE).valid_time).is_(None),
                cast(Any, WBE).deleted_at.is_(None),
            )
            .cte(name="wbe_descendants", recursive=True)
        )

        # Recursive case: children of children
        wbe_alias = aliased(WBE, name="wbe_child")
        wbe_cte = wbe_cte.union_all(
            select(
                wbe_alias.id,
                wbe_alias.wbe_id,
                wbe_alias.code,
                wbe_alias.name,
                wbe_alias.parent_wbe_id,
                (wbe_cte.c.depth + 1).label("depth"),
            ).where(
                wbe_alias.parent_wbe_id == wbe_cte.c.wbe_id,
                wbe_alias.branch == branch,
                func.upper(cast(Any, wbe_alias).valid_time).is_(None),
                cast(Any, wbe_alias).deleted_at.is_(None),
            )
        )

        # Execute CTE query ordered by depth (parents before children)
        descendants_stmt = select(wbe_cte).order_by(wbe_cte.c.depth.asc())
        descendants_result = await self.session.execute(descendants_stmt)
        descendant_rows = descendants_result.all()

        # Fetch full WBE objects for each descendant
        descendant_list = []
        for row in descendant_rows:
            descendant = await self.get_wbe(row.wbe_id)
            if descendant:
                descendant_list.append(descendant)
                
        return descendant_list
    
    async def get_children_count(self, wbe_id: UUID, branch: str = "main") -> int:
        """Get count of direct children for a WBE.
        
        Useful for UI to show children count indicator.
        
        Args:
            wbe_id: Parent WBE ID
            branch: Branch name
            
        Returns:
            Count of direct children
        """
        from typing import Any, cast

        from sqlalchemy import func, select

        stmt = (
            select(func.count())
            .select_from(WBE)
            .where(
                WBE.parent_wbe_id == wbe_id,
                WBE.branch == branch,
                func.upper(cast(Any, WBE).valid_time).is_(None),
                cast(Any, WBE).deleted_at.is_(None),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0


    async def get_breadcrumb(self, wbe_id: UUID) -> dict:
        """Get breadcrumb trail for a WBE including project and all ancestors.
        
        Uses recursive CTE to efficiently fetch the entire ancestor chain in a single query.
        
        Args:
            wbe_id: Root WBE ID
            
        Returns:
            Dict with 'project' and 'wbe_path' keys
            
        Raises:
            ValueError: If WBE not found
        """
        from typing import Any, cast

        from sqlalchemy import func, literal_column, select, union_all
        from sqlalchemy.orm import aliased

        from app.models.domain.project import Project

        # First, get the current WBE
        current_wbe = await self.get_wbe(wbe_id)
        if not current_wbe:
            raise ValueError(f"WBE with id {wbe_id} not found")

        # Get the project
        project_stmt = (
            select(Project)
            .where(
                Project.project_id == current_wbe.project_id,
                Project.branch == current_wbe.branch,
                func.upper(cast(Any, Project).valid_time).is_(None),
                cast(Any, Project).deleted_at.is_(None),
            )
            .limit(1)
        )
        project_result = await self.session.execute(project_stmt)
        project = project_result.scalar_one_or_none()
        
        if not project:
            raise ValueError(f"Project {current_wbe.project_id} not found")

        # Build recursive CTE to get all ancestors
        # Base case: current WBE
        wbe_cte = (
            select(
                WBE.id,
                WBE.wbe_id,
                WBE.code,
                WBE.name,
                WBE.parent_wbe_id,
                literal_column("0").label("depth"),  # Depth 0 is the current WBE
            )
            .where(
                WBE.wbe_id == wbe_id,
                WBE.branch == current_wbe.branch,
                func.upper(cast(Any, WBE).valid_time).is_(None),
                cast(Any, WBE).deleted_at.is_(None),
            )
            .cte(name="wbe_ancestors", recursive=True)
        )

        # Recursive case: get parent WBEs
        wbe_alias = aliased(WBE, name="wbe_parent")
        wbe_cte = wbe_cte.union_all(
            select(
                wbe_alias.id,
                wbe_alias.wbe_id,
                wbe_alias.code,
                wbe_alias.name,
                wbe_alias.parent_wbe_id,
                (wbe_cte.c.depth + 1).label("depth"),
            ).where(
                wbe_alias.wbe_id == wbe_cte.c.parent_wbe_id,
                wbe_alias.branch == current_wbe.branch,
                func.upper(cast(Any, wbe_alias).valid_time).is_(None),
                cast(Any, wbe_alias).deleted_at.is_(None),
            )
        )

        # Execute CTE query ordered by depth (root first)
        ancestors_stmt = select(wbe_cte).order_by(wbe_cte.c.depth.desc())
        ancestors_result = await self.session.execute(ancestors_stmt)
        ancestors = ancestors_result.all()

        # Build breadcrumb response
        return {
            "project": {
                "id": project.id,
                "project_id": project.project_id,
                "code": project.code,
                "name": project.name,
            },
            "wbe_path": [
                {
                    "id": ancestor.id,
                    "wbe_id": ancestor.wbe_id,
                    "code": ancestor.code,
                    "name": ancestor.name,
                }
                for ancestor in ancestors
            ],
        }

    async def get_wbe_history(self, wbe_id: UUID) -> list[WBE]:
        """Get all versions of a WBE by root wbe_id (with creator name)."""
        return await self.get_history(wbe_id)
