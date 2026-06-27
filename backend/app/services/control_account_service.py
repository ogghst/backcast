"""Control Account Service - ANSI-748 management control point.

Extends BranchableService for Control Account operations.
Control Accounts are the intersection of WBS Elements and Organizational Units
where budget authority is delegated.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.branching.service import BranchableService
from app.core.versioning.commands import CreateVersionCommand
from app.core.versioning.enums import BranchMode
from app.models.domain.control_account import ControlAccount
from app.models.domain.work_package import WorkPackage


class ControlAccountService(BranchableService[ControlAccount]):  # type: ignore[type-var,unused-ignore]
    """Service for Control Account entity operations.

    Extends BranchableService with control-account-specific methods including
    budget computation through child WorkPackages.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ControlAccount, session)

    async def create_root(
        self,
        root_id: UUID,
        actor_id: UUID,
        control_date: datetime | None = None,
        branch: str = "main",
        **data: Any,
    ) -> ControlAccount:
        """Create the initial version of a Control Account."""
        data["control_account_id"] = root_id

        cmd = CreateVersionCommand(
            entity_class=ControlAccount,
            root_id=root_id,
            actor_id=actor_id,
            control_date=control_date,
            branch=branch,
            **data,
        )
        return await cmd.execute(self.session)

    async def get_control_accounts(
        self,
        wbs_element_id: UUID | None = None,
        organizational_unit_id: UUID | None = None,
        skip: int = 0,
        limit: int = 100,
        branch: str = "main",
        branch_mode: BranchMode = BranchMode.MERGED,
        as_of: datetime | None = None,
    ) -> tuple[list[ControlAccount], int]:
        """Get control accounts with optional WBS/OrgUnit filtering.

        Args:
            wbs_element_id: Optional WBS Element filter.
            organizational_unit_id: Optional Organizational Unit filter.
            skip: Records to skip.
            limit: Maximum records to return.
            branch: Branch name.
            branch_mode: Branch isolation mode.
            as_of: Optional timestamp for time-travel.

        Returns:
            Tuple of (list of control accounts, total count).
        """
        stmt = select(ControlAccount)

        # Apply branch mode filter
        stmt = self._apply_branch_mode_filter(
            stmt, branch=branch, branch_mode=branch_mode, as_of=as_of
        )

        if as_of:
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            stmt = stmt.where(
                func.upper(cast(Any, ControlAccount).valid_time).is_(None),
                cast(Any, ControlAccount).deleted_at.is_(None),
            )

        if wbs_element_id is not None:
            stmt = stmt.where(ControlAccount.wbs_element_id == wbs_element_id)

        if organizational_unit_id is not None:
            stmt = stmt.where(
                ControlAccount.organizational_unit_id == organizational_unit_id
            )

        # Count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        # Sort and paginate
        stmt = stmt.order_by(cast(Any, ControlAccount).valid_time.desc())
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

    async def get_or_create(
        self,
        wbs_element_id: UUID,
        organizational_unit_id: UUID,
        name: str,
        actor_id: UUID,
        branch: str = "main",
        control_date: datetime | None = None,
    ) -> ControlAccount:
        """Get existing Control Account for (WBS, OrgUnit) or create one.

        Each intersection of WBS Element and Organizational Unit should have
        at most one Control Account.

        Args:
            wbs_element_id: WBS Element root ID.
            organizational_unit_id: Organizational Unit root ID.
            name: Name for the control account if created.
            actor_id: User performing the operation.
            branch: Branch name.
            control_date: Optional control date.

        Returns:
            Existing or newly created ControlAccount.
        """
        stmt = (
            select(ControlAccount)
            .where(
                ControlAccount.wbs_element_id == wbs_element_id,
                ControlAccount.organizational_unit_id == organizational_unit_id,
                ControlAccount.branch == branch,
                func.upper(cast(Any, ControlAccount).valid_time).is_(None),
                cast(Any, ControlAccount).deleted_at.is_(None),
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            return existing

        root_id = uuid4()
        return await self.create_root(
            root_id=root_id,
            actor_id=actor_id,
            control_date=control_date,
            branch=branch,
            wbs_element_id=wbs_element_id,
            organizational_unit_id=organizational_unit_id,
            name=name,
        )

    async def compute_budget(
        self,
        control_account_id: UUID,
        branch: str = "main",
    ) -> Decimal:
        """Compute budget for a Control Account.

        Budget = sum of WorkPackage.budget_amount for all WorkPackages
        under this Control Account.

        Args:
            control_account_id: Control Account root ID.
            branch: Branch name.

        Returns:
            Sum of work package budgets.
        """
        stmt = select(
            func.coalesce(func.sum(WorkPackage.budget_amount), Decimal("0"))
        ).where(
            WorkPackage.control_account_id == control_account_id,
            WorkPackage.branch == branch,
            func.upper(cast(Any, WorkPackage).valid_time).is_(None),
            cast(Any, WorkPackage).deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar() or Decimal("0")
