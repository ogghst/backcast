"""Global cross-entity search service.

Searches across all 13 searchable entity types (12 versioned + documents) sequentially
(SQLAlchemy AsyncSession does not support concurrent operations), applies
tier-appropriate temporal/branch/permission filters, scores by relevance, and returns
a flat ranked list.

Documents use SimpleEntityBase (no temporal/branch columns) and are searched via
a dedicated path that bypasses versioned-entity filters.
"""

from datetime import datetime
from typing import Any, Literal, cast
from uuid import UUID

from sqlalchemy import case, func, or_, select
from sqlalchemy import cast as sql_cast
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.versioning.enums import BranchMode
from app.models.domain.change_order import ChangeOrder
from app.models.domain.control_account import ControlAccount
from app.models.domain.cost_element import CostElement
from app.models.domain.cost_element_type import CostElementType
from app.models.domain.cost_registration import CostRegistration
from app.models.domain.document import Document
from app.models.domain.forecast import Forecast
from app.models.domain.organizational_unit import OrganizationalUnit
from app.models.domain.progress_entry import ProgressEntry
from app.models.domain.project import Project
from app.models.domain.schedule_baseline import ScheduleBaseline
from app.models.domain.user import User
from app.models.domain.wbs_element import WBSElement
from app.models.domain.work_package import WorkPackage
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
    *,
    cf_codes: list[str] | None = None,
) -> float:
    """Compute the best relevance score for a result row.

    Scoring tiers:
    - Primary fields (code, name): exact 1.0 / prefix 0.9 / ilike 0.7
    - Description fields: ilike 0.5
    - Secondary fields: ilike 0.3
    - Custom fields (Phase 2): substring 0.3 (same tier as secondary)

    Returns 0.0 if nothing matched (should not happen since rows are ILIKE-filtered).

    NOTE: custom-field VALUES are read here ONLY to score the row — they are
    NEVER serialized into the result snippet (no value leakage). The result
    object continues to surface standard fields (code/name/description) only.
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

    # Phase 2: custom fields — substring only, same tier as secondary (0.3).
    # Reads the value solely to score; the value is not returned to the caller.
    if cf_codes:
        cf_values = getattr(row, "custom_fields", None)
        if isinstance(cf_values, dict):
            for code in cf_codes:
                val = cf_values.get(code)
                if val is not None and query_lower in str(val).lower():
                    if 0.3 > best:
                        best = 0.3
                        break

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

    ISOLATED: only the specified branch.
    MERGED: DISTINCT ON with branch precedence (current branch over main).
    """
    if branch_mode == BranchMode.MERGED and branch != "main":
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
_ENTITY_CONFIG: list[
    tuple[str, type[Any], str, list[str], list[str], list[str], bool, bool]
] = [
    # Branchable entities
    (
        "project",
        Project,
        "project_id",
        ["code", "name"],
        ["description"],
        ["status"],
        True,
        False,
    ),
    (
        "wbs_element",
        WBSElement,
        "wbs_element_id",
        ["code", "name"],
        ["description"],
        [],
        True,
        False,
    ),
    (
        "cost_element",
        CostElement,
        "cost_element_id",
        ["code", "name"],
        ["description"],
        [],
        False,
        False,
    ),
    (
        "schedule_baseline",
        ScheduleBaseline,
        "schedule_baseline_id",
        ["name"],
        ["description"],
        [],
        True,
        False,
    ),
    (
        "change_order",
        ChangeOrder,
        "change_order_id",
        ["code", "title"],
        ["description", "justification"],
        ["status"],
        True,
        False,
    ),
    ("forecast", Forecast, "forecast_id", [], ["basis_of_estimate"], [], True, False),
    # Versionable entities
    (
        "cost_registration",
        CostRegistration,
        "cost_registration_id",
        [],
        ["description"],
        ["invoice_number", "vendor_reference"],
        False,
        False,
    ),
    (
        "work_package",
        WorkPackage,
        "work_package_id",
        ["name"],
        ["description"],
        ["coq_category"],
        True,
        False,
    ),
    (
        "progress_entry",
        ProgressEntry,
        "progress_entry_id",
        [],
        ["notes"],
        [],
        False,
        False,
    ),
    # Global entities (no project scoping)
    ("user", User, "user_id", ["email", "full_name"], [], [], False, True),
    (
        "organizational_unit",
        OrganizationalUnit,
        "organizational_unit_id",
        ["code", "name"],
        ["description"],
        [],
        False,
        True,
    ),
    (
        "cost_element_type",
        CostElementType,
        "cost_element_type_id",
        ["code", "name"],
        ["description"],
        [],
        False,
        True,
    ),
]

#: Phase 2: entity types that carry a ``custom_fields`` JSONB column, mapped
#: from the search label (``_ENTITY_CONFIG`` first tuple element) to the
#: ``CustomEntityTemplate.target_entity_type`` discriminator used by the
#: resolver. Entities absent here have NO custom-field search coverage.
_CF_ENTITY_TYPES: dict[str, str] = {
    "project": "PROJECT",
    "wbs_element": "WBS_ELEMENT",
    "work_package": "WORK_PACKAGE",
    "change_order": "CHANGE_ORDER",
}


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
        project_id: UUID | None = None,
        wbe_id: UUID | None = None,
        branch: str = "main",
        branch_mode: BranchMode = BranchMode.MERGED,
        as_of: datetime | None = None,
        limit: int = 50,
        search_mode: Literal["ui", "ai"] = "ui",
    ) -> GlobalSearchResponse:
        """Search across all entity types and return ranked results.

        Args:
            query: Search string (at least 1 character).
            user_id: Authenticated user ID for RBAC scoping.
            project_id: Optional project root ID to scope results.
            wbe_id: Optional WBS Element root ID to scope results (includes descendants).
            branch: Branch name (default "main").
            branch_mode: ISOLATED or MERGED for branchable entities.
            as_of: Optional timestamp for time-travel queries.
            limit: Maximum results to return.
            search_mode: ``"ui"`` gates custom-field matching on ``searchable``;
                ``"ai"`` gates on ``ai_visible`` (D8: only ai_visible fields ever
                reach the LLM via search). Defaults to ``"ui"``.

        Returns:
            GlobalSearchResponse with ranked results.
        """
        # 1. Resolve accessible project IDs via RBAC
        accessible_project_ids = await self._get_accessible_projects(user_id)

        # 2. If wbe_id provided, resolve descendant WBS Element IDs
        wbe_ids: list[UUID] | None = None
        if wbe_id is not None:
            wbe_ids = await self._resolve_wbe_descendants(
                wbe_id, branch, branch_mode, as_of
            )
            wbe_ids.append(wbe_id)

        # Phase 2: resolve the searchable/ai_visible custom-field code map
        # ONCE per entity type that has a custom_fields column. UI mode gates on
        # ``searchable``; AI mode gates on ``ai_visible`` (D8).
        flag = "searchable" if search_mode == "ui" else "ai_visible"
        from app.services.custom_field_service import CustomFieldService

        cf_service = CustomFieldService(self.session)
        cf_codes_by_type: dict[str, list[str]] = {}
        for entity_type, target_type in _CF_ENTITY_TYPES.items():
            codes = await cf_service.list_current_field_codes(target_type, flag=flag)
            if codes:
                cf_codes_by_type[entity_type] = list(codes.keys())

        # 3. Run all entity searches sequentially (async session limitation)
        search_term = f"%{query}%"
        query_lower = query.lower()

        all_results_lists: list[list[SearchResultItem]] = []
        for config in _ENTITY_CONFIG:
            entity_type = config[0]
            results = await self._search_entity(
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
                cf_codes=cf_codes_by_type.get(entity_type, []),
            )
            all_results_lists.append(results)

        # Documents use SimpleEntityBase (no temporal/branch columns),
        # so they need a separate search path.
        doc_results = await self._search_documents(
            search_term=search_term,
            query_lower=query_lower,
            accessible_project_ids=accessible_project_ids,
            project_id=project_id,
            wbe_ids=wbe_ids,
            as_of=as_of,
            branch=branch,
            branch_mode=branch_mode,
            limit=limit,
        )
        all_results_lists.append(doc_results)

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
    ) -> list[UUID]:
        """Get project IDs accessible to the user via RBAC.

        Admin users see all projects. Others are filtered by membership.
        """
        from app.core.rbac_unified import (
            get_unified_rbac_service,
            set_unified_rbac_session,
        )

        set_unified_rbac_session(self.session)
        service = get_unified_rbac_service()
        return await service.get_accessible_projects(user_id)

    async def _resolve_wbe_descendants(
        self,
        root_wbe_id: UUID,
        branch: str,
        branch_mode: BranchMode,
        as_of: datetime | None,
    ) -> list[UUID]:
        """Resolve all descendant WBS Element IDs for a given root WBS Element.

        Uses iterative BFS via parent_wbs_element_id hierarchy.
        Returns a list of descendant root IDs (not including root_wbe_id itself).
        """
        descendants: list[UUID] = []
        queue: list[UUID] = [root_wbe_id]

        while queue:
            parent_ids = queue
            queue = []

            stmt = select(WBSElement.wbs_element_id).where(
                WBSElement.parent_wbs_element_id.in_(parent_ids),
            )
            stmt = self._apply_temporal_filter(stmt, WBSElement, as_of)
            stmt = _apply_branch_mode_filter(
                stmt, WBSElement, "wbs_element_id", branch, branch_mode
            )
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
        cf_codes: list[str] | None = None,
    ) -> list[SearchResultItem]:
        """Search a single entity type and return scored results.

        Phase 2: ``cf_codes`` (when non-empty) extends the ILIKE OR-clause with
        one ``custom_fields->>code ILIKE :term`` per resolved code. The codes are
        already gated on ``searchable`` (UI) or ``ai_visible`` (AI) by the
        caller. Custom-field JSONB participates ONLY in the match; result
        snippets surface standard fields only (no value leakage).
        """
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

        # Phase 2: extend the OR clause with custom-field ILIKEs. Only entities
        # that carry a custom_fields column AND have resolved codes contribute.
        if cf_codes and hasattr(entity_class, "custom_fields"):
            for code in cf_codes:
                ilike_clauses.append(
                    entity_class.custom_fields.op("->>")(code).ilike(search_term)
                )

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
                as_of,
                branch,
                branch_mode,
            )

        # Limit rows fetched per entity type
        stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        rows = result.scalars().all()

        # Score and convert to SearchResultItem
        items: list[SearchResultItem] = []
        for row in rows:
            score = _best_score(
                row,
                query_lower,
                primary_fields,
                description_fields,
                secondary_fields,
                cf_codes=cf_codes,
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
                wbs_element_id=getattr(row, "wbs_element_id", None),
            )
            items.append(item)

        return items

    async def _search_documents(
        self,
        search_term: str,
        query_lower: str,
        accessible_project_ids: list[UUID],
        project_id: UUID | None,
        wbe_ids: list[UUID] | None,
        as_of: datetime | None,
        branch: str,
        branch_mode: BranchMode,
        limit: int,
    ) -> list[SearchResultItem]:
        """Search documents by name, description, extension, and tags.

        Documents are SimpleEntityBase entities (no temporal/branch columns),
        so they bypass the versioned entity search path entirely.
        """
        if not accessible_project_ids:
            return []

        target_project_ids = accessible_project_ids
        if project_id is not None:
            if project_id not in accessible_project_ids:
                return []
            target_project_ids = [project_id]

        # When wbe_ids provided, restrict to projects containing those WBS elements
        if wbe_ids is not None:
            wbe_project_subq = select(WBSElement.project_id).where(
                WBSElement.wbs_element_id.in_(wbe_ids)
            )
            wbe_project_subq = self._apply_scope_filters(
                wbe_project_subq,
                WBSElement,
                "wbs_element_id",
                as_of,
                branch,
                branch_mode,
            )
            wbe_proj_result = await self.session.execute(wbe_project_subq)
            wbe_project_ids = [row[0] for row in wbe_proj_result.all()]
            target_project_ids = [
                pid for pid in target_project_ids if pid in wbe_project_ids
            ]
            if not target_project_ids:
                return []

        stmt = (
            select(Document)
            .where(
                Document.project_id.in_([str(pid) for pid in target_project_ids]),
                or_(
                    Document.name.ilike(search_term),
                    Document.description.ilike(search_term),
                    Document.extension.ilike(search_term),
                ),
            )
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        rows = result.scalars().all()

        items: list[SearchResultItem] = []
        for row in rows:
            score = _best_score(
                row,
                query_lower,
                primary_fields=["name", "extension"],
                description_fields=["description"],
                secondary_fields=[],
            )
            if score <= 0.0:
                continue

            item = SearchResultItem(
                entity_type="document",
                id=row.id,
                root_id=row.id,
                code=None,
                name=row.name,
                description=row.description,
                status=None,
                relevance_score=score,
                project_id=str(row.project_id) if row.project_id else None,
                wbs_element_id=None,
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

    def _apply_scope_filters(
        self,
        stmt: Any,
        entity_class: type[Any],
        root_field: str,
        as_of: datetime | None,
        branch: str,
        branch_mode: BranchMode,
    ) -> Any:
        """Apply temporal and branch filters to an intermediate entity subquery."""
        stmt = self._apply_temporal_filter(stmt, entity_class, as_of)
        if hasattr(entity_class, "branch"):
            stmt = _apply_branch_mode_filter(
                stmt, entity_class, root_field, branch, branch_mode
            )
        return stmt

    def _apply_project_scope(
        self,
        stmt: Any,
        entity_class: type[Any],
        root_field: str,
        accessible_project_ids: list[UUID],
        project_id: UUID | None,
        wbe_ids: list[UUID] | None,
        as_of: datetime | None,
        branch: str,
        branch_mode: BranchMode,
    ) -> Any:
        """Apply RBAC project scoping to the query.

        Strategy varies by how the entity links to a project:
        - Direct project_id column: filter directly (resolves project from wbe_ids
          when provided, otherwise uses target_project_ids).
        - wbs_element_id column: join to WBSElement, filter by wbe_ids or
          WBSElement.project_id.
        - cost_element_id column: join chain CE -> WP -> CA -> WBSElement -> project.
        - control_account_id column: join chain CA -> WBSElement -> project.
        - work_package_id column: join chain WP -> CA -> WBSElement -> project.
        - Reverse FK via WorkPackage: entities like ScheduleBaseline and Forecast that
          have no direct project link but are referenced by WorkPackage FK columns.
          Resolves accessible WP IDs via WP -> CA -> WBS -> project, then filters
          by the FK column matching root_field.
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
            if wbe_ids is not None:
                # Resolve project IDs that contain the specified WBS elements
                wbe_project_subq = select(WBSElement.project_id).where(
                    WBSElement.wbs_element_id.in_(wbe_ids)
                )
                wbe_project_subq = self._apply_scope_filters(
                    wbe_project_subq,
                    WBSElement,
                    "wbs_element_id",
                    as_of,
                    branch,
                    branch_mode,
                )
                stmt = stmt.where(entity_class.project_id.in_(wbe_project_subq))
            else:
                stmt = stmt.where(entity_class.project_id.in_(target_project_ids))
            return stmt

        # Entity has wbs_element_id -> join to WBSElement for project_id
        if hasattr(entity_class, "wbs_element_id") and not hasattr(
            entity_class, "cost_element_id"
        ):
            if wbe_ids is not None:
                stmt = stmt.where(entity_class.wbs_element_id.in_(wbe_ids))
            else:
                wbe_subq = (
                    select(WBSElement.wbs_element_id)
                    .where(WBSElement.project_id.in_(target_project_ids))
                    .correlate(entity_class)
                )
                wbe_subq = self._apply_scope_filters(
                    wbe_subq,
                    WBSElement,
                    "wbs_element_id",
                    as_of,
                    branch,
                    branch_mode,
                )
                stmt = stmt.where(entity_class.wbs_element_id.in_(wbe_subq))
            return stmt

        # Entity has cost_element_id -> join chain CE -> WP -> CA -> WBSElement -> project
        if hasattr(entity_class, "cost_element_id"):
            if wbe_ids is not None:
                ca_subq = select(ControlAccount.control_account_id).where(
                    ControlAccount.wbs_element_id.in_(wbe_ids)
                )
                ca_subq = self._apply_scope_filters(
                    ca_subq,
                    ControlAccount,
                    "control_account_id",
                    as_of,
                    branch,
                    branch_mode,
                )
                wp_subq = select(WorkPackage.work_package_id).where(
                    WorkPackage.control_account_id.in_(ca_subq)
                )
                wp_subq = self._apply_scope_filters(
                    wp_subq,
                    WorkPackage,
                    "work_package_id",
                    as_of,
                    branch,
                    branch_mode,
                )
                ce_subq = select(CostElement.cost_element_id).where(
                    CostElement.work_package_id.in_(wp_subq)
                )
                ce_subq = self._apply_scope_filters(
                    ce_subq,
                    CostElement,
                    "cost_element_id",
                    as_of,
                    branch,
                    branch_mode,
                )
                stmt = stmt.where(entity_class.cost_element_id.in_(ce_subq))
            else:
                # Full chain: CE -> WP -> CA -> WBSElement -> project
                wbe_subq = select(WBSElement.wbs_element_id).where(
                    WBSElement.project_id.in_(target_project_ids)
                )
                wbe_subq = self._apply_scope_filters(
                    wbe_subq,
                    WBSElement,
                    "wbs_element_id",
                    as_of,
                    branch,
                    branch_mode,
                )
                ca_subq = select(ControlAccount.control_account_id).where(
                    ControlAccount.wbs_element_id.in_(wbe_subq)
                )
                ca_subq = self._apply_scope_filters(
                    ca_subq,
                    ControlAccount,
                    "control_account_id",
                    as_of,
                    branch,
                    branch_mode,
                )
                wp_subq = select(WorkPackage.work_package_id).where(
                    WorkPackage.control_account_id.in_(ca_subq)
                )
                wp_subq = self._apply_scope_filters(
                    wp_subq,
                    WorkPackage,
                    "work_package_id",
                    as_of,
                    branch,
                    branch_mode,
                )
                ce_subq = select(CostElement.cost_element_id).where(
                    CostElement.work_package_id.in_(wp_subq)
                )
                ce_subq = self._apply_scope_filters(
                    ce_subq,
                    CostElement,
                    "cost_element_id",
                    as_of,
                    branch,
                    branch_mode,
                )
                stmt = stmt.where(entity_class.cost_element_id.in_(ce_subq))
            return stmt

        # Entity has control_account_id -> join chain CA -> WBSElement -> project
        if hasattr(entity_class, "control_account_id"):
            if wbe_ids is not None:
                ca_subq = select(ControlAccount.control_account_id).where(
                    ControlAccount.wbs_element_id.in_(wbe_ids)
                )
                ca_subq = self._apply_scope_filters(
                    ca_subq,
                    ControlAccount,
                    "control_account_id",
                    as_of,
                    branch,
                    branch_mode,
                )
                stmt = stmt.where(entity_class.control_account_id.in_(ca_subq))
            else:
                wbe_subq = select(WBSElement.wbs_element_id).where(
                    WBSElement.project_id.in_(target_project_ids)
                )
                wbe_subq = self._apply_scope_filters(
                    wbe_subq,
                    WBSElement,
                    "wbs_element_id",
                    as_of,
                    branch,
                    branch_mode,
                )
                ca_subq = select(ControlAccount.control_account_id).where(
                    ControlAccount.wbs_element_id.in_(wbe_subq)
                )
                ca_subq = self._apply_scope_filters(
                    ca_subq,
                    ControlAccount,
                    "control_account_id",
                    as_of,
                    branch,
                    branch_mode,
                )
                stmt = stmt.where(entity_class.control_account_id.in_(ca_subq))
            return stmt

        # Entity has work_package_id -> join chain WP -> CA -> WBSElement -> project
        if hasattr(entity_class, "work_package_id") and not hasattr(
            entity_class, "cost_element_id"
        ):
            if wbe_ids is not None:
                ca_subq = select(ControlAccount.control_account_id).where(
                    ControlAccount.wbs_element_id.in_(wbe_ids)
                )
                ca_subq = self._apply_scope_filters(
                    ca_subq,
                    ControlAccount,
                    "control_account_id",
                    as_of,
                    branch,
                    branch_mode,
                )
                wp_subq = select(WorkPackage.work_package_id).where(
                    WorkPackage.control_account_id.in_(ca_subq)
                )
                wp_subq = self._apply_scope_filters(
                    wp_subq,
                    WorkPackage,
                    "work_package_id",
                    as_of,
                    branch,
                    branch_mode,
                )
                stmt = stmt.where(entity_class.work_package_id.in_(wp_subq))
            else:
                wbe_subq = select(WBSElement.wbs_element_id).where(
                    WBSElement.project_id.in_(target_project_ids)
                )
                wbe_subq = self._apply_scope_filters(
                    wbe_subq,
                    WBSElement,
                    "wbs_element_id",
                    as_of,
                    branch,
                    branch_mode,
                )
                ca_subq = select(ControlAccount.control_account_id).where(
                    ControlAccount.wbs_element_id.in_(wbe_subq)
                )
                ca_subq = self._apply_scope_filters(
                    ca_subq,
                    ControlAccount,
                    "control_account_id",
                    as_of,
                    branch,
                    branch_mode,
                )
                wp_subq = select(WorkPackage.work_package_id).where(
                    WorkPackage.control_account_id.in_(ca_subq)
                )
                wp_subq = self._apply_scope_filters(
                    wp_subq,
                    WorkPackage,
                    "work_package_id",
                    as_of,
                    branch,
                    branch_mode,
                )
                stmt = stmt.where(entity_class.work_package_id.in_(wp_subq))
            return stmt

        # Entities linked to project only through a reverse FK on WorkPackage
        # (e.g. ScheduleBaseline via WorkPackage.schedule_baseline_id,
        #  Forecast via WorkPackage.forecast_id).
        # Check if WorkPackage has a column matching this entity's root_field.
        if hasattr(WorkPackage, root_field):
            if wbe_ids is not None:
                ca_subq = select(ControlAccount.control_account_id).where(
                    ControlAccount.wbs_element_id.in_(wbe_ids)
                )
                ca_subq = self._apply_scope_filters(
                    ca_subq,
                    ControlAccount,
                    "control_account_id",
                    as_of,
                    branch,
                    branch_mode,
                )
                wp_subq = select(WorkPackage.work_package_id).where(
                    WorkPackage.control_account_id.in_(ca_subq)
                )
                wp_subq = self._apply_scope_filters(
                    wp_subq,
                    WorkPackage,
                    "work_package_id",
                    as_of,
                    branch,
                    branch_mode,
                )
            else:
                wbe_subq = select(WBSElement.wbs_element_id).where(
                    WBSElement.project_id.in_(target_project_ids)
                )
                wbe_subq = self._apply_scope_filters(
                    wbe_subq,
                    WBSElement,
                    "wbs_element_id",
                    as_of,
                    branch,
                    branch_mode,
                )
                ca_subq = select(ControlAccount.control_account_id).where(
                    ControlAccount.wbs_element_id.in_(wbe_subq)
                )
                ca_subq = self._apply_scope_filters(
                    ca_subq,
                    ControlAccount,
                    "control_account_id",
                    as_of,
                    branch,
                    branch_mode,
                )
                wp_subq = select(WorkPackage.work_package_id).where(
                    WorkPackage.control_account_id.in_(ca_subq)
                )
                wp_subq = self._apply_scope_filters(
                    wp_subq,
                    WorkPackage,
                    "work_package_id",
                    as_of,
                    branch,
                    branch_mode,
                )

            # Get distinct root_field values from accessible WorkPackages
            wp_fk_subq = (
                select(getattr(WorkPackage, root_field))
                .where(WorkPackage.work_package_id.in_(wp_subq))
                .where(getattr(WorkPackage, root_field).is_not(None))
            )
            stmt = stmt.where(getattr(entity_class, root_field).in_(wp_fk_subq))
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
