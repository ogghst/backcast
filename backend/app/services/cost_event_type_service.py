"""Cost Event Type Service - versionable entity management."""

from datetime import datetime
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.temporal_queries import is_current_version
from app.core.versioning.commands import (
    CreateVersionCommand,
    SoftDeleteCommand,
    UpdateVersionCommand,
)
from app.core.versioning.service import TemporalService
from app.models.domain.cost_event_type import CostEventType
from app.models.schemas.cost_event_type import (
    CostEventTypeCreate,
    CostEventTypeUpdate,
)


class CostEventTypeService(TemporalService[CostEventType]):  # type: ignore[type-var,unused-ignore]
    """Service for Cost Event Type management (versionable, not branchable)."""

    def __init__(self, db: AsyncSession):
        super().__init__(CostEventType, db)

    async def create(  # type: ignore[override]
        self, type_in: CostEventTypeCreate, actor_id: UUID
    ) -> CostEventType:
        type_data = type_in.model_dump(exclude_unset=True)
        root_id = type_in.cost_event_type_id or uuid4()
        type_data["cost_event_type_id"] = root_id

        control_date = getattr(type_in, "control_date", None)
        type_data.pop("control_date", None)

        cmd = CreateVersionCommand(  # type: ignore[type-var]
            entity_class=CostEventType,
            root_id=root_id,
            actor_id=actor_id,
            control_date=control_date,
            **type_data,
        )
        return await cmd.execute(self.session)

    async def update(  # type: ignore[override]
        self,
        cost_event_type_id: UUID,
        type_in: CostEventTypeUpdate,
        actor_id: UUID,
    ) -> CostEventType:
        update_data = type_in.model_dump(exclude_unset=True)

        class CETUpdateCommand(UpdateVersionCommand[CostEventType]):  # type: ignore[type-var,unused-ignore]
            def _root_field_name(self) -> str:
                return "cost_event_type_id"

        control_date = getattr(type_in, "control_date", None)
        update_data.pop("control_date", None)

        cmd = CETUpdateCommand(
            entity_class=CostEventType,
            root_id=cost_event_type_id,
            actor_id=actor_id,
            control_date=control_date,
            **update_data,
        )
        return await cmd.execute(self.session)

    async def soft_delete(
        self,
        cost_event_type_id: UUID,
        actor_id: UUID,
        control_date: datetime | None = None,
    ) -> None:
        class CETSoftDeleteCommand(SoftDeleteCommand[CostEventType]):  # type: ignore[type-var,unused-ignore]
            def _root_field_name(self) -> str:
                return "cost_event_type_id"

        cmd = CETSoftDeleteCommand(
            entity_class=CostEventType,
            root_id=cost_event_type_id,
            actor_id=actor_id,
            control_date=control_date,
        )
        await cmd.execute(self.session)

    async def get_by_id(self, cost_event_type_id: UUID) -> CostEventType | None:
        stmt = (
            select(CostEventType)
            .where(
                CostEventType.cost_event_type_id == cost_event_type_id,
                is_current_version(CostEventType.valid_time, CostEventType.deleted_at),
            )
            .order_by(CostEventType.valid_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_history(self, cost_event_type_id: UUID) -> list[CostEventType]:
        stmt = (
            select(CostEventType)
            .where(CostEventType.cost_event_type_id == cost_event_type_id)
            .order_by(CostEventType.valid_time.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_cost_event_types(
        self,
        filters: dict[str, Any] | None = None,
        skip: int = 0,
        limit: int = 100000,
        search: str | None = None,
        filter_string: str | None = None,
        sort_field: str | None = None,
        sort_order: str = "asc",
    ) -> tuple[list[CostEventType], int]:
        from sqlalchemy import and_, or_

        from app.core.filtering import FilterParser

        stmt = select(CostEventType).where(
            is_current_version(CostEventType.valid_time, CostEventType.deleted_at)
        )

        if search:
            search_term = f"%{search}%"
            stmt = stmt.where(
                or_(
                    CostEventType.code.ilike(search_term),
                    CostEventType.name.ilike(search_term),
                )
            )

        if filter_string:
            allowed_fields = ["code", "name", "is_quality"]
            parsed_filters = FilterParser.parse_filters(filter_string)
            filter_expressions = FilterParser.build_sqlalchemy_filters(
                cast(Any, CostEventType),
                parsed_filters,
                allowed_fields=allowed_fields,
            )
            if filter_expressions:
                stmt = stmt.where(and_(*filter_expressions))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        if sort_field and hasattr(CostEventType, sort_field):
            column = getattr(CostEventType, sort_field)
            if sort_order.lower() == "desc":
                stmt = stmt.order_by(column.desc())
            else:
                stmt = stmt.order_by(column.asc())
        else:
            stmt = stmt.order_by(CostEventType.name.asc())

        stmt = stmt.offset(skip).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total
