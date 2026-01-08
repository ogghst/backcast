"""DepartmentService implementation.

Provides Department-specific operations on top of generic temporal service.
"""

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.versioning.commands import (
    CreateVersionCommand,
    SoftDeleteCommand,
    UpdateVersionCommand,
)
from app.core.versioning.service import TemporalService
from app.models.domain.department import Department
from app.models.schemas.department import DepartmentCreate, DepartmentUpdate


class DepartmentService(TemporalService[Department]):  # type: ignore[type-var]
    """Service for Department entity operations.

    Extends TemporalService with department-specific methods like get_by_code.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Department, session)

    async def get_department(self, department_id: UUID) -> Department | None:
        """Get department by ID (current version)."""
        return await self.get_by_id(department_id)

    async def get_departments(
        self,
        skip: int = 0,
        limit: int = 100000,
        search: str | None = None,
        filter_string: str | None = None,
        sort_field: str | None = None,
        sort_order: str = "asc",
    ) -> tuple[list[Department], int]:
        """Get departments with server-side search, filtering, and sorting.
        
        Returns:
            Tuple of (list of departments, total count)
        """
        from sqlalchemy import and_, func, or_
        from typing import Any, cast

        from app.core.filtering import FilterParser

        # Base statement
        stmt = select(Department).where(
            func.upper(Department.valid_time).is_(None),
            Department.deleted_at.is_(None),
        )

        # Apply search
        if search:
            search_term = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Department.code.ilike(search_term),
                    Department.name.ilike(search_term),
                )
            )

        # Apply filters
        if filter_string:
            allowed_fields = ["code", "name"]
            parsed_filters = FilterParser.parse_filters(filter_string)
            filter_expressions = FilterParser.build_sqlalchemy_filters(
                Department, parsed_filters, allowed_fields=allowed_fields
            )
            if filter_expressions:
                stmt = stmt.where(and_(*filter_expressions))

        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        # Apply sorting
        if sort_field and hasattr(Department, sort_field):
            column = getattr(Department, sort_field)
            if sort_order.lower() == "desc":
                stmt = stmt.order_by(column.desc())
            else:
                stmt = stmt.order_by(column.asc())
        else:
            stmt = stmt.order_by(Department.name.asc())

        # Apply pagination
        stmt = stmt.offset(skip).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_by_code(self, code: str) -> Department | None:
        """Get department by code (current active version)."""
        stmt = (
            select(Department)
            .where(Department.code == code, Department.deleted_at.is_(None))
            .order_by(Department.valid_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_department(
        self, dept_in: DepartmentCreate, actor_id: UUID
    ) -> Department:
        """Create new department using CreateVersionCommand."""
        dept_data = dept_in.model_dump()

        # Ensure root department_id exists
        root_id = uuid4()
        dept_data["department_id"] = root_id

        cmd = CreateVersionCommand(
            entity_class=Department,  # type: ignore[type-var]
            root_id=root_id,
            actor_id=actor_id,
            **dept_data,
        )
        return await cmd.execute(self.session)

    async def update_department(
        self, department_id: UUID, dept_in: DepartmentUpdate, actor_id: UUID
    ) -> Department:
        """Update department using UpdateVersionCommand."""
        update_data = dept_in.model_dump(exclude_unset=True)
        cmd = UpdateVersionCommand(
            entity_class=Department,  # type: ignore[type-var]
            root_id=department_id,
            actor_id=actor_id,
            **update_data,
        )
        return await cmd.execute(self.session)

    async def delete_department(self, department_id: UUID, actor_id: UUID) -> None:
        """Soft delete department using SoftDeleteCommand."""
        cmd = SoftDeleteCommand(
            entity_class=Department,  # type: ignore[type-var]
            root_id=department_id,
            actor_id=actor_id,
        )
        await cmd.execute(self.session)

    async def get_department_history(self, department_id: UUID) -> list[Department]:
        """Get all versions of a department by root department_id (with creator name)."""
        return await self.get_history(department_id)
