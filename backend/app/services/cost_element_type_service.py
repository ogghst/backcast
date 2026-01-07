"""Cost Element Type Service - versionable entity management."""

from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import select, func
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


class CostElementTypeService(TemporalService[CostElementType]):  # type: ignore[type-var]
    """Service for Cost Element Type management (versionable, not branchable)."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session.

        Args:
            db: Async database session
        """
        super().__init__(CostElementType, db)

    async def create(
        self, type_in: CostElementTypeCreate, actor_id: UUID
    ) -> CostElementType:
        """Create new cost element type using CreateVersionCommand."""
        type_data = type_in.model_dump()

        # Ensure root cost_element_type_id exists
        root_id = uuid4()
        type_data["cost_element_type_id"] = root_id

        cmd = CreateVersionCommand(
            entity_class=CostElementType,  # type: ignore[type-var]
            root_id=root_id,
            actor_id=actor_id,
            **type_data,
        )
        return await cmd.execute(self.session)

    async def update(
        self,
        cost_element_type_id: UUID,
        type_in: CostElementTypeUpdate,
        actor_id: UUID,
    ) -> CostElementType:
        """Update cost element type using UpdateVersionCommand."""
        update_data = type_in.model_dump(exclude_unset=True)
        
        # Custom command class to handle multi-word entity name
        class CostElementTypeUpdateCommand(UpdateVersionCommand):  # type: ignore[type-var]
            def _root_field_name(self) -> str:
                return "cost_element_type_id"
        
        cmd = CostElementTypeUpdateCommand(
            entity_class=CostElementType,  # type: ignore[type-var]
            root_id=cost_element_type_id,
            actor_id=actor_id,
            **update_data,
        )
        return await cmd.execute(self.session)

    async def soft_delete(
        self, cost_element_type_id: UUID, actor_id: UUID
    ) -> None:
        """Soft delete cost element type using SoftDeleteCommand."""
        class CostElementTypeSoftDeleteCommand(SoftDeleteCommand):  # type: ignore[type-var]
            def _root_field_name(self) -> str:
                return "cost_element_type_id"
        
        cmd = CostElementTypeSoftDeleteCommand(
            entity_class=CostElementType,  # type: ignore[type-var]
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
                func.upper(cast(Any, CostElementType).valid_time).is_(None),
                cast(Any, CostElementType).deleted_at.is_(None),
            )
            .order_by(cast(Any, CostElementType).valid_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self, filters: dict | None = None, skip: int = 0, limit: int = 100
    ) -> list[CostElementType]:
        """Get all cost element types with optional filtering."""
        stmt = (
            select(CostElementType)
            .where(
                func.upper(cast(Any, CostElementType).valid_time).is_(None),
                cast(Any, CostElementType).deleted_at.is_(None),
            )
        )

        if filters:
            if "department_id" in filters:
                stmt = stmt.where(CostElementType.department_id == filters["department_id"])

        stmt = stmt.order_by(CostElementType.valid_time.desc()).offset(skip).limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
