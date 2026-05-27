"""Entity Discovery Service for branchable entities.

Service to discover all active (non-deleted) branchable entities
(WBSElements, CostElements, Projects) in a given branch.
"""

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.cost_element import CostElement
from app.models.domain.project import Project
from app.models.domain.wbs_element import WBSElement


class EntityDiscoveryService:
    """Service for discovering branchable entities in a specific branch.

    Provides methods to query WBSElements, CostElements, and Projects that exist
    in a given branch, filtering out soft-deleted entities.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the service with a database session.

        Args:
            session: Async SQLAlchemy session
        """
        self.session = session

    async def discover_wbes(self, branch: str) -> list[WBSElement]:
        """Discover all active WBSElements in the specified branch.

        Args:
            branch: Branch name to search (e.g., "BR-123")

        Returns:
            List of WBSElements where branch matches and deleted_at IS NULL
        """
        stmt = select(WBSElement).where(
            and_(WBSElement.branch == branch, WBSElement.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def discover_cost_elements(self, branch: str) -> list[CostElement]:
        """Discover all active CostElements (not branch-scoped).

        CostElements are versionable but NOT branchable, so branch is ignored.
        Returns all current (non-deleted) cost elements regardless of branch.

        Args:
            branch: Unused (CostElements are not branch-scoped). Kept for API compat.

        Returns:
            List of CostElements where deleted_at IS NULL
        """
        stmt = select(CostElement).where(and_(CostElement.deleted_at.is_(None)))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def discover_projects(self, branch: str) -> list[Project]:
        """Discover all active Projects in the specified branch.

        Args:
            branch: Branch name to search (e.g., "BR-123")

        Returns:
            List of Projects where branch matches and deleted_at IS NULL
        """
        stmt = select(Project).where(
            and_(Project.branch == branch, Project.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def discover_all_wbes(self, branch: str) -> list[WBSElement]:
        """Discover all current WBSElements in the specified branch, including soft-deleted.

        Returns only CURRENT versions (valid_time upper bound is NULL) to avoid
        processing historical versions during merge operations.

        Args:
            branch: Branch name to search (e.g., "BR-123")

        Returns:
            List of current WBSElement versions where branch matches (including soft-deleted)
        """
        stmt = select(WBSElement).where(
            and_(
                WBSElement.branch == branch,
                func.upper(WBSElement.valid_time).is_(None),
                func.not_(func.isempty(WBSElement.valid_time)),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def discover_all_cost_elements(self, branch: str) -> list[CostElement]:
        """Discover all current CostElements (not branch-scoped), including soft-deleted.

        CostElements are versionable but NOT branchable, so branch is ignored.
        Returns only CURRENT versions (valid_time upper bound is NULL) to avoid
        processing historical versions during merge operations.

        Args:
            branch: Unused (CostElements are not branch-scoped). Kept for API compat.

        Returns:
            List of current CostElement versions (including soft-deleted)
        """
        stmt = select(CostElement).where(
            and_(
                func.upper(CostElement.valid_time).is_(None),
                func.not_(func.isempty(CostElement.valid_time)),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
