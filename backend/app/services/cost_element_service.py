"""Cost Element Service - branchable entity management."""

import builtins
from collections.abc import Sequence
from datetime import datetime
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.versioning.commands import (
    CreateVersionCommand,
    SoftDeleteCommand,
    UpdateVersionCommand,
)
from app.core.versioning.service import TemporalService
from app.models.domain.cost_element import CostElement
from app.models.domain.cost_element_type import CostElementType
from app.models.domain.wbe import WBE
from app.models.schemas.cost_element import CostElementCreate, CostElementUpdate


class CostElementService(TemporalService[CostElement]):  # type: ignore[type-var,unused-ignore]
    """Service for Cost Element management (branchable + versionable)."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session.

        Args:
            db: Async database session
        """
        super().__init__(CostElement, db)

    def _get_base_stmt(self) -> Any:
        """Get base select statement with WBE name and CostElementType joins."""
        from sqlalchemy.orm import aliased

        WBEAlias = aliased(WBE, name="wbe_lookup")
        TypeAlias = aliased(CostElementType, name="type_lookup")

        # Subquery for current WBE versions
        wbe_subq = (
            select(WBEAlias.wbe_id, WBEAlias.name.label("wbe_name"))
            .where(
                func.upper(cast(Any, WBEAlias).valid_time).is_(None),
                cast(Any, WBEAlias).deleted_at.is_(None),
            )
            .subquery("wbe_lookup_subq")
        )

        # Subquery for current CostElementType versions
        type_subq = (
            select(
                TypeAlias.cost_element_type_id,
                TypeAlias.name.label("type_name"),
                TypeAlias.code.label("type_code"),
            )
            .where(
                func.upper(cast(Any, TypeAlias).valid_time).is_(None),
                cast(Any, TypeAlias).deleted_at.is_(None),
            )
            .subquery("type_lookup_subq")
        )

        return (
            select(
                CostElement,
                wbe_subq.c.wbe_name,
                type_subq.c.type_name,
                type_subq.c.type_code,
            )
            .outerjoin(wbe_subq, CostElement.wbe_id == wbe_subq.c.wbe_id)
            .outerjoin(
                type_subq,
                CostElement.cost_element_type_id == type_subq.c.cost_element_type_id,
            )
        )

    async def _resolve_relations(
        self, query_results: Sequence[Any]
    ) -> list[CostElement]:
        """Helper to resolve related names for a list of results."""
        resolved = []
        for item in query_results:
            if hasattr(item, "__iter__") and not isinstance(item, (str, bytes)):
                item_list = list(item)
                if len(item_list) >= 4:
                    # entity, wbe_name, type_name, type_code
                    entity = item_list[0]
                    entity.wbe_name = item_list[1]
                    entity.cost_element_type_name = item_list[2]
                    entity.cost_element_type_code = item_list[3]
                    resolved.append(entity)
                elif len(item_list) >= 2:
                    # Fallback for backwards compatibility
                    entity, wbe_name = item_list[0], item_list[1]
                    entity.wbe_name = wbe_name
                    resolved.append(entity)
                else:
                    resolved.append(item_list[0])
            else:
                resolved.append(item)
        return resolved

    async def create(  # type: ignore[override]
        self,
        element_in: CostElementCreate,
        actor_id: UUID,
        branch: str = "main",
        control_date: datetime | None = None,
    ) -> CostElement:
        """Create new cost element using CreateVersionCommand."""
        element_data = element_in.model_dump(exclude_unset=True)

        # Use provided cost_element_id (for seeding) or generate new one
        root_id = element_in.cost_element_id or uuid4()
        element_data["cost_element_id"] = root_id
        element_data["branch"] = branch

        cmd = CreateVersionCommand(
            entity_class=CostElement,  # type: ignore[type-var,unused-ignore]
            root_id=root_id,
            actor_id=actor_id,
            control_date=control_date,
            **element_data,
        )
        return await cmd.execute(self.session)

    async def update(  # type: ignore[override]
        self,
        cost_element_id: UUID,
        element_in: CostElementUpdate,
        actor_id: UUID,
        branch: str = "main",
        control_date: datetime | None = None,
    ) -> CostElement:
        """Update cost element using UpdateVersionCommand or Fork if new branch."""
        update_data = element_in.model_dump(exclude_unset=True)
        update_data["branch"] = branch

        # Check if version exists in target branch
        # We need to manage the query manually to avoid TemporalService issues and handle branching
        current = await self.get_by_id(cost_element_id, branch=branch)

        if current:
            # Linear update in same branch: Close old, Open new

            # Custom command class to handle multi-word entity name AND branch filtering
            class CostElementUpdateCommand(UpdateVersionCommand[CostElement]):  # type: ignore[type-var,unused-ignore]
                def __init__(
                    self,
                    entity_class: type[CostElement],
                    root_id: UUID,
                    actor_id: UUID,
                    branch: str = "main",
                    control_date: datetime | None = None,
                    **updates: Any,
                ) -> None:
                    super().__init__(entity_class, root_id, actor_id, control_date=control_date, **updates)
                    self.branch = branch

                def _root_field_name(self) -> str:
                    return "cost_element_id"

                async def _get_current(self, session: AsyncSession) -> Any | None:
                    stmt = (
                        select(self.entity_class)
                        .where(
                            getattr(self.entity_class, self._root_field_name())
                            == self.root_id,
                            self.entity_class.branch == self.branch,
                            func.upper(cast(Any, self.entity_class).valid_time).is_(
                                None
                            ),
                            cast(Any, self.entity_class).deleted_at.is_(None),
                        )
                        .order_by(cast(Any, self.entity_class).valid_time.desc())
                        .limit(1)
                    )
                    result = await session.execute(stmt)
                    return result.scalar_one_or_none()

            cmd = CostElementUpdateCommand(
                entity_class=CostElement,  # type: ignore[type-var,unused-ignore]
                root_id=cost_element_id,
                actor_id=actor_id,
                control_date=control_date,
                # Branch is passed via update_data unpacking to match signature
                **update_data,
            )
            return await cmd.execute(self.session)

        else:
            # Version not found in target branch -> Fork from main (or parent)
            # This handles "Create Branch" scenario implicitly on update

            # Try to find source in 'main' to fork from
            # Note: In a real system we might want to let the caller specify the source branch
            source_version = await self.get_by_id(cost_element_id, branch="main")
            if not source_version:
                # If not found in main either, we can't update a non-existent entity
                raise ValueError(
                    f"Cost Element {cost_element_id} not found in {branch} or main."
                )

            # Clone data from source
            data = {
                c.name: getattr(source_version, c.name)
                for c in source_version.__table__.columns
            }

            # Remove system/audit fields to let DB/Command handle them
            system_fields = [
                "valid_time",
                "transaction_time",
                "created_by",
                "deleted_by",
                "deleted_at",
                "id",  # New version needs new ID
            ]
            for field in system_fields:
                data.pop(field, None)

            # Apply updates
            data.update(update_data)

            # Set branching metadata
            data["branch"] = branch
            data["parent_id"] = source_version.id  # Link to parent version

            # Create new version (Insert only, do not close parent)
            create_cmd = CreateVersionCommand(
                entity_class=CostElement,  # type: ignore[type-var,unused-ignore]
                root_id=cost_element_id,
                actor_id=actor_id,
                control_date=control_date,
                **data,
            )
            return await create_cmd.execute(self.session)

    async def soft_delete(
        self,
        cost_element_id: UUID,
        actor_id: UUID,
        branch: str = "main",
        control_date: datetime | None = None
    ) -> None:
        """Soft delete cost element using SoftDeleteCommand."""

        # Custom command class
        class CostElementSoftDeleteCommand(SoftDeleteCommand[CostElement]):  # type: ignore[type-var,unused-ignore]
            def __init__(
                self,
                entity_class: type[CostElement],
                root_id: UUID,
                actor_id: UUID,
                branch: str = "main",
                control_date: datetime | None = None,
            ) -> None:
                super().__init__(entity_class, root_id, actor_id, control_date=control_date)
                self.branch = branch

            def _root_field_name(self) -> str:
                return "cost_element_id"

            async def _get_current(self, session: AsyncSession) -> Any | None:
                """Get current active version filtering by branch."""
                stmt = (
                    select(self.entity_class)
                    .where(
                        getattr(self.entity_class, self._root_field_name())
                        == self.root_id,
                        self.entity_class.branch == self.branch,
                        func.upper(cast(Any, self.entity_class).valid_time).is_(None),
                        cast(Any, self.entity_class).deleted_at.is_(None),
                    )
                    .order_by(cast(Any, self.entity_class).valid_time.desc())
                    .limit(1)
                )
                result = await session.execute(stmt)
                return result.scalar_one_or_none()

        cmd = CostElementSoftDeleteCommand(
            entity_class=CostElement,  # type: ignore[type-var,unused-ignore]
            root_id=cost_element_id,
            actor_id=actor_id,
            branch=branch,
            control_date=control_date,
        )
        await cmd.execute(self.session)

    async def get_by_id(
        self, cost_element_id: UUID, branch: str = "main"
    ) -> CostElement | None:
        """Get cost element by root ID and branch with WBE name."""
        stmt = (
            self._get_base_stmt()
            .where(
                CostElement.cost_element_id == cost_element_id,
                CostElement.branch == branch,
                func.upper(cast(Any, CostElement).valid_time).is_(None),
                cast(Any, CostElement).deleted_at.is_(None),
            )
            .order_by(cast(Any, CostElement).valid_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        resolved = await self._resolve_relations(result.all())
        return resolved[0] if resolved else None

    async def get_cost_elements(
        self,
        filters: dict[str, Any] | None = None,
        branch: str = "main",
        skip: int = 0,
        limit: int = 100000,
        search: str | None = None,
        filter_string: str | None = None,
        sort_field: str | None = None,
        sort_order: str = "asc",
    ) -> tuple[list[CostElement], int]:
        """Get all cost elements with search, filtering, and sorting.

        Args:
            filters: Legacy dict filters (for backward compatibility)
            branch: Branch name to filter by (default: "main")
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
            search: Search term to match against code and name (case-insensitive)
            filter_string: Filter string in format "column:value;column:value1,value2"
                          Example: "code:LAB;name:Phase"
            sort_field: Field name to sort by (e.g., "name", "code", "budget_amount")
            sort_order: Sort order, either "asc" or "desc" (default: "asc")

        Returns:
            Tuple of (list of cost elements with relations, total count matching filters)

        Raises:
            ValueError: If invalid filter field or sort field is provided

        Examples:
            >>> # Get cost elements for a specific WBE
            >>> elements, total = await service.get_cost_elements(
            ...     filters={"wbe_id": wbe_id},
            ...     search="Mechanical",
            ...     sort_field="budget_amount",
            ...     sort_order="desc"
            ... )
        """
        from sqlalchemy import and_, or_

        from app.core.filtering import FilterParser

        # Base query with WBE name and type joins
        stmt = self._get_base_stmt().where(
            CostElement.branch == branch,
            func.upper(cast(Any, CostElement).valid_time).is_(None),
            cast(Any, CostElement).deleted_at.is_(None),
        )

        # Apply legacy dict filters (for backward compatibility)
        if filters:
            if "wbe_id" in filters:
                stmt = stmt.where(CostElement.wbe_id == filters["wbe_id"])
            if "cost_element_type_id" in filters:
                stmt = stmt.where(
                    CostElement.cost_element_type_id == filters["cost_element_type_id"]
                )

        # Apply search (across code and name)
        if search:
            search_term = f"%{search}%"
            stmt = stmt.where(
                or_(
                    CostElement.code.ilike(search_term),
                    CostElement.name.ilike(search_term),
                )
            )

        # Apply new filter string format
        if filter_string:
            # Define allowed filterable fields for security
            allowed_fields = ["code", "name"]

            parsed_filters = FilterParser.parse_filters(filter_string)
            filter_expressions = FilterParser.build_sqlalchemy_filters(
                cast(Any, CostElement), parsed_filters, allowed_fields=allowed_fields
            )
            if filter_expressions:
                stmt = stmt.where(and_(*filter_expressions))

        # Get total count (before pagination)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        # Apply sorting
        if sort_field:
            # Validate sort field exists on model
            if not hasattr(CostElement, sort_field):
                raise ValueError(f"Invalid sort field: {sort_field}")

            column = getattr(CostElement, sort_field)
            if sort_order.lower() == "desc":
                stmt = stmt.order_by(column.desc())
            else:
                stmt = stmt.order_by(column.asc())
        else:
            # Default sort by valid_time descending
            stmt = stmt.order_by(cast(Any, CostElement).valid_time.desc())

        # Apply pagination
        stmt = stmt.offset(skip).limit(limit)

        # Execute query
        result = await self.session.execute(stmt)
        cost_elements = await self._resolve_relations(result.all())

        return cost_elements, total

    async def list(
        self,
        filters: dict[str, Any] | None = None,
        branch: str = "main",
        skip: int = 0,
        limit: int = 100000,
    ) -> list[CostElement]:
        """Alias for get_cost_elements() to maintain backward compatibility.

        Note: Returns only items, not total count. Use get_cost_elements() for pagination.
        """
        items, _ = await self.get_cost_elements(
            filters=filters, branch=branch, skip=skip, limit=limit
        )
        return items

    async def get_history(self, root_id: UUID) -> builtins.list[CostElement]:
        """Get all versions of a cost element with creator, WBE name, and type info."""
        from sqlalchemy.orm import aliased

        from app.models.domain.user import User

        # User lookup subquery
        UserAlias = cast(Any, User)
        creator_subq = (
            select(UserAlias.user_id, UserAlias.full_name)
            .distinct(UserAlias.user_id)
            .order_by(UserAlias.user_id, UserAlias.transaction_time.desc())
            .subquery("creator_lookup")
        )

        # WBE lookup subquery
        WBEAlias = aliased(WBE, name="wbe_history_lookup")
        wbe_subq = (
            select(WBEAlias.wbe_id, WBEAlias.name.label("wbe_name"))
            .where(
                func.upper(cast(Any, WBEAlias).valid_time).is_(None),
                cast(Any, WBEAlias).deleted_at.is_(None),
            )
            .subquery("wbe_history_lookup_subq")
        )

        # CostElementType lookup subquery
        TypeAlias = aliased(CostElementType, name="type_history_lookup")
        type_subq = (
            select(
                TypeAlias.cost_element_type_id,
                TypeAlias.name.label("type_name"),
                TypeAlias.code.label("type_code"),
            )
            .where(
                func.upper(cast(Any, TypeAlias).valid_time).is_(None),
                cast(Any, TypeAlias).deleted_at.is_(None),
            )
            .subquery("type_history_lookup_subq")
        )

        stmt = (
            select(
                CostElement,
                creator_subq.c.full_name.label("created_by_name"),
                wbe_subq.c.wbe_name,
                type_subq.c.type_name,
                type_subq.c.type_code,
            )
            .outerjoin(creator_subq, CostElement.created_by == creator_subq.c.user_id)
            .outerjoin(wbe_subq, CostElement.wbe_id == wbe_subq.c.wbe_id)
            .outerjoin(
                type_subq,
                CostElement.cost_element_type_id == type_subq.c.cost_element_type_id,
            )
            .where(
                CostElement.cost_element_id == root_id,
                cast(Any, CostElement).deleted_at.is_(None),
            )
            .order_by(cast(Any, CostElement).transaction_time.desc())
        )

        result = await self.session.execute(stmt)
        history = []
        for row in result.all():
            entity, creator_name, wbe_name, type_name, type_code = row
            entity.created_by_name = creator_name
            entity.wbe_name = wbe_name
            entity.cost_element_type_name = type_name
            entity.cost_element_type_code = type_code
            history.append(entity)

        return history
