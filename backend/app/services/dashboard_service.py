"""DashboardService for aggregating activity across all entities.

Provides dashboard data including recent activity and last edited project
with metrics. Caches results for performance.
"""

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db_utils import safe_db_execute
from app.core.temporal_queries import is_current_version, is_current_version_on_branch

# Defer imports to avoid circular import issues
from app.models.domain.change_order import ChangeOrder
from app.models.domain.cost_element import CostElement
from app.models.domain.project import Project
from app.models.domain.user import User
from app.models.domain.wbs_element import WBSElement
from app.models.schemas.dashboard import (
    DashboardActivity,
    DashboardData,
    ProjectMetrics,
    ProjectSpotlight,
)

# from app.services.change_order_service import ChangeOrderService
# from app.services.cost_element_service import CostElementService
# from app.services.project import ProjectService
# from app.services.wbs_element_service import WBSElementService

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
        # Defer imports to avoid circular import issues
        from app.services.change_order_service import ChangeOrderService
        from app.services.cost_element_service import CostElementService
        from app.services.project import ProjectService
        from app.services.wbs_element_service import WBSElementService

        self.session = session
        self.project_service = ProjectService(session)
        self.wbs_element_service = WBSElementService(session)
        self.cost_element_service = CostElementService(session)
        self.change_order_service = ChangeOrderService(session)

    async def _get_accessible_project_ids(self, user_id: UUID) -> set[UUID]:
        """Get the set of project IDs the user has RBAC access to.

        Args:
            user_id: User ID to check access for

        Returns:
            Set of accessible project IDs (all project IDs for global roles)
        """
        from app.core.rbac_unified import get_unified_rbac_service

        unified_service = get_unified_rbac_service()
        accessible = await unified_service.get_accessible_projects(user_id)
        return set(accessible)

    async def get_dashboard_data(
        self,
        user_id: UUID,
        activity_limit: int = 10,
        as_of: datetime | None = None,
        branch: str = "main",
    ) -> DashboardData:
        """Get complete dashboard data for a user.

        Args:
            user_id: User ID to get data for, used for RBAC filtering
            activity_limit: Maximum number of activities per entity type
            as_of: Optional timestamp for time-travel queries (not yet used
                in sub-queries; reserved for future implementation)
            branch: Branch name to query (default: "main")

        Returns:
            DashboardData with last edited project and recent activity,
            filtered by the user's RBAC-accessible projects
        """
        try:
            # Resolve RBAC-accessible project IDs once, then filter all entities
            accessible_ids = await self._get_accessible_project_ids(user_id)

            # Get recent activity for all entities with eager loading to avoid N+1 queries
            recent_projects: list[
                Project
            ] = await self.project_service.get_recently_updated(
                user_id=None,
                limit=activity_limit,
                branch=branch,
            )

            # Filter projects by user's RBAC access
            recent_projects = [
                p for p in recent_projects if p.project_id in accessible_ids
            ]

            recent_wbes: list[
                WBSElement
            ] = await self.wbs_element_service.get_recently_updated(
                user_id=None,
                limit=activity_limit,
                branch=branch,
                eager_load_project=True,  # Eager load project to avoid N+1 queries
            )

            # Filter WBEs by user's RBAC access
            recent_wbes = [w for w in recent_wbes if w.project_id in accessible_ids]

            # Cost Elements are now EOC line items without branch/name.
            # Dashboard activity for "cost elements" is no longer meaningful at this level.
            recent_cost_elements: list[CostElement] = []

            recent_change_orders: list[
                ChangeOrder
            ] = await self.change_order_service.get_recently_updated(
                user_id=None,
                limit=activity_limit,
                branch=branch,
                eager_load_project=True,  # Eager load project to avoid N+1 queries
            )

            # Filter Change Orders by user's RBAC access
            recent_change_orders = [
                co
                for co in (recent_change_orders or [])
                if co.project_id in accessible_ids
            ]

            # Convert to dashboard activities
            project_activities = [self._project_to_activity(p) for p in recent_projects]
            wbs_element_activities = [
                await self._wbs_element_to_activity(w) for w in recent_wbes
            ]
            cost_element_activities = [
                await self._cost_element_to_activity(ce) for ce in recent_cost_elements
            ]
            change_order_activities = [
                await self._change_order_to_activity(co) for co in recent_change_orders
            ]

            # Get last edited project with metrics
            last_edited_project = None
            if recent_projects:
                last_edited_project = await self._get_project_spotlight(
                    recent_projects[0].project_id,
                    branch=branch,
                )

            return DashboardData(
                last_edited_project=last_edited_project,
                recent_activity={
                    "projects": project_activities,
                    "wbes": wbs_element_activities,
                    "cost_elements": cost_element_activities,
                    "change_orders": change_order_activities,
                },
            )
        except Exception as e:
            # Rollback transaction on error to prevent InFailedSQLTransactionError
            await self.session.rollback()
            raise ValueError(f"Failed to get dashboard data: {str(e)}") from e

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
            else datetime.now(UTC),
            actor_id=project.created_by,
            actor_name=getattr(project, "created_by_name", None),
            project_id=None,  # Projects don't have a parent project
            project_name=None,
            branch=project.branch,
        )

    async def _wbs_element_to_activity(self, wbe: WBSElement) -> DashboardActivity:
        """Convert a WBSElement to DashboardActivity.

        Args:
            wbe: WBSElement domain model (with project eagerly loaded if called from get_dashboard_data)

        Returns:
            DashboardActivity for the WBSElement
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
            entity_id=wbe.wbs_element_id,
            entity_name=wbe.name,
            entity_type="wbe",
            action=action,
            timestamp=wbe.transaction_time.lower
            if wbe.transaction_time
            else datetime.now(UTC),
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
            cost_element: CostElement domain model

        Returns:
            DashboardActivity for the cost element
        """
        # Resolve project via WorkPackage -> ControlAccount -> WBSElement
        project_name = None
        project_id = None

        # Use the work_package relationship to resolve project
        if cost_element.work_package_id:
            from app.services.work_package_service import WorkPackageService

            wp_service = WorkPackageService(self.session)
            wp = await wp_service.get_as_of(cost_element.work_package_id, branch="main")
            if wp:
                project_id = await self._resolve_project_id_for_wp(wp)
                if project_id:
                    project = await self.project_service.get_as_of(
                        project_id, branch="main"
                    )
                    if project:
                        project_name = project.name

        # Determine action
        action = "updated"

        return DashboardActivity(
            entity_id=cost_element.cost_element_id,
            entity_name=f"Cost Element {str(cost_element.cost_element_id)[:8]}",
            entity_type="cost_element",
            action=action,
            timestamp=cost_element.transaction_time.lower
            if cost_element.transaction_time
            else datetime.now(UTC),
            actor_id=cost_element.created_by,
            actor_name=getattr(cost_element, "created_by_name", None),
            project_id=project_id,
            project_name=project_name,
            branch="main",
        )

    async def _resolve_project_id_for_wp(self, wp: Any) -> UUID | None:
        """Resolve project_id from a WorkPackage via ControlAccount -> WBSElement."""
        from app.models.domain.control_account import ControlAccount
        from app.models.domain.wbs_element import WBSElement

        stmt = (
            select(WBSElement.project_id)
            .join(
                ControlAccount,
                ControlAccount.wbs_element_id == WBSElement.wbs_element_id,
            )
            .where(
                ControlAccount.control_account_id == wp.control_account_id,
                func.upper(cast(Any, WBSElement).valid_time).is_(None),
                cast(Any, WBSElement).deleted_at.is_(None),
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

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
        if change_order.status == "draft":
            action = "created"
        elif change_order.status in ("approved", "rejected", "implemented"):
            action = change_order.status

        return DashboardActivity(
            entity_id=change_order.change_order_id,
            entity_name=change_order.title or change_order.code,
            entity_type="change_order",
            action=action,
            timestamp=change_order.transaction_time.lower
            if change_order.transaction_time
            else datetime.now(UTC),
            actor_id=change_order.created_by,
            actor_name=getattr(change_order, "created_by_name", None),
            project_id=change_order.project_id,
            project_name=project_name,
            branch=change_order.branch,
        )

    async def _get_project_spotlight(
        self, project_id: UUID, branch: str = "main"
    ) -> ProjectSpotlight | None:
        """Get project spotlight with metrics.

        Args:
            project_id: Project ID to get spotlight for
            branch: Branch name to query (default: "main")

        Returns:
            ProjectSpotlight with metrics, or None if project not found
        """

        # Get project
        project = await self.project_service.get_as_of(project_id, branch=branch)
        if not project:
            return None

        # Calculate metrics
        metrics = await self._calculate_project_metrics(project_id, branch=branch)

        # Get last activity timestamp
        last_activity = project.transaction_time.lower
        if project.transaction_time:
            last_activity = project.transaction_time.lower

        return ProjectSpotlight(
            project_id=project.project_id,
            project_name=project.name,
            project_code=project.code,
            last_activity=last_activity or datetime.now(UTC),
            metrics=metrics,
            branch=project.branch,
            currency=project.currency or "EUR",
        )

    async def _calculate_project_metrics(
        self, project_id: UUID, branch: str = "main"
    ) -> ProjectMetrics:
        """Calculate metrics for a project.

        Args:
            project_id: Project ID to calculate metrics for
            branch: Branch name to query (default: "main")

        Returns:
            ProjectMetrics with calculated values
        """
        from typing import Any, cast

        # Get project
        project = await self.project_service.get_as_of(project_id, branch=branch)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Count WBEs
        wbs_element_stmt = (
            select(func.count())
            .select_from(WBSElement)
            .where(
                WBSElement.project_id == project_id,
                is_current_version_on_branch(
                    cast(Any, WBSElement).valid_time,
                    WBSElement.branch,
                    branch,
                    cast(Any, WBSElement).deleted_at,
                ),
            )
        )
        wbs_element_result = await safe_db_execute(
            self.session,
            self.session.execute(wbs_element_stmt),
            "Failed to count WBEs for project metrics",
        )
        total_wbes = wbs_element_result.scalar() or 0

        # Count Cost Elements (via WorkPackage -> ControlAccount -> WBSElement)
        from app.models.domain.control_account import ControlAccount
        from app.models.domain.work_package import WorkPackage

        ce_stmt = (
            select(func.count())
            .select_from(CostElement)
            .join(
                WorkPackage, CostElement.work_package_id == WorkPackage.work_package_id
            )
            .join(
                ControlAccount,
                WorkPackage.control_account_id == ControlAccount.control_account_id,
            )
            .join(
                WBSElement, ControlAccount.wbs_element_id == WBSElement.wbs_element_id
            )
            .where(
                WBSElement.project_id == project_id,
                func.upper(cast(Any, CostElement).valid_time).is_(None),
                cast(Any, CostElement).deleted_at.is_(None),
            )
        )
        ce_result = await safe_db_execute(
            self.session,
            self.session.execute(ce_stmt),
            "Failed to count cost elements for project metrics",
        )
        total_cost_elements = ce_result.scalar() or 0

        # Count active change orders
        co_stmt = (
            select(func.count())
            .select_from(ChangeOrder)
            .where(
                ChangeOrder.project_id == project_id,
                ChangeOrder.branch == branch,
                ChangeOrder.status.in_(
                    ["draft", "submitted_for_approval", "under_review"]
                ),
                is_current_version_on_branch(
                    cast(Any, ChangeOrder).valid_time,
                    ChangeOrder.branch,
                    branch,
                    cast(Any, ChangeOrder).deleted_at,
                ),
            )
        )
        co_result = await safe_db_execute(
            self.session,
            self.session.execute(co_stmt),
            "Failed to count change orders for project metrics",
        )
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
            is_current_version(
                cast(Any, User).transaction_time,
                cast(Any, User).deleted_at,
            ),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
