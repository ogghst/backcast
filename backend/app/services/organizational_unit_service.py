"""Organizational Unit Service - branchable entity management.

Extends BranchableService for Organizational Unit operations within
the ANSI-748 model. Replaces the old DepartmentService.
"""

from datetime import datetime
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.branching.service import BranchableService
from app.core.versioning.commands import CreateVersionCommand
from app.core.versioning.enums import BranchMode
from app.models.domain.organizational_unit import OrganizationalUnit
from app.models.schemas.organizational_unit import (
    OrganizationalUnitCreate,
    OrganizationalUnitUpdate,
)


class OrganizationalUnitService(BranchableService[OrganizationalUnit]):  # type: ignore[type-var,unused-ignore]
    """Service for Organizational Unit entity operations.

    Extends BranchableService with unit-specific methods including
    hierarchical queries and code lookup.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(OrganizationalUnit, session)

    async def create_root(
        self,
        root_id: UUID,
        actor_id: UUID,
        control_date: datetime | None = None,
        branch: str = "main",
        **data: Any,
    ) -> OrganizationalUnit:
        """Create the initial version of an Organizational Unit."""
        data["organizational_unit_id"] = root_id

        cmd = CreateVersionCommand(
            entity_class=OrganizationalUnit,
            root_id=root_id,
            actor_id=actor_id,
            control_date=control_date,
            branch=branch,
            **data,
        )
        return await cmd.execute(self.session)

    async def list_organizational_units(
        self,
        skip: int = 0,
        limit: int = 100000,
        search: str | None = None,
        filter_string: str | None = None,
        sort_field: str | None = None,
        sort_order: str = "asc",
        branch: str = "main",
    ) -> tuple[list[OrganizationalUnit], int]:
        """Get organizational units with search, filtering, and sorting.

        Args:
            skip: Records to skip.
            limit: Maximum records to return.
            search: Search term for code and name.
            filter_string: Filter string (e.g., "code:MECH").
            sort_field: Field to sort by.
            sort_order: "asc" or "desc".
            branch: Branch name.

        Returns:
            Tuple of (list of units, total count).
        """
        from app.core.filtering import FilterParser

        stmt = select(OrganizationalUnit).where(
            OrganizationalUnit.branch == branch,
            func.upper(cast(Any, OrganizationalUnit).valid_time).is_(None),
            cast(Any, OrganizationalUnit).deleted_at.is_(None),
        )

        if search:
            search_term = f"%{search}%"
            stmt = stmt.where(
                or_(
                    OrganizationalUnit.code.ilike(search_term),
                    OrganizationalUnit.name.ilike(search_term),
                )
            )

        if filter_string:
            allowed_fields = ["code", "name", "parent_unit_id"]
            parsed_filters = FilterParser.parse_filters(filter_string)
            filter_expressions = FilterParser.build_sqlalchemy_filters(
                cast(Any, OrganizationalUnit),
                parsed_filters,
                allowed_fields=allowed_fields,
            )
            if filter_expressions:
                stmt = stmt.where(and_(*filter_expressions))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        if sort_field and hasattr(OrganizationalUnit, sort_field):
            column = getattr(OrganizationalUnit, sort_field)
            if sort_order.lower() == "desc":
                stmt = stmt.order_by(column.desc())
            else:
                stmt = stmt.order_by(column.asc())
        else:
            stmt = stmt.order_by(OrganizationalUnit.name.asc())

        stmt = stmt.offset(skip).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_children(self, parent_unit_id: UUID) -> list[OrganizationalUnit]:
        """Get direct children of an organizational unit.

        Args:
            parent_unit_id: Parent unit root ID.

        Returns:
            List of child OrganizationalUnit entities.
        """
        stmt = (
            select(OrganizationalUnit)
            .where(
                OrganizationalUnit.parent_unit_id == parent_unit_id,
                func.upper(cast(Any, OrganizationalUnit).valid_time).is_(None),
                cast(Any, OrganizationalUnit).deleted_at.is_(None),
            )
            .order_by(OrganizationalUnit.code)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_code(self, code: str) -> OrganizationalUnit | None:
        """Get organizational unit by code (current active version).

        Args:
            code: Unit code to look up.

        Returns:
            OrganizationalUnit if found, None otherwise.
        """
        stmt = (
            select(OrganizationalUnit)
            .where(
                OrganizationalUnit.code == code,
                func.upper(cast(Any, OrganizationalUnit).valid_time).is_(None),
                cast(Any, OrganizationalUnit).deleted_at.is_(None),
            )
            .order_by(cast(Any, OrganizationalUnit).valid_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _validate_parent_unit_id(
        self, parent_unit_id: UUID | None, exclude_root_id: UUID | None = None
    ) -> None:
        """Validate parent_unit_id: existence check and circular reference prevention."""
        if parent_unit_id is None:
            return

        # Prevent self-reference
        if exclude_root_id and parent_unit_id == exclude_root_id:
            raise ValueError("Organizational unit cannot be its own parent")

        # Verify parent exists as active current version
        parent = await self.get_as_of(entity_id=parent_unit_id)
        if not parent:
            raise ValueError(f"Parent organizational unit {parent_unit_id} not found")

        # Walk parent chain to detect circular references
        visited: set[UUID] = {parent_unit_id}
        if exclude_root_id:
            visited.add(exclude_root_id)

        current = parent.parent_unit_id
        depth = 0
        max_depth = 20
        while current is not None and depth < max_depth:
            if current in visited:
                raise ValueError(
                    "Circular reference detected in parent_unit_id hierarchy"
                )
            visited.add(current)
            ancestor = await self.get_as_of(entity_id=current)
            if not ancestor:
                break
            current = ancestor.parent_unit_id
            depth += 1

    async def create_organizational_unit(
        self, unit_in: OrganizationalUnitCreate, actor_id: UUID
    ) -> OrganizationalUnit:
        """Create new organizational unit.

        Args:
            unit_in: Creation data.
            actor_id: User creating the unit.

        Returns:
            Created OrganizationalUnit entity.
        """
        unit_data = unit_in.model_dump(exclude_unset=True)
        root_id = unit_in.organizational_unit_id or uuid4()
        unit_data["organizational_unit_id"] = root_id

        control_date = getattr(unit_in, "control_date", None)
        unit_data.pop("control_date", None)

        # Validate Manager (User) existence if provided
        if unit_data.get("manager_id"):
            from app.models.domain.user import User

            user_exists = await self.session.execute(
                select(User.id)
                .where(
                    User.user_id == unit_data["manager_id"],
                    func.upper(cast(Any, User).valid_time).is_(None),
                    cast(Any, User).deleted_at.is_(None),
                )
                .limit(1)
            )
            if not user_exists.scalar_one_or_none():
                raise ValueError(f"Manager (User) {unit_data['manager_id']} not found")

        # Validate parent_unit_id hierarchy
        if unit_data.get("parent_unit_id"):
            await self._validate_parent_unit_id(unit_data["parent_unit_id"])

        cmd = CreateVersionCommand(
            entity_class=OrganizationalUnit,
            root_id=root_id,
            actor_id=actor_id,
            control_date=control_date,
            **unit_data,
        )
        return await cmd.execute(self.session)

    async def update_organizational_unit(
        self,
        organizational_unit_id: UUID,
        unit_in: OrganizationalUnitUpdate,
        actor_id: UUID,
    ) -> OrganizationalUnit:
        """Update organizational unit.

        Args:
            organizational_unit_id: Root ID of the unit to update.
            unit_in: Update data.
            actor_id: User performing the update.

        Returns:
            Updated OrganizationalUnit entity.
        """
        update_data = unit_in.model_dump(exclude_unset=True)
        control_date = update_data.pop("control_date", None)
        branch = update_data.pop("branch", None) or "main"

        # Validate parent_unit_id hierarchy if being changed
        if "parent_unit_id" in update_data and update_data["parent_unit_id"] is not None:
            await self._validate_parent_unit_id(
                update_data["parent_unit_id"], exclude_root_id=organizational_unit_id
            )

        from app.core.branching.commands import UpdateCommand

        cmd = UpdateCommand(  # type: ignore[type-var]
            entity_class=OrganizationalUnit,
            root_id=organizational_unit_id,
            actor_id=actor_id,
            branch=branch,
            control_date=control_date,
            updates=update_data,
        )
        return await cmd.execute(self.session)

    async def delete_organizational_unit(
        self, organizational_unit_id: UUID, actor_id: UUID
    ) -> None:
        """Soft delete organizational unit.

        Args:
            organizational_unit_id: Root ID of the unit to delete.
            actor_id: User performing the delete.
        """
        await self.soft_delete(
            root_id=organizational_unit_id,
            actor_id=actor_id,
        )

    async def get_organizational_unit_history(
        self, organizational_unit_id: UUID
    ) -> list[OrganizationalUnit]:
        """Get all versions of an organizational unit.

        Args:
            organizational_unit_id: Root ID.

        Returns:
            List of versions ordered by transaction_time descending.
        """
        return await self.get_history(organizational_unit_id)

    async def get_organizational_unit_as_of(
        self,
        organizational_unit_id: UUID,
        as_of: datetime,
        branch: str = "main",
        branch_mode: BranchMode | None = None,
    ) -> OrganizationalUnit | None:
        """Get organizational unit as it was at specific timestamp.

        Args:
            organizational_unit_id: Root ID.
            as_of: Timestamp for historical query.
            branch: Branch name.
            branch_mode: Branch resolution mode.

        Returns:
            OrganizationalUnit at the specified timestamp, or None.
        """
        return await self.get_as_of(organizational_unit_id, as_of, branch, branch_mode)

    # --- Backward-compatible aliases for gradual migration ---

    async def get_departments(
        self,
        skip: int = 0,
        limit: int = 100000,
        search: str | None = None,
        filter_string: str | None = None,
        sort_field: str | None = None,
        sort_order: str = "asc",
    ) -> tuple[list[OrganizationalUnit], int]:
        """Backward-compatible alias for list_organizational_units()."""
        return await self.list_organizational_units(
            skip=skip,
            limit=limit,
            search=search,
            filter_string=filter_string,
            sort_field=sort_field,
            sort_order=sort_order,
        )
