"""Cost Element Type Service - versionable entity management."""

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
from app.models.domain.cost_element_type import CostElementType
from app.models.schemas.cost_element_type import (
    CostElementTypeCreate,
    CostElementTypeUpdate,
)


class CostElementTypeService(TemporalService[CostElementType]):  # type: ignore[type-var,unused-ignore]
    """Service for Cost Element Type management (versionable, not branchable)."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session.

        Args:
            db: Async database session
        """
        super().__init__(CostElementType, db)

    async def create(  # type: ignore[override]
        self, type_in: CostElementTypeCreate, actor_id: UUID
    ) -> CostElementType:
        """Create new cost element type using CreateVersionCommand."""
        type_data = type_in.model_dump()

        # Ensure root cost_element_type_id exists
        root_id = uuid4()
        type_data["cost_element_type_id"] = root_id

        cmd = CreateVersionCommand(
            entity_class=CostElementType,  # type: ignore[type-var,unused-ignore]
            root_id=root_id,
            actor_id=actor_id,
            **type_data,
        )
        return await cmd.execute(self.session)

    async def update(  # type: ignore[override]
        self,
        cost_element_type_id: UUID,
        type_in: CostElementTypeUpdate,
        actor_id: UUID,
    ) -> CostElementType:
        """Update cost element type using UpdateVersionCommand."""
        update_data = type_in.model_dump(exclude_unset=True)

        # Custom command class to handle multi-word entity name
        class CostElementTypeUpdateCommand(UpdateVersionCommand[CostElementType]):  # type: ignore[type-var,unused-ignore]
            def _root_field_name(self) -> str:
                return "cost_element_type_id"

        cmd = CostElementTypeUpdateCommand(
            entity_class=CostElementType,  # type: ignore[type-var,unused-ignore]
            root_id=cost_element_type_id,
            actor_id=actor_id,
            **update_data,
        )
        return await cmd.execute(self.session)

    async def soft_delete(self, cost_element_type_id: UUID, actor_id: UUID) -> None:
        """Soft delete cost element type using SoftDeleteCommand."""

        class CostElementTypeSoftDeleteCommand(SoftDeleteCommand[CostElementType]):  # type: ignore[type-var,unused-ignore]
            def _root_field_name(self) -> str:
                return "cost_element_type_id"

        cmd = CostElementTypeSoftDeleteCommand(
            entity_class=CostElementType,  # type: ignore[type-var,unused-ignore]
            root_id=cost_element_type_id,
            actor_id=actor_id,
        )
        await cmd.execute(self.session)

    async def get_by_id(self, cost_element_type_id: UUID) -> CostElementType | None:
        """Get current cost element type by root ID."""
        stmt = (
            select(CostElementType)
            .where(
                CostElementType.cost_element_type_id == cost_element_type_id,
                func.upper(CostElementType.valid_time).is_(None),
                CostElementType.deleted_at.is_(None),
            )
            .order_by(CostElementType.valid_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_cost_element_types(
        self,
        filters: dict[str, Any] | None = None,
        skip: int = 0,
        limit: int = 100000,
        search: str | None = None,
        filter_string: str | None = None,
        sort_field: str | None = None,
        sort_order: str = "asc",
    ) -> tuple[list[CostElementType], int]:
        """Get cost element types with server-side features."""
        from typing import Any

        from sqlalchemy import and_, func, or_

        from app.core.filtering import FilterParser

        stmt = select(CostElementType).where(
            func.upper(CostElementType.valid_time).is_(None),
            CostElementType.deleted_at.is_(None),
        )

        if filters:
            if "department_id" in filters:
                stmt = stmt.where(
                    CostElementType.department_id == filters["department_id"]
                )

        if search:
            search_term = f"%{search}%"
            stmt = stmt.where(
                or_(
                    CostElementType.code.ilike(search_term),
                    CostElementType.name.ilike(search_term),
                )
            )

        if filter_string:
            allowed_fields = ["code", "name"]
            parsed_filters = FilterParser.parse_filters(filter_string)
            filter_expressions = FilterParser.build_sqlalchemy_filters(
                cast(Any, CostElementType),
                parsed_filters,
                allowed_fields=allowed_fields,
            )
            if filter_expressions:
                stmt = stmt.where(and_(*filter_expressions))

        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        # Apply sorting
        if sort_field and hasattr(CostElementType, sort_field):
            column = getattr(CostElementType, sort_field)
            if sort_order.lower() == "desc":
                stmt = stmt.order_by(column.desc())
            else:
                stmt = stmt.order_by(column.asc())
        else:
            stmt = stmt.order_by(CostElementType.name.asc())

        stmt = stmt.offset(skip).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def list(
        self, filters: dict[str, Any] | None = None, skip: int = 0, limit: int = 100000
    ) -> list[CostElementType]:
        """Legacy list method (backward compatibility)."""
        items, _ = await self.get_cost_element_types(
            filters=filters, skip=skip, limit=limit
        )
        return items
