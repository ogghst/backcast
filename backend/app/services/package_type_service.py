"""Package Type Service - versionable entity management."""

from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.filtering import FilterParser
from app.core.temporal_queries import is_current_version
from app.core.versioning.service import TemporalService
from app.models.domain.package_type import PackageType
from app.models.schemas.package_type import (
    PackageTypeCreate,
    PackageTypeUpdate,
)


class PackageTypeService(TemporalService[PackageType]):  # type: ignore[type-var,unused-ignore]
    """Service for Package Type management (versionable, not branchable)."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session.

        Args:
            db: Async database session
        """
        super().__init__(PackageType, db)

    async def create(  # type: ignore[override]
        self, type_in: PackageTypeCreate, actor_id: UUID
    ) -> PackageType:
        """Create new package type."""
        data = type_in.model_dump(exclude_unset=True)
        data.pop("control_date", None)
        return await super().create(
            actor_id=actor_id,
            control_date=type_in.control_date,
            **data,
        )

    async def update(  # type: ignore[override]
        self,
        package_type_id: UUID,
        type_in: PackageTypeUpdate,
        actor_id: UUID,
    ) -> PackageType:
        """Update package type (creates new version)."""
        data = type_in.model_dump(exclude_unset=True)
        return await super().update(
            package_type_id,
            actor_id=actor_id,
            **data,
        )

    async def soft_delete(
        self,
        package_type_id: UUID,
        actor_id: UUID,
        control_date: datetime | None = None,
    ) -> None:
        """Soft delete package type."""
        await super().soft_delete(
            package_type_id, actor_id=actor_id, control_date=control_date
        )

    async def get_by_id(self, package_type_id: UUID) -> PackageType | None:
        """Get current package type by root ID."""
        stmt = (
            select(PackageType)
            .where(
                PackageType.package_type_id == package_type_id,
                is_current_version(PackageType.valid_time, PackageType.deleted_at),
            )
            .order_by(PackageType.valid_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_package_types(
        self,
        skip: int = 0,
        limit: int = 100000,
        search: str | None = None,
        filter_string: str | None = None,
        sort_field: str | None = None,
        sort_order: str = "asc",
    ) -> tuple[list[PackageType], int]:
        """Get package types with server-side features."""
        stmt = select(PackageType).where(
            is_current_version(PackageType.valid_time, PackageType.deleted_at)
        )

        if search:
            search_term = f"%{search}%"
            stmt = stmt.where(
                or_(
                    PackageType.code.ilike(search_term),
                    PackageType.name.ilike(search_term),
                )
            )

        if filter_string:
            allowed_fields = ["code", "name", "color"]
            parsed_filters = FilterParser.parse_filters(filter_string)
            filter_expressions = FilterParser.build_sqlalchemy_filters(
                cast(Any, PackageType),
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
        if sort_field and hasattr(PackageType, sort_field):
            column = getattr(PackageType, sort_field)
            if sort_order.lower() == "desc":
                stmt = stmt.order_by(column.desc())
            else:
                stmt = stmt.order_by(column.asc())
        else:
            stmt = stmt.order_by(PackageType.name.asc())

        stmt = stmt.offset(skip).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def list(self, skip: int = 0, limit: int = 100000) -> list[PackageType]:
        """Legacy list method (backward compatibility)."""
        items, _ = await self.get_package_types(skip=skip, limit=limit)
        return items
