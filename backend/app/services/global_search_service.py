"""Global cross-entity search service.

Searches across all 12 searchable entity types in parallel via asyncio.gather,
applies tier-appropriate temporal/branch/permission filters, scores by relevance,
and returns a flat ranked list.
"""

import asyncio
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import case, func, or_, select
from sqlalchemy import cast as sql_cast
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.versioning.enums import BranchMode
from app.models.domain.change_order import ChangeOrder
from app.models.domain.cost_element import CostElement
from app.models.domain.cost_element_type import CostElementType
from app.models.domain.cost_registration import CostRegistration
from app.models.domain.department import Department
from app.models.domain.forecast import Forecast
from app.models.domain.progress_entry import ProgressEntry
from app.models.domain.project import Project
from app.models.domain.quality_event import QualityEvent
from app.models.domain.schedule_baseline import ScheduleBaseline
from app.models.domain.user import User
from app.models.domain.wbe import WBE
from app.models.schemas.search import GlobalSearchResponse, SearchResultItem


def _score(
    value: str | None,
    query_lower: str,
) -> float | None:
    """Score a field value against the query string.

    Returns the highest applicable score, or None if no match:
    - Exact match: 1.0
    - Prefix match: 0.9
    - ILIKE (substring) match: 0.7
    """
    if value is None:
        return None
    val_lower = value.lower()
    q = query_lower
    if val_lower == q:
        return 1.0
    if val_lower.startswith(q):
        return 0.9
    if q in val_lower:
        return 0.7
    return None


def _best_score(
    row: Any,
    query_lower: str,
    primary_fields: list[str],
    description_fields: list[str],
    secondary_fields: list[str],
) -> float:
    """Compute the best relevance score for a result row.

    Scoring tiers:
    - Primary fields (code, name): exact 1.0 / prefix 0.9 / ilike 0.7
    - Description fields: ilike 0.5
    - Secondary fields: ilike 0.3

    Returns 0.0 if nothing matched (should not happen since rows are ILIKE-filtered).
    """
    best = 0.0

    # Primary: exact / prefix / substring
    for field in primary_fields:
        val = getattr(row, field, None)
        s = _score(val, query_lower)
        if s is not None and s > best:
            best = s

    # Description: substring only
    for field in description_fields:
        val = getattr(row, field, None)
        if val is not None and query_lower in val.lower():
            if 0.5 > best:
                best = 0.5

    # Secondary: substring only
    for field in secondary_fields:
        val = getattr(row, field, None)
        if val is not None and query_lower in val.lower():
            if 0.3 > best:
                best = 0.3

    return best


# ---------------------------------------------------------------------------
# Temporal filter helpers (inline SQL, no service dependency)
# ---------------------------------------------------------------------------


def _apply_current_filter(
    stmt: Any,
    entity_class: type[Any],
) -> Any:
    """Filter to current (open valid_time, not deleted) versions."""
    return stmt.where(
        func.upper(cast(Any, entity_class).valid_time).is_(None),
        cast(Any, entity_class).deleted_at.is_(None),
    )


def _apply_bitemporal_filter(
    stmt: Any,
    entity_class: type[Any],
    as_of: datetime,
) -> Any:
    """Apply bitemporal WHERE clauses for time-travel queries."""
    as_of_tstz = sql_cast(as_of, TIMESTAMP(timezone=True))
    return stmt.where(
        cast(Any, entity_class).valid_time.op("@>")(as_of_tstz),
        func.lower(cast(Any, entity_class).valid_time) <= as_of_tstz,
        or_(
            cast(Any, entity_class).deleted_at.is_(None),
            cast(Any, entity_class).deleted_at > as_of_tstz,
        ),
    )


def _apply_branch_mode_filter(
    stmt: Any,
    entity_class: type[Any],
    root_field: str,
    branch: str,
    branch_mode: BranchMode,
) -> Any:
    """Apply branch mode filtering for branchable entities.

    STRICT: only the specified branch.
    MERGE: DISTINCT ON with branch precedence (current branch over main).
    """
    if branch_mode == BranchMode.MERGE and branch != "main":
        stmt = stmt.where(
            cast(Any, entity_class).branch.in_([branch, "main"]),
        )

        deleted_root_ids_subq = (
            select(getattr(entity_class, root_field))
            .where(
                cast(Any, entity_class).branch == branch,
                cast(Any, entity_class).deleted_at.is_not(None),
            )
            .distinct()
        )

        stmt = stmt.where(
            or_(
                cast(Any, entity_class).branch == branch,
                ~getattr(entity_class, root_field).in_(
                    deleted_root_ids_subq.scalar_subquery()
                ),
            ),
        )

        stmt = stmt.order_by(
            getattr(entity_class, root_field),
            case(
                (cast(Any, entity_class).branch == branch, 0),
                else_=1,
            ),
            cast(Any, entity_class).valid_time.desc(),
        )

        stmt = stmt.distinct(getattr(entity_class, root_field))
    else:
        stmt = stmt.where(cast(Any, entity_class).branch == branch)

    return stmt


# ---------------------------------------------------------------------------
# Entity search configuration
# ---------------------------------------------------------------------------

# Each entry: (entity_type_label, model_class, root_field, primary_fields,
#              description_fields, secondary_fields, is_branchable, is_global)
_ENTITY_CONFIG: list[tuple[str, type[Any], str, list[str], list[str], list[str], bool, bool]] = [
    # Branchable entities
    ("project", Project, "project_id", ["code", "name"], ["description"], ["status"], True, False),
    ("wbe", WBE, "wbe_id", ["code", "name"], ["description"], [], True, False),
    ("cost_element", CostElement, "cost_element_id", ["code", "name"], ["description"], [], True, False),
    ("schedule_baseline", ScheduleBaseline, "schedule_baseline_id", ["name"], ["description"], [], True, False),
    ("change_order", ChangeOrder, "change_order_id", ["code", "title"], ["description", "justification"], ["status"], True, False),
    ("forecast", Forecast, "forecast_id", [], ["basis_of_estimate"], [], True, False),
    # Versionable entities
    ("cost_registration", CostRegistration, "cost_registration_id", [], ["description"], ["invoice_number", "vendor_reference"], False, False),
    ("quality_event", QualityEvent, "quality_event_id", [], ["description"], ["event_type", "root_cause", "resolution_notes"], False, False),
    ("progress_entry", ProgressEntry, "progress_entry_id", [], ["notes"], [], False, False),
    # Global entities (no project scoping)
    ("user", User, "user_id", ["email", "full_name"], [], [], False, True),
    ("department", Department, "department_id", ["code", "name"], ["description"], [], False, True),
    ("cost_element_type", CostElementType, "cost_element_type_id", ["code", "name"], ["description"], [], False, True),
]


class GlobalSearchService:
    """Standalone service for cross-entity search.

    Does NOT extend BranchableService or TemporalService. Builds SQL queries
    directly using the domain models and inlines temporal/branch filter logic.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def search(
        self,
        query: str,
        *,
        user_id: UUID,
        user_role: str,
        project_id: UUID | None = None,
        wbe_id: UUID | None = None,
        branch: str = "main",
        branch_mode: BranchMode = BranchMode.MERGE,
        as_of: datetime | None = None,
        limit: int = 50,
    ) -> GlobalSearchResponse:
        """Search across all entity types and return ranked results.

        Args:
            query: Search string (at least 1 character).
            user_id: Authenticated user ID for RBAC scoping.
            user_role: User role for RBAC scoping.
            project_id: Optional project root ID to scope results.
            wbe_id: Optional WBE root ID to scope results (includes descendants).
            branch: Branch name (default "main").
            branch_mode: STRICT or MERGE for branchable entities.
            as_of: Optional timestamp for time-travel queries.
            limit: Maximum results to return.

        Returns:
            GlobalSearchResponse with ranked results.
        """
        # 1. Resolve accessible project IDs via RBAC
        accessible_project_ids = await self._get_accessible_projects(
            user_id, user_role
        )

        # 2. If wbe_id provided, resolve descendant WBE IDs
        wbe_ids: list[UUID] | None = None
        if wbe_id is not None:
            wbe_ids = await self._resolve_wbe_descendants(wbe_id, branch, branch_mode, as_of)
            wbe_ids.append(wbe_id)

        # 3. Run all entity searches in parallel
        search_term = f"%{query}%"
        query_lower = query.lower()

        coroutines = []
        for config in _ENTITY_CONFIG:
            coroutines.append(
                self._search_entity(
                    config=config,
                    search_term=search_term,
                    query_lower=query_lower,
                    accessible_project_ids=accessible_project_ids,
                    project_id=project_id,
                    wbe_ids=wbe_ids,
                    branch=branch,
                    branch_mode=branch_mode,
                    as_of=as_of,
                    limit=limit,
                )
            )

        all_results_lists = await asyncio.gather(*coroutines)

        # 4. Merge, sort by score, take top limit
        all_results: list[SearchResultItem] = []
        for results in all_results_lists:
            all_results.extend(results)

        all_results.sort(key=lambda r: r.relevance_score, reverse=True)
        top_results = all_results[:limit]

        return GlobalSearchResponse(
            results=top_results,
            total=len(top_results),
            query=query,
        )

    async def _get_accessible_projects(
        self,
        user_id: UUID,
        user_role: str,
    ) -> list[UUID]:
        """Get project IDs accessible to the user via RBAC.

        Admin users see all projects. Others are filtered by membership.
        """
        from app.core.rbac import get_rbac_service, inject_rbac_session

        rbac_service = get_rbac_service()
        inject_rbac_session(rbac_service, self.session)
        return await rbac_service.get_user_projects(user_id, user_role)

    async def _resolve_wbe_descendants(
        self,
        root_wbe_id: UUID,
        branch: str,
        branch_mode: BranchMode,
        as_of: datetime | None,
    ) -> list[UUID]:
        """Resolve all descendant WBE IDs for a given root WBE.

        Uses iterative BFS via parent_wbe_id hierarchy.
        Returns a list of descendant root IDs (not including root_wbe_id itself).
        """
        descendants: list[UUID] = []
        queue: list[UUID] = [root_wbe_id]

        while queue:
            parent_ids = queue
            queue = []

            stmt = select(WBE.wbe_id).where(
                WBE.parent_wbe_id.in_(parent_ids),
            )
            stmt = self._apply_temporal_filter(stmt, WBE, as_of)
            stmt = _apply_branch_mode_filter(stmt, WBE, "wbe_id", branch, branch_mode)
            stmt = stmt.limit(500)

            result = await self.session.execute(stmt)
            child_ids = [row[0] for row in result.all()]

            descendants.extend(child_ids)
            if child_ids:
                queue = child_ids

        return descendants

    async def _search_entity(
        self,
        config: tuple[str, type[Any], str, list[str], list[str], list[str], bool, bool],
        search_term: str,
        query_lower: str,
        accessible_project_ids: list[UUID],
        project_id: UUID | None,
        wbe_ids: list[UUID] | None,
        branch: str,
        branch_mode: BranchMode,
        as_of: datetime | None,
        limit: int,
    ) -> list[SearchResultItem]:
        """Search a single entity type and return scored results."""
        (
            entity_type,
            entity_class,
            root_field,
            primary_fields,
            description_fields,
            secondary_fields,
            is_branchable,
            is_global,
        ) = config

        # Build base statement selecting the entity
        stmt = select(entity_class)

        # Build ILIKE WHERE on all searchable fields
        ilike_fields = primary_fields + description_fields + secondary_fields
        ilike_clauses = []
        for field_name in ilike_fields:
            col = getattr(entity_class, field_name, None)
            if col is not None:
                ilike_clauses.append(col.ilike(search_term))

        if not ilike_clauses:
            return []

        stmt = stmt.where(or_(*ilike_clauses))

        # Apply temporal filters
        stmt = self._apply_temporal_filter(stmt, entity_class, as_of)

        # Apply branch mode filter for branchable entities
        if is_branchable:
            stmt = _apply_branch_mode_filter(
                stmt, entity_class, root_field, branch, branch_mode
            )

        # Apply project scoping (skip for global entities)
        if not is_global:
            stmt = self._apply_project_scope(
                stmt,
                entity_class,
                root_field,
                accessible_project_ids,
                project_id,
                wbe_ids,
            )

        # Limit rows fetched per entity type
        stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        rows = result.scalars().all()

        # Score and convert to SearchResultItem
        items: list[SearchResultItem] = []
        for row in rows:
            score = _best_score(
                row, query_lower, primary_fields, description_fields, secondary_fields
            )
            if score <= 0.0:
                continue

            item = SearchResultItem(
                entity_type=entity_type,
                id=row.id,
                root_id=getattr(row, root_field),
                code=getattr(row, "code", None),
                name=self._get_display_name(row, entity_type),
                description=self._get_description(row, entity_type),
                status=getattr(row, "status", None),
                relevance_score=score,
                project_id=getattr(row, "project_id", None),
                wbe_id=getattr(row, "wbe_id", None),
            )
            items.append(item)

        return items

    def _apply_temporal_filter(
        self,
        stmt: Any,
        entity_class: type[Any],
        as_of: datetime | None,
    ) -> Any:
        """Apply temporal filter based on whether as_of is provided."""
        if as_of is not None:
            return _apply_bitemporal_filter(stmt, entity_class, as_of)
        return _apply_current_filter(stmt, entity_class)

    def _apply_project_scope(
        self,
        stmt: Any,
        entity_class: type[Any],
        root_field: str,
        accessible_project_ids: list[UUID],
        project_id: UUID | None,
        wbe_ids: list[UUID] | None,
    ) -> Any:
        """Apply RBAC project scoping to the query.

        Strategy varies by how the entity links to a project:
        - Direct project_id column: filter directly.
        - wbe_id column: join to WBE, filter WBE.project_id.
        - cost_element_id column: join chain CE -> WBE -> project.
        """
        # If accessible_project_ids is empty, user has no access
        if not accessible_project_ids:
            return stmt.where(cast(Any, entity_class).id.is_(None))

        target_project_ids = accessible_project_ids
        if project_id is not None:
            if project_id not in accessible_project_ids:
                return stmt.where(cast(Any, entity_class).id.is_(None))
            target_project_ids = [project_id]

        # Entity has direct project_id
        if hasattr(entity_class, "project_id"):
            stmt = stmt.where(entity_class.project_id.in_(target_project_ids))
            return stmt

        # Entity has wbe_id -> join to WBE for project_id
        if hasattr(entity_class, "wbe_id") and not hasattr(entity_class, "cost_element_id"):
            # WBE itself
            if wbe_ids is not None:
                stmt = stmt.where(entity_class.wbe_id.in_(wbe_ids))
            else:
                wbe_subq = (
                    select(WBE.wbe_id)
                    .where(WBE.project_id.in_(target_project_ids))
                    .correlate(entity_class)
                )
                stmt = stmt.where(entity_class.wbe_id.in_(wbe_subq))
            return stmt

        # Entity has cost_element_id -> join chain CE -> WBE -> project
        if hasattr(entity_class, "cost_element_id"):
            if wbe_ids is not None:
                # If WBE-scoped, resolve CE IDs under those WBEs
                ce_subq = (
                    select(CostElement.cost_element_id)
                    .where(CostElement.wbe_id.in_(wbe_ids))
                )
                stmt = stmt.where(entity_class.cost_element_id.in_(ce_subq))
            else:
                # Full chain: CE -> WBE -> project
                wbe_subq = (
                    select(WBE.wbe_id)
                    .where(WBE.project_id.in_(target_project_ids))
                )
                ce_subq = (
                    select(CostElement.cost_element_id)
                    .where(CostElement.wbe_id.in_(wbe_subq))
                )
                stmt = stmt.where(entity_class.cost_element_id.in_(ce_subq))
            return stmt

        return stmt

    @staticmethod
    def _get_display_name(row: Any, entity_type: str) -> str | None:
        """Get the display name for an entity, handling entity-specific fields."""
        if entity_type == "change_order":
            return getattr(row, "title", None)
        if entity_type == "user":
            return getattr(row, "full_name", None)
        return getattr(row, "name", None)

    @staticmethod
    def _get_description(row: Any, entity_type: str) -> str | None:
        """Get the description field, handling entity-specific fields."""
        if entity_type == "forecast":
            return getattr(row, "basis_of_estimate", None)
        return getattr(row, "description", None)
