"""Schedule Dependency Service - predecessor/successor link management.

Plain async service (no base service inheritance) for managing
ScheduleDependency entities. Provides CRUD operations with full
validation: self-reference checks, schedule existence, duplicate
prevention, and cycle detection via DFS.
"""

from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import delete as sql_delete
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.schedule_dependency import ScheduleDependency
from app.models.domain.work_package import WorkPackage
from app.models.schemas.schedule_dependency import (
    ScheduleDependencyCreate,
    ScheduleDependencyUpdate,
)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ScheduleDependencyError(Exception):
    """Base exception for schedule dependency errors."""

    pass


class SelfReferenceError(ScheduleDependencyError):
    """Predecessor and successor are the same schedule."""

    pass


class ScheduleNotFoundError(ScheduleDependencyError):
    """Referenced schedule baseline does not exist or is deleted."""

    pass


class DuplicateDependencyError(ScheduleDependencyError):
    """A dependency of the same type already exists between the same pair."""

    pass


class CircularDependencyError(ScheduleDependencyError):
    """The proposed dependency would create a cycle in the dependency graph."""

    pass


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class ScheduleDependencyService:
    """Service for managing schedule dependencies.

    Provides CRUD operations with validation for predecessor/successor
    relationships between Schedule Baselines.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session.

        Args:
            session: Async database session.
        """
        self.session = session

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create(
        self, data: ScheduleDependencyCreate, actor_id: UUID
    ) -> ScheduleDependency:
        """Create a new schedule dependency after full validation.

        Args:
            data: Creation schema with predecessor/successor IDs and type.
            actor_id: UUID of the user performing the action.

        Returns:
            Created ScheduleDependency entity.

        Raises:
            SelfReferenceError: If predecessor and successor are the same.
            ScheduleNotFoundError: If a referenced baseline does not exist.
            DuplicateDependencyError: If an identical dependency already exists.
            CircularDependencyError: If the link would create a cycle.
        """
        await self._validate_self_reference(data.predecessor_id, data.successor_id)
        await self._validate_schedules_exist(
            data.predecessor_id, data.successor_id, data.branch
        )
        await self._validate_no_duplicate(
            data.predecessor_id,
            data.successor_id,
            data.dependency_type,
            data.branch,
        )
        await self._validate_no_cycle(
            data.predecessor_id,
            data.successor_id,
            data.project_id,
            data.branch,
        )

        dependency = ScheduleDependency(
            schedule_dependency_id=uuid4(),
            predecessor_id=data.predecessor_id,
            successor_id=data.successor_id,
            dependency_type=data.dependency_type,
            lag_days=data.lag_days,
            branch=data.branch,
            project_id=data.project_id,
        )
        self.session.add(dependency)
        await self.session.flush()
        await self.session.refresh(dependency)
        return dependency

    async def get_by_id(
        self, schedule_dependency_id: UUID
    ) -> ScheduleDependency | None:
        """Get a dependency by its root ID.

        Args:
            schedule_dependency_id: Root UUID of the dependency.

        Returns:
            ScheduleDependency if found, None otherwise.
        """
        stmt = select(ScheduleDependency).where(
            ScheduleDependency.schedule_dependency_id == schedule_dependency_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_project(
        self, project_id: UUID, branch: str = "main"
    ) -> list[ScheduleDependency]:
        """List all dependencies for a project and branch.

        Args:
            project_id: Project root UUID.
            branch: Branch name (default: "main").

        Returns:
            List of ScheduleDependency entities.
        """
        stmt = select(ScheduleDependency).where(
            ScheduleDependency.project_id == project_id,
            ScheduleDependency.branch == branch,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_for_schedule(
        self, schedule_baseline_id: UUID, branch: str = "main"
    ) -> list[ScheduleDependency]:
        """List all dependencies involving a schedule baseline.

        Returns dependencies where the baseline is either predecessor
        or successor, filtered by branch.

        Args:
            schedule_baseline_id: Schedule Baseline root UUID.
            branch: Branch name (default: "main").

        Returns:
            List of matching ScheduleDependency entities.
        """
        stmt = select(ScheduleDependency).where(
            (ScheduleDependency.predecessor_id == schedule_baseline_id)
            | (ScheduleDependency.successor_id == schedule_baseline_id),
            ScheduleDependency.branch == branch,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(
        self, schedule_dependency_id: UUID, data: ScheduleDependencyUpdate
    ) -> ScheduleDependency | None:
        """Update mutable fields of a schedule dependency.

        If dependency_type is changed, re-validates for duplicates and cycles.

        Args:
            schedule_dependency_id: Root UUID of the dependency to update.
            data: Update schema with optional new values.

        Returns:
            Updated ScheduleDependency, or None if not found.

        Raises:
            DuplicateDependencyError: If the new type duplicates an existing link.
            CircularDependencyError: If the new type would create a cycle.
        """
        dependency = await self.get_by_id(schedule_dependency_id)
        if dependency is None:
            return None

        new_type = data.dependency_type
        new_lag = data.lag_days

        if new_type is not None and new_type != dependency.dependency_type:
            await self._validate_no_duplicate(
                dependency.predecessor_id,
                dependency.successor_id,
                new_type,
                dependency.branch,
                exclude_id=schedule_dependency_id,
            )
            await self._validate_no_cycle(
                dependency.predecessor_id,
                dependency.successor_id,
                dependency.project_id,
                dependency.branch,
                exclude_id=schedule_dependency_id,
            )
            dependency.dependency_type = new_type

        if new_lag is not None:
            dependency.lag_days = new_lag

        await self.session.flush()
        await self.session.refresh(dependency)
        return dependency

    async def delete(self, schedule_dependency_id: UUID) -> bool:
        """Hard-delete a schedule dependency.

        Args:
            schedule_dependency_id: Root UUID of the dependency.

        Returns:
            True if deleted, False if not found.
        """
        stmt = sql_delete(ScheduleDependency).where(
            ScheduleDependency.schedule_dependency_id == schedule_dependency_id
        )
        result = await self.session.execute(stmt)
        deleted: int = result.rowcount  # type: ignore[attr-defined]
        return deleted > 0

    async def delete_for_schedule(
        self, schedule_baseline_id: UUID, branch: str = "main"
    ) -> int:
        """Delete all dependencies referencing a schedule baseline.

        Cascade hook called when a schedule baseline is soft-deleted.
        Removes dependencies where the baseline is predecessor or successor.

        Args:
            schedule_baseline_id: Schedule Baseline root UUID.
            branch: Branch name (default: "main").

        Returns:
            Count of deleted dependency records.
        """
        stmt = sql_delete(ScheduleDependency).where(
            (ScheduleDependency.predecessor_id == schedule_baseline_id)
            | (ScheduleDependency.successor_id == schedule_baseline_id),
            ScheduleDependency.branch == branch,
        )
        result = await self.session.execute(stmt)
        deleted: int = result.rowcount  # type: ignore[attr-defined]
        return deleted

    # ------------------------------------------------------------------
    # Validation (private)
    # ------------------------------------------------------------------

    async def _validate_self_reference(
        self, predecessor_id: str | UUID, successor_id: str | UUID
    ) -> None:
        """Raise SelfReferenceError if predecessor and successor are identical.

        Args:
            predecessor_id: Predecessor schedule baseline root ID.
            successor_id: Successor schedule baseline root ID.

        Raises:
            SelfReferenceError: If both IDs are the same.
        """
        if str(predecessor_id) == str(successor_id):
            raise SelfReferenceError(
                f"Predecessor and successor cannot be the same schedule: "
                f"{predecessor_id}"
            )

    async def _validate_schedules_exist(
        self, predecessor_id: str | UUID, successor_id: str | UUID, branch: str
    ) -> None:
        """Verify both referenced work packages exist with schedule baselines.

        The predecessor_id/successor_id are work_package root IDs.
        Each must exist on the given branch, not be soft-deleted,
        and have a schedule_baseline_id assigned.

        Args:
            predecessor_id: Predecessor work package root ID.
            successor_id: Successor work package root ID.
            branch: Branch name to match.

        Raises:
            ScheduleNotFoundError: If either work package is missing or has no schedule.
        """
        for wp_id in (predecessor_id, successor_id):
            stmt = select(func.count()).select_from(
                select(WorkPackage)
                .where(
                    WorkPackage.work_package_id == wp_id,
                    WorkPackage.branch == branch,
                    cast(Any, WorkPackage).deleted_at.is_(None),
                    func.upper(cast(Any, WorkPackage).valid_time).is_(None),
                    WorkPackage.schedule_baseline_id.isnot(None),
                )
                .subquery()
            )
            result = await self.session.execute(stmt)
            count = result.scalar_one()
            if count == 0:
                raise ScheduleNotFoundError(
                    f"Work package {wp_id} has no schedule baseline on branch '{branch}'"
                )

    async def _validate_no_duplicate(
        self,
        predecessor_id: str | UUID,
        successor_id: str | UUID,
        dependency_type: str,
        branch: str,
        exclude_id: str | UUID | None = None,
    ) -> None:
        """Check that an identical dependency does not already exist.

        Args:
            predecessor_id: Predecessor schedule baseline root ID.
            successor_id: Successor schedule baseline root ID.
            dependency_type: Dependency type string (FS, SS, FF, SF).
            branch: Branch name.
            exclude_id: Optional dependency root ID to exclude (for updates).

        Raises:
            DuplicateDependencyError: If a matching dependency exists.
        """
        stmt = select(func.count()).select_from(
            select(ScheduleDependency)
            .where(
                ScheduleDependency.predecessor_id == predecessor_id,
                ScheduleDependency.successor_id == successor_id,
                ScheduleDependency.dependency_type == dependency_type,
                ScheduleDependency.branch == branch,
            )
            .subquery()
        )
        if exclude_id is not None:
            sub = (
                select(ScheduleDependency)
                .where(
                    ScheduleDependency.predecessor_id == predecessor_id,
                    ScheduleDependency.successor_id == successor_id,
                    ScheduleDependency.dependency_type == dependency_type,
                    ScheduleDependency.branch == branch,
                    ScheduleDependency.schedule_dependency_id != exclude_id,
                )
                .subquery()
            )
            stmt = select(func.count()).select_from(sub)

        result = await self.session.execute(stmt)
        count = result.scalar_one()
        if count > 0:
            raise DuplicateDependencyError(
                f"Dependency of type {dependency_type} already exists between "
                f"{predecessor_id} and {successor_id} on branch '{branch}'"
            )

    async def _validate_no_cycle(
        self,
        predecessor_id: str | UUID,
        successor_id: str | UUID,
        project_id: str | UUID,
        branch: str,
        exclude_id: str | UUID | None = None,
    ) -> None:
        """Detect whether a proposed dependency would create a cycle.

        Uses DFS on the dependency graph built from all existing
        dependencies in the project/branch (optionally excluding one).

        The adjacency list maps successor -> predecessor (reverse edges)
        so that walking from successor_id can reach predecessor_id if
        adding the proposed link would close a cycle.

        Args:
            predecessor_id: Proposed predecessor.
            successor_id: Proposed successor.
            project_id: Project root ID for scoping the graph.
            branch: Branch name.
            exclude_id: Optional dependency root ID to exclude (for updates).

        Raises:
            CircularDependencyError: If a cycle would be created.
        """
        deps = await self._get_project_dependencies(project_id, branch, exclude_id)

        pred_key = str(predecessor_id)
        succ_key = str(successor_id)

        # Build adjacency: successor -> list of predecessors (str keys)
        adj: dict[str, list[str]] = {}
        for dep in deps:
            adj.setdefault(str(dep.successor_id), []).append(str(dep.predecessor_id))

        # Add the proposed edge before DFS
        adj.setdefault(succ_key, []).append(pred_key)

        visited: set[str] = set()

        def _has_path(node: str, target: str) -> bool:
            """Return True if node can reach target via adjacency edges."""
            if node == target:
                return True
            if node in visited:
                return False
            visited.add(node)
            for neighbor in adj.get(node, []):
                if _has_path(neighbor, target):
                    return True
            return False

        # Walk from predecessor following edges. If we can reach
        # successor, the proposed edge (successor->predecessor)
        # creates a cycle: successor->predecessor->...->successor.
        if _has_path(pred_key, succ_key):
            raise CircularDependencyError(
                f"Adding dependency {predecessor_id} -> {successor_id} "
                f"would create a circular dependency"
            )

    async def _get_project_dependencies(
        self,
        project_id: str | UUID,
        branch: str,
        exclude_id: str | UUID | None = None,
    ) -> list[ScheduleDependency]:
        """Fetch all dependencies for a project/branch.

        Args:
            project_id: Project root ID.
            branch: Branch name.
            exclude_id: Optional dependency root ID to exclude.

        Returns:
            List of ScheduleDependency entities.
        """
        stmt = select(ScheduleDependency).where(
            ScheduleDependency.project_id == project_id,
            ScheduleDependency.branch == branch,
        )
        if exclude_id is not None:
            stmt = stmt.where(ScheduleDependency.schedule_dependency_id != exclude_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
