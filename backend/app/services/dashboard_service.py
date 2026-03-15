"""DashboardService for aggregating activity across all entities.

Provides dashboard data including recent activity and last edited project
with metrics. Caches results for performance.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.change_order import ChangeOrder
from app.models.domain.cost_element import CostElement
from app.models.domain.project import Project
from app.models.domain.user import User
from app.models.domain.wbe import WBE
from app.models.schemas.dashboard import (
    DashboardActivity,
    DashboardData,
    ProjectMetrics,
    ProjectSpotlight,
)
from app.services.change_order_service import ChangeOrderService
from app.services.cost_element_service import CostElementService
from app.services.project import ProjectService
from app.services.wbe import WBEService

logger = logging.getLogger(__name__)


class DashboardService:
    """Service for dashboard data aggregation.

    Provides methods for retrieving recent activity across all entities
    and calculating project metrics for the spotlight feature.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize dashboard service.

        Args:
            session: Async database session
        """
        self.session = session
        self.project_service = ProjectService(session)
        self.wbe_service = WBEService(session)
        self.cost_element_service = CostElementService(session)
        self.change_order_service = ChangeOrderService(session)

    async def get_dashboard_data(
        self,
        user_id: UUID,
        activity_limit: int = 10,
    ) -> DashboardData:
        """Get complete dashboard data for a user.

        Args:
            user_id: User ID to get data for (not currently used, for future filtering)
            activity_limit: Maximum number of activities per entity type

        Returns:
            DashboardData with last edited project and recent activity
        """
        # Note: user_id validation skipped for now since auth is handled at API layer
        # In the future, this could be used to filter dashboard data by user permissions

        # Get recent activity for all entities with eager loading to avoid N+1 queries
        recent_projects: list[Project] = await self.project_service.get_recently_updated(
            user_id=None,  # Get all projects, not just user's
            limit=activity_limit,
            branch="main",
        )

        recent_wbes: list[WBE] = await self.wbe_service.get_recently_updated(
            user_id=None,
            limit=activity_limit,
            branch="main",
            eager_load_project=True,  # Eager load project to avoid N+1 queries
        )

        recent_cost_elements: list[CostElement] = (
            await self.cost_element_service.get_recently_updated(
                user_id=None,
                limit=activity_limit,
                branch="main",
                eager_load_wbe_and_project=True,  # Eager load WBE and project to avoid N+1 queries
            )
        )

        recent_change_orders: list[ChangeOrder] = (
            await self.change_order_service.get_recently_updated(
                user_id=None,
                limit=activity_limit,
                branch="main",
                eager_load_project=True,  # Eager load project to avoid N+1 queries
            )
        )

        # Convert to dashboard activities
        project_activities = [
            self._project_to_activity(p) for p in recent_projects
        ]
        wbe_activities = [
            await self._wbe_to_activity(w) for w in recent_wbes
        ]
        cost_element_activities = [
            await self._cost_element_to_activity(ce)
            for ce in recent_cost_elements or []
        ]
        change_order_activities = [
            await self._change_order_to_activity(co)
            for co in recent_change_orders or []
        ]

        # Get last edited project with metrics
        last_edited_project = None
        if recent_projects:
            last_edited_project = await self._get_project_spotlight(
                recent_projects[0].project_id
            )

        return DashboardData(
            last_edited_project=last_edited_project,
            recent_activity={
                "projects": project_activities,
                "wbes": wbe_activities,
                "cost_elements": cost_element_activities,
                "change_orders": change_order_activities,
            },
        )

    def _project_to_activity(self, project: Project) -> DashboardActivity:
        """Convert a Project to DashboardActivity.

        Args:
            project: Project domain model

        Returns:
            DashboardActivity for the project
        """
        # Determine action based on transaction_time
        # Use "updated" for all activity since we can't distinguish create vs update
        # without tracking initial creation separately
        action = "updated"

        return DashboardActivity(
            entity_id=project.project_id,
            entity_name=project.name,
            entity_type="project",
            action=action,
            timestamp=project.transaction_time.lower
            if project.transaction_time
            else datetime.utcnow(),
            actor_id=project.created_by,
            actor_name=getattr(project, "created_by_name", None),
            project_id=None,  # Projects don't have a parent project
            project_name=None,
            branch=project.branch,
        )

    async def _wbe_to_activity(self, wbe: WBE) -> DashboardActivity:
        """Convert a WBE to DashboardActivity.

        Args:
            wbe: WBE domain model (with project eagerly loaded if called from get_dashboard_data)

        Returns:
            DashboardActivity for the WBE
        """
        # Use preloaded project relationship if available (from eager loading)
        # Otherwise fall back to querying (for backward compatibility)
        project_name = None
        if wbe.project_id:
            if hasattr(wbe, "project") and wbe.project:
                # Use eagerly loaded project (avoiding N+1 query)
                project_name = wbe.project.name
            else:
                # Fall back to querying if not eagerly loaded (backward compatibility)
                project = await self.project_service.get_as_of(
                    wbe.project_id, branch="main"
                )
                if project:
                    project_name = project.name

        # Determine action
        action = "updated"

        return DashboardActivity(
            entity_id=wbe.wbe_id,
            entity_name=wbe.name,
            entity_type="wbe",
            action=action,
            timestamp=wbe.transaction_time.lower
            if wbe.transaction_time
            else datetime.utcnow(),
            actor_id=wbe.created_by,
            actor_name=getattr(wbe, "created_by_name", None),
            project_id=wbe.project_id,
            project_name=project_name,
            branch=wbe.branch,
        )

    async def _cost_element_to_activity(
        self, cost_element: CostElement
    ) -> DashboardActivity:
        """Convert a CostElement to DashboardActivity.

        Args:
            cost_element: CostElement domain model (with WBE and project eagerly loaded if called from get_dashboard_data)

        Returns:
            DashboardActivity for the cost element
        """
        # Use preloaded WBE and project relationships if available (from eager loading)
        # Otherwise fall back to querying (for backward compatibility)
        project_name = None
        project_id = None

        if cost_element.wbe_id:
            if hasattr(cost_element, "wbe") and cost_element.wbe:
                # Use eagerly loaded WBE (avoiding N+1 query)
                wbe = cost_element.wbe
                project_id = wbe.project_id
                if hasattr(wbe, "project") and wbe.project:
                    # Use eagerly loaded project (avoiding another N+1 query)
                    project_name = wbe.project.name
            else:
                # Fall back to querying if not eagerly loaded (backward compatibility)
                queried_wbe = await self.wbe_service.get_as_of(
                    cost_element.wbe_id, branch="main"
                )
                if queried_wbe:
                    project_id = queried_wbe.project_id
                    project = await self.project_service.get_as_of(
                        project_id, branch="main"
                    )
                    if project:
                        project_name = project.name

        # Determine action
        action = "updated"

        return DashboardActivity(
            entity_id=cost_element.cost_element_id,
            entity_name=cost_element.name,
            entity_type="cost_element",
            action=action,
            timestamp=cost_element.transaction_time.lower
            if cost_element.transaction_time
            else datetime.utcnow(),
            actor_id=cost_element.created_by,
            actor_name=getattr(cost_element, "created_by_name", None),
            project_id=project_id,
            project_name=project_name,
            branch=cost_element.branch,
        )

    async def _change_order_to_activity(
        self, change_order: ChangeOrder
    ) -> DashboardActivity:
        """Convert a ChangeOrder to DashboardActivity.

        Args:
            change_order: ChangeOrder domain model (with project eagerly loaded if called from get_dashboard_data)

        Returns:
            DashboardActivity for the change order
        """
        # Use preloaded project relationship if available (from eager loading)
        # Otherwise fall back to querying (for backward compatibility)
        project_name = None
        if change_order.project_id:
            if hasattr(change_order, "project") and change_order.project:
                # Use eagerly loaded project (avoiding N+1 query)
                project_name = change_order.project.name
            else:
                # Fall back to querying if not eagerly loaded (backward compatibility)
                project = await self.project_service.get_as_of(
                    change_order.project_id, branch="main"
                )
                if project:
                    project_name = project.name

        # Determine action based on status
        action = "updated"
        if change_order.status == "Draft":
            action = "created"
        elif change_order.status in ("Approved", "Rejected", "Merged"):
            action = change_order.status.lower()

        return DashboardActivity(
            entity_id=change_order.change_order_id,
            entity_name=change_order.title or change_order.code,
            entity_type="change_order",
            action=action,
            timestamp=change_order.transaction_time.lower
            if change_order.transaction_time
            else datetime.utcnow(),
            actor_id=change_order.created_by,
            actor_name=getattr(change_order, "created_by_name", None),
            project_id=change_order.project_id,
            project_name=project_name,
            branch=change_order.branch,
        )

    async def _get_project_spotlight(
        self, project_id: UUID
    ) -> ProjectSpotlight | None:
        """Get project spotlight with metrics.

        Args:
            project_id: Project ID to get spotlight for

        Returns:
            ProjectSpotlight with metrics, or None if project not found
        """

        # Get project
        project = await self.project_service.get_as_of(project_id, branch="main")
        if not project:
            return None

        # Calculate metrics
        metrics = await self._calculate_project_metrics(project_id)

        # Get last activity timestamp
        last_activity = project.transaction_time.lower
        if project.transaction_time:
            last_activity = project.transaction_time.lower

        return ProjectSpotlight(
            project_id=project.project_id,
            project_name=project.name,
            project_code=project.code,
            last_activity=last_activity or datetime.utcnow(),
            metrics=metrics,
            branch=project.branch,
        )

    async def _calculate_project_metrics(self, project_id: UUID) -> ProjectMetrics:
        """Calculate metrics for a project.

        Args:
            project_id: Project ID to calculate metrics for

        Returns:
            ProjectMetrics with calculated values
        """
        from typing import Any, cast

        # Get project
        project = await self.project_service.get_as_of(project_id, branch="main")
        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Count WBEs
        wbe_stmt = select(func.count()).select_from(WBE).where(
            WBE.project_id == project_id,
            WBE.branch == "main",
            func.upper(cast(Any, WBE).valid_time).is_(None),
            cast(Any, WBE).deleted_at.is_(None),
        )
        wbe_result = await self.session.execute(wbe_stmt)
        total_wbes = wbe_result.scalar() or 0

        # Count Cost Elements
        ce_stmt = select(func.count()).select_from(CostElement).where(
            CostElement.wbe_id.in_(
                select(WBE.wbe_id).where(
                    WBE.project_id == project_id,
                    WBE.branch == "main",
                    func.upper(cast(Any, WBE).valid_time).is_(None),
                    cast(Any, WBE).deleted_at.is_(None),
                )
            ),
            CostElement.branch == "main",
            func.upper(cast(Any, CostElement).valid_time).is_(None),
            cast(Any, CostElement).deleted_at.is_(None),
        )
        ce_result = await self.session.execute(ce_stmt)
        total_cost_elements = ce_result.scalar() or 0

        # Count active change orders
        co_stmt = select(func.count()).select_from(ChangeOrder).where(
            ChangeOrder.project_id == project_id,
            ChangeOrder.branch == "main",
            ChangeOrder.status.in_(["Draft", "Submitted for Approval", "Under Review"]),
            func.upper(cast(Any, ChangeOrder).valid_time).is_(None),
            cast(Any, ChangeOrder).deleted_at.is_(None),
        )
        co_result = await self.session.execute(co_stmt)
        active_change_orders = co_result.scalar() or 0

        # Get EVM status (simplified - could be enhanced with actual EVM calculations)
        ev_status = None
        # TODO: Implement actual EVM status calculation
        # For now, set to "on_track" if there are cost elements with budgets
        if total_cost_elements > 0:
            ev_status = "on_track"

        return ProjectMetrics(
            total_budget=project.budget or Decimal("0"),
            total_wbes=total_wbes,
            total_cost_elements=total_cost_elements,
            active_change_orders=active_change_orders,
            ev_status=ev_status,
        )

    async def _get_user(self, user_id: UUID) -> User | None:
        """Get user by ID.

        Args:
            user_id: User ID to look up

        Returns:
            User if found, None otherwise
        """
        stmt = select(User).where(
            User.user_id == user_id,
            func.upper(cast(Any, User).transaction_time).is_(None),
            cast(Any, User).deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
