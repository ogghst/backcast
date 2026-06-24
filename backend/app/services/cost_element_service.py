"""Cost Element Service - EOC (Element of Cost) under a Work Package.

Extends TemporalService (NOT BranchableService) for Cost Element operations.
Cost Elements are versionable but NOT branchable -- financial facts are global.
"""

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
from app.core.versioning.enums import BranchMode
from app.core.versioning.service import TemporalService
from app.models.domain.cost_element import CostElement
from app.models.domain.cost_element_type import CostElementType
from app.models.schemas.cost_element import CostElementCreate, CostElementUpdate


class CostElementService(TemporalService[CostElement]):  # type: ignore[type-var,unused-ignore]
    """Service for Cost Element (EOC) entity operations.

    Cost Elements are categorization entities linking a Work Package to a
    Cost Element Type. Budget is held on WorkPackage.budget_amount (the BAC),
    not on CostElement.

    Versionable but NOT branchable (cost data is global facts).
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(CostElement, session)

    async def create_cost_element(
        self,
        element_in: CostElementCreate,
        actor_id: UUID,
    ) -> CostElement:
        """Create new cost element (EOC) under a Work Package.

        Args:
            element_in: Creation data.
            actor_id: User creating the element.

        Returns:
            Created CostElement entity.

        Raises:
            ValueError: If WorkPackage or CostElementType not found.
        """
        element_data = element_in.model_dump(exclude_unset=True)
        control_date = getattr(element_in, "control_date", None)
        element_data.pop("control_date", None)

        root_id = element_in.cost_element_id or uuid4()
        element_data["cost_element_id"] = root_id

        # Validate WorkPackage existence
        from app.models.domain.work_package import WorkPackage

        wp_exists = await self.session.execute(
            select(WorkPackage.id)
            .where(
                WorkPackage.work_package_id == element_in.work_package_id,
                func.upper(cast(Any, WorkPackage).valid_time).is_(None),
                cast(Any, WorkPackage).deleted_at.is_(None),
            )
            .limit(1)
        )
        if not wp_exists.scalar_one_or_none():
            raise ValueError(f"Work Package {element_in.work_package_id} not found")

        # Validate CostElementType existence
        type_exists = await self.session.execute(
            select(CostElementType.id)
            .where(
                CostElementType.cost_element_type_id == element_in.cost_element_type_id,
                func.upper(cast(Any, CostElementType).valid_time).is_(None),
                cast(Any, CostElementType).deleted_at.is_(None),
            )
            .limit(1)
        )
        if not type_exists.scalar_one_or_none():
            raise ValueError(
                f"Cost Element Type {element_in.cost_element_type_id} not found"
            )

        cmd = CreateVersionCommand(  # type: ignore[type-var]
            entity_class=CostElement,
            root_id=root_id,
            actor_id=actor_id,
            control_date=control_date,
            **element_data,
        )
        return await cmd.execute(self.session)

    async def update_cost_element(
        self,
        cost_element_id: UUID,
        element_in: CostElementUpdate,
        actor_id: UUID,
    ) -> CostElement:
        """Update cost element (creates new version).

        Args:
            cost_element_id: Root ID to update.
            element_in: Update data.
            actor_id: User making the update.

        Returns:
            Updated CostElement entity.
        """
        update_data = element_in.model_dump(exclude_unset=True)
        control_date = update_data.pop("control_date", None)

        # Validate CostElementType if changed
        if element_in.cost_element_type_id is not None:
            type_exists = await self.session.execute(
                select(CostElementType.id)
                .where(
                    CostElementType.cost_element_type_id
                    == element_in.cost_element_type_id,
                    func.upper(cast(Any, CostElementType).valid_time).is_(None),
                    cast(Any, CostElementType).deleted_at.is_(None),
                )
                .limit(1)
            )
            if not type_exists.scalar_one_or_none():
                raise ValueError(
                    f"Cost Element Type {element_in.cost_element_type_id} not found"
                )

        class CostElementUpdateCommand(UpdateVersionCommand[CostElement]):  # type: ignore[type-var,unused-ignore]
            def _root_field_name(self) -> str:
                return "cost_element_id"

        cmd = CostElementUpdateCommand(
            entity_class=CostElement,
            root_id=cost_element_id,
            actor_id=actor_id,
            control_date=control_date,
            **update_data,
        )
        return await cmd.execute(self.session)

    async def soft_delete_cost_element(
        self,
        cost_element_id: UUID,
        actor_id: UUID,
        control_date: datetime | None = None,
    ) -> None:
        """Soft delete cost element.

        Args:
            cost_element_id: Root ID to delete.
            actor_id: User performing deletion.
            control_date: Optional control date.
        """

        class CostElementSoftDeleteCommand(SoftDeleteCommand[CostElement]):  # type: ignore[type-var,unused-ignore]
            def _root_field_name(self) -> str:
                return "cost_element_id"

        cmd = CostElementSoftDeleteCommand(
            entity_class=CostElement,
            root_id=cost_element_id,
            actor_id=actor_id,
            control_date=control_date,
        )
        await cmd.execute(self.session)

    async def get_cost_elements(
        self,
        work_package_id: UUID | None = None,
        cost_element_type_id: UUID | None = None,
        skip: int = 0,
        limit: int = 100,
        as_of: datetime | None = None,
    ) -> tuple[list[CostElement], int]:
        """Get cost elements with optional filtering and pagination.

        Args:
            work_package_id: Optional Work Package filter.
            cost_element_type_id: Optional Cost Element Type filter.
            skip: Records to skip.
            limit: Maximum records.
            as_of: Optional timestamp for time-travel.

        Returns:
            Tuple of (list of cost elements, total count).
        """
        stmt = select(CostElement)

        if as_of is not None:
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            stmt = stmt.where(
                func.upper(CostElement.valid_time).is_(None),
                CostElement.deleted_at.is_(None),
            )

        if work_package_id is not None:
            stmt = stmt.where(CostElement.work_package_id == work_package_id)

        if cost_element_type_id is not None:
            stmt = stmt.where(CostElement.cost_element_type_id == cost_element_type_id)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = stmt.order_by(CostElement.valid_time.desc())
        stmt = stmt.offset(skip).limit(limit)

        result = await self.session.execute(stmt)
        entities = list(result.scalars().all())
        # Resolve created_by_name + created_at/updated_at across all versions.
        from app.core.versioning.creator_resolver import (
            populate_creator_names,
            populate_entity_timestamps,
        )

        await populate_creator_names(self.session, entities)
        await populate_entity_timestamps(self.session, entities)
        return entities, total

    async def get_by_id(
        self,
        cost_element_id: UUID,
    ) -> CostElement | None:
        """Get current cost element by root ID.

        Args:
            cost_element_id: Root ID.

        Returns:
            Current CostElement or None.
        """
        stmt = (
            select(CostElement)
            .where(
                CostElement.cost_element_id == cost_element_id,
                func.upper(CostElement.valid_time).is_(None),
                CostElement.deleted_at.is_(None),
            )
            .order_by(CostElement.valid_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_history(self, root_id: UUID) -> list[CostElement]:
        """Get all versions of a cost element with creator name.

        Args:
            root_id: Root cost_element_id.

        Returns:
            All versions ordered by transaction_time descending.
        """
        from app.models.domain.user import User

        UserAlias = cast(Any, User)
        creator_subq = (
            select(UserAlias.user_id, UserAlias.full_name)
            .distinct(UserAlias.user_id)
            .order_by(UserAlias.user_id, UserAlias.transaction_time.desc())
            .subquery("creator_lookup")
        )

        stmt = (
            select(
                CostElement,
                creator_subq.c.full_name.label("created_by_name"),
            )
            .outerjoin(
                creator_subq,
                CostElement.created_by == creator_subq.c.user_id,
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
            entity = row[0]
            entity.created_by_name = row[1]
            history.append(entity)

        # Derive created_at (true creation) + updated_at across all versions.
        from app.core.versioning.creator_resolver import populate_entity_timestamps

        await populate_entity_timestamps(self.session, history)

        return history

    async def get_cost_element_as_of(
        self,
        cost_element_id: UUID,
        as_of: datetime,
        branch: str = "main",
        branch_mode: BranchMode | None = None,
    ) -> CostElement | None:
        """Get cost element as it was at specific timestamp.

        Args:
            cost_element_id: Root ID.
            as_of: Timestamp for historical query.
            branch: Not applicable for non-branchable entities.
            branch_mode: Not applicable for non-branchable entities.

        Returns:
            CostElement at the specified timestamp, or None.
        """
        stmt = select(CostElement).where(
            CostElement.cost_element_id == cost_element_id,
        )
        stmt = self._apply_bitemporal_filter(stmt, as_of)
        result = await self.session.execute(stmt)
        entity = result.scalar_one_or_none()
        if entity is not None:
            from app.core.versioning.creator_resolver import (
                populate_creator_names,
                populate_entity_timestamps,
            )

            await populate_creator_names(self.session, [entity])
            await populate_entity_timestamps(self.session, [entity])
        return entity

    async def get_breadcrumb(self, cost_element_id: UUID) -> dict[str, Any]:
        """Get breadcrumb trail for a Cost Element.

        Hierarchy: Project -> WBSElement -> CostElement (with type info)

        Uses a single JOIN query through: CostElement -> WorkPackage ->
        ControlAccount -> WBSElement -> Project, plus CostElementType.

        Args:
            cost_element_id: Cost Element root ID.

        Returns:
            Dict with breadcrumb hierarchy matching frontend CostElementBreadcrumb.

        Raises:
            ValueError: If Cost Element or any parent not found.
        """
        from app.models.domain.control_account import ControlAccount
        from app.models.domain.project import Project
        from app.models.domain.wbs_element import WBSElement
        from app.models.domain.work_package import WorkPackage

        stmt = (
            select(
                CostElement.id.label("ce_id"),
                CostElement.cost_element_id.label("ce_cost_element_id"),
                CostElementType.code.label("ce_type_code"),
                CostElementType.name.label("ce_type_name"),
                WorkPackage.name.label("wp_name"),
                WorkPackage.code.label("wp_code"),
                WBSElement.id.label("wbs_id"),
                WBSElement.wbs_element_id.label("wbs_wbs_element_id"),
                WBSElement.code.label("wbs_code"),
                WBSElement.name.label("wbs_name"),
                Project.id.label("proj_id"),
                Project.project_id.label("proj_project_id"),
                Project.code.label("proj_code"),
                Project.name.label("proj_name"),
            )
            .join(
                WorkPackage,
                WorkPackage.work_package_id == CostElement.work_package_id,
            )
            .join(
                ControlAccount,
                ControlAccount.control_account_id == WorkPackage.control_account_id,
            )
            .join(
                WBSElement,
                WBSElement.wbs_element_id == ControlAccount.wbs_element_id,
            )
            .join(
                Project,
                Project.project_id == WBSElement.project_id,
            )
            .join(
                CostElementType,
                CostElementType.cost_element_type_id
                == CostElement.cost_element_type_id,
            )
            .where(
                CostElement.cost_element_id == cost_element_id,
                func.upper(cast(Any, CostElement).valid_time).is_(None),
                cast(Any, CostElement).deleted_at.is_(None),
                func.upper(cast(Any, WorkPackage).valid_time).is_(None),
                cast(Any, WorkPackage).deleted_at.is_(None),
                func.upper(cast(Any, ControlAccount).valid_time).is_(None),
                cast(Any, ControlAccount).deleted_at.is_(None),
                func.upper(cast(Any, WBSElement).valid_time).is_(None),
                cast(Any, WBSElement).deleted_at.is_(None),
                func.upper(cast(Any, Project).valid_time).is_(None),
                cast(Any, Project).deleted_at.is_(None),
                func.upper(cast(Any, CostElementType).valid_time).is_(None),
                cast(Any, CostElementType).deleted_at.is_(None),
            )
            .limit(1)
        )

        result = await self.session.execute(stmt)
        row = result.first()

        if not row:
            raise ValueError(f"Cost Element {cost_element_id} not found")

        return {
            "project": {
                "id": row.proj_id,
                "project_id": row.proj_project_id,
                "code": row.proj_code,
                "name": row.proj_name,
            },
            "wbs_element": {
                "id": row.wbs_id,
                "wbs_element_id": row.wbs_wbs_element_id,
                "code": row.wbs_code,
                "name": row.wbs_name,
            },
            "cost_element": {
                "id": row.ce_id,
                "cost_element_id": row.ce_cost_element_id,
                "cost_element_type_name": row.ce_type_name,
                "cost_element_type_code": row.ce_type_code,
                "work_package_name": row.wp_name,
                "work_package_code": row.wp_code,
            },
        }

    async def get_as_of_batch(
        self,
        entity_ids: list[UUID],
        as_of: datetime | None = None,
        branch: str = "main",
        branch_mode: BranchMode | None = None,
    ) -> dict[UUID, CostElement]:
        """Bulk time-travel fetch for multiple cost elements.

        Args:
            entity_ids: List of root IDs.
            as_of: Timestamp for time-travel (None = current).
            branch: Not applicable.
            branch_mode: Not applicable.

        Returns:
            Dictionary mapping cost_element_id to CostElement.
        """
        if not entity_ids:
            return {}

        stmt = (
            select(CostElement)
            .where(CostElement.cost_element_id.in_(entity_ids))
            .where(CostElement.deleted_at.is_(None))
        )

        if as_of is not None:
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            stmt = stmt.where(func.upper(CostElement.valid_time).is_(None))

        rows = await self.session.execute(stmt)
        entities = list(rows.scalars())
        from app.core.versioning.creator_resolver import (
            populate_creator_names,
            populate_entity_timestamps,
        )

        await populate_creator_names(self.session, entities)
        await populate_entity_timestamps(self.session, entities)
        return {e.cost_element_id: e for e in entities}
