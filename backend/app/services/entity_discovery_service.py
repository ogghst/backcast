"""Entity Discovery Service for branchable entities.

Service to discover all active (non-deleted) branchable entities
(WBEs, CostElements, Projects) in a given branch.
"""

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.cost_element import CostElement
from app.models.domain.project import Project
from app.models.domain.wbe import WBE


class EntityDiscoveryService:
    """Service for discovering branchable entities in a specific branch.

    Provides methods to query WBEs, CostElements, and Projects that exist
    in a given branch, filtering out soft-deleted entities.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the service with a database session.

        Args:
            session: Async SQLAlchemy session
        """
        self.session = session

    async def discover_wbes(self, branch: str) -> list[WBE]:
        """Discover all active WBEs in the specified branch.

        Args:
            branch: Branch name to search (e.g., "BR-123")

        Returns:
            List of WBEs where branch matches and deleted_at IS NULL
        """
        stmt = select(WBE).where(
            and_(WBE.branch == branch, WBE.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def discover_cost_elements(self, branch: str) -> list[CostElement]:
        """Discover all active CostElements in the specified branch.

        Args:
            branch: Branch name to search (e.g., "BR-123")

        Returns:
            List of CostElements where branch matches and deleted_at IS NULL
        """
        stmt = select(CostElement).where(
            and_(CostElement.branch == branch, CostElement.deleted_at.is_(None))
        )
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

    async def discover_all_wbes(self, branch: str) -> list[WBE]:
        """Discover all WBEs in the specified branch, including soft-deleted.

        Args:
            branch: Branch name to search (e.g., "BR-123")

        Returns:
            List of all WBEs where branch matches (including deleted)
        """
        stmt = select(WBE).where(WBE.branch == branch)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def discover_all_cost_elements(self, branch: str) -> list[CostElement]:
        """Discover all CostElements in the specified branch, including soft-deleted.

        Args:
            branch: Branch name to search (e.g., "BR-123")

        Returns:
            List of all CostElements where branch matches (including deleted)
        """
        stmt = select(CostElement).where(CostElement.branch == branch)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
