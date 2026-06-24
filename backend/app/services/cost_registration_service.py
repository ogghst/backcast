"""Cost Registration Service - versionable cost tracking management.

Cost registrations track actual expenditures against cost elements (EOCs).
Budget validation is now against WorkPackage.budget_amount (not CostElement).
The hierarchy is: CostElement -> WorkPackage -> ControlAccount -> WBSElement -> Project.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.versioning.commands import (
    CreateVersionCommand,
    SoftDeleteCommand,
    UpdateVersionCommand,
)
from app.core.versioning.enums import BranchMode
from app.core.versioning.service import TemporalService
from app.models.domain.control_account import ControlAccount
from app.models.domain.cost_element import CostElement
from app.models.domain.cost_registration import CostRegistration
from app.models.domain.wbs_element import WBSElement
from app.models.domain.work_package import WorkPackage
from app.models.schemas.cost_registration import (
    CostRegistrationCreate,
    CostRegistrationUpdate,
)
from app.models.schemas.project_budget_settings import (
    BudgetExceededError,
    BudgetWarning,
)
from app.services.project_budget_settings_service import (
    ProjectBudgetSettingsService,
)


class BudgetStatus(BaseModel):
    """Budget status for a work package."""

    work_package_id: UUID
    budget: Decimal
    used: Decimal
    remaining: Decimal
    percentage: Decimal


class ProjectBudgetStatus(BaseModel):
    """Budget status for a project (aggregated across all work packages)."""

    project_id: UUID
    project_budget: Decimal
    total_spend: Decimal
    remaining: Decimal
    percentage: Decimal


class WBSElementBudgetStatus(BaseModel):
    """Budget status for a WBS Element (aggregated through Control Accounts and Work Packages)."""

    wbs_element_id: UUID
    budget: Decimal
    total_spend: Decimal
    remaining: Decimal
    percentage: Decimal


class CostRegistrationService(TemporalService[CostRegistration]):  # type: ignore[type-var,unused-ignore]
    """Service for Cost Registration management (versionable, not branchable).

    Cost registrations track actual expenditures against cost elements (EOCs).
    They are versionable (NOT branchable) - costs are global facts.
    """

    def __init__(self, db: AsyncSession):
        """Initialize service with database session.

        Args:
            db: Async database session
        """
        super().__init__(CostRegistration, db)

    async def get_project_budget_status(
        self,
        project_id: UUID,
        branch: str = "main",
        as_of: datetime | None = None,
        branch_mode: BranchMode = BranchMode.MERGED,
    ) -> ProjectBudgetStatus:
        """Get project-level budget status (aggregated across all work packages).

        Calculates total spend across all cost registrations in the project
        and compares against the project's computed budget (sum of all
        work package budgets through ControlAccount -> WBSElement hierarchy).

        Args:
            project_id: The project to get status for
            branch: Branch context for queries (defaults to "main")
            as_of: Optional timestamp for time-travel query on cost registrations
            branch_mode: Branch resolution mode

        Returns:
            ProjectBudgetStatus with project_budget, total_spend, remaining, percentage
        """
        from app.models.domain.project import Project

        # Verify project exists
        project_stmt = select(Project).where(
            Project.project_id == project_id,
            Project.branch == branch,
            func.upper(cast(Any, Project).valid_time).is_(None),
            cast(Any, Project).deleted_at.is_(None),
        )
        project_result = await self.session.execute(project_stmt.limit(1))
        project = project_result.scalar_one_or_none()

        if project is None and branch != "main":
            project_stmt_main = select(Project).where(
                Project.project_id == project_id,
                Project.branch == "main",
                func.upper(cast(Any, Project).valid_time).is_(None),
                cast(Any, Project).deleted_at.is_(None),
            )
            project_result_main = await self.session.execute(project_stmt_main.limit(1))
            project = project_result_main.scalar_one_or_none()

        if project is None:
            raise ValueError(
                f"Project {project_id} not found on branch {branch} or main"
            )

        effective_branch = project.branch

        # Compute project budget: sum of WorkPackage.budget_amount
        # Hierarchy: WBSElement -> ControlAccount -> WorkPackage
        budget_stmt = (
            select(func.coalesce(func.sum(WorkPackage.budget_amount), Decimal("0")))
            .join(
                ControlAccount,
                WorkPackage.control_account_id == ControlAccount.control_account_id,
            )
            .join(
                WBSElement,
                ControlAccount.wbs_element_id == WBSElement.wbs_element_id,
            )
            .where(
                WBSElement.project_id == project_id,
                WBSElement.branch == effective_branch,
                func.upper(cast(Any, WBSElement).valid_time).is_(None),
                cast(Any, WBSElement).deleted_at.is_(None),
                ControlAccount.branch == effective_branch,
                func.upper(cast(Any, ControlAccount).valid_time).is_(None),
                cast(Any, ControlAccount).deleted_at.is_(None),
                WorkPackage.branch == effective_branch,
                func.upper(cast(Any, WorkPackage).valid_time).is_(None),
                cast(Any, WorkPackage).deleted_at.is_(None),
            )
        )
        budget_result = await self.session.execute(budget_stmt)
        project_budget = Decimal(str(budget_result.scalar_one()))

        # Calculate total spend: CostElement -> CostRegistration, filtered by project
        # Hierarchy: WBSElement -> ControlAccount -> WorkPackage -> CostElement -> CostRegistration
        total_spend_stmt = (
            select(func.sum(CostRegistration.amount))
            .join(
                CostElement,
                CostRegistration.cost_element_id == CostElement.cost_element_id,
            )
            .join(
                WorkPackage,
                CostElement.work_package_id == WorkPackage.work_package_id,
            )
            .join(
                ControlAccount,
                WorkPackage.control_account_id == ControlAccount.control_account_id,
            )
            .join(
                WBSElement,
                ControlAccount.wbs_element_id == WBSElement.wbs_element_id,
            )
            .where(
                WBSElement.project_id == project_id,
                WBSElement.branch == effective_branch,
                func.upper(cast(Any, WBSElement).valid_time).is_(None),
                cast(Any, WBSElement).deleted_at.is_(None),
                ControlAccount.branch == effective_branch,
                func.upper(cast(Any, ControlAccount).valid_time).is_(None),
                cast(Any, ControlAccount).deleted_at.is_(None),
                WorkPackage.branch == effective_branch,
                func.upper(cast(Any, WorkPackage).valid_time).is_(None),
                cast(Any, WorkPackage).deleted_at.is_(None),
                func.upper(cast(Any, CostElement).valid_time).is_(None),
                cast(Any, CostElement).deleted_at.is_(None),
            )
        )

        if as_of is not None:
            total_spend_stmt = self._apply_bitemporal_filter(total_spend_stmt, as_of)
        else:
            total_spend_stmt = total_spend_stmt.where(
                func.upper(CostRegistration.valid_time).is_(None)
            ).where(CostRegistration.deleted_at.is_(None))

        result = await self.session.execute(total_spend_stmt)
        total_spend = result.scalar_one() or Decimal("0")
        total_spend = Decimal(str(total_spend))

        remaining = project_budget - total_spend
        percentage = (
            (total_spend / project_budget * Decimal("100"))
            if project_budget > 0
            else Decimal("0")
        )

        return ProjectBudgetStatus(
            project_id=project_id,
            project_budget=project_budget,
            total_spend=total_spend,
            remaining=remaining,
            percentage=percentage,
        )

    async def get_wbs_element_budget_status(
        self,
        wbs_element_id: UUID,
        branch: str = "main",
        as_of: datetime | None = None,
        branch_mode: BranchMode = BranchMode.MERGED,
    ) -> WBSElementBudgetStatus:
        """Get WBS Element-level budget status.

        Uses a recursive CTE to include this WBS Element and all descendants,
        then sums work package budgets and actual cost registrations.

        Args:
            wbs_element_id: The WBS Element to get status for
            branch: Branch context (defaults to "main")
            as_of: Optional timestamp for time-travel query on cost registrations
            branch_mode: Branch resolution mode

        Returns:
            WBSElementBudgetStatus with budget, total_spend, remaining, percentage
        """
        from sqlalchemy import literal_column

        # Recursive CTE: WBSElement + all descendants
        wbs_hierarchy = (
            select(
                WBSElement.wbs_element_id,
                literal_column("0").label("depth"),
            )
            .where(
                WBSElement.wbs_element_id == wbs_element_id,
                WBSElement.branch == branch,
                func.upper(cast(Any, WBSElement).valid_time).is_(None),
                cast(Any, WBSElement).deleted_at.is_(None),
            )
            .cte(name="wbs_hierarchy_cte", recursive=True)
        )

        child_wbs = aliased(WBSElement, name="child_wbs")
        wbs_hierarchy = wbs_hierarchy.union_all(
            select(
                child_wbs.wbs_element_id,
                (wbs_hierarchy.c.depth + 1).label("depth"),
            ).where(
                child_wbs.parent_wbs_element_id == wbs_hierarchy.c.wbs_element_id,
                child_wbs.branch == branch,
                func.upper(cast(Any, child_wbs).valid_time).is_(None),
                cast(Any, child_wbs).deleted_at.is_(None),
            )
        )

        # Sum WorkPackage budgets in the hierarchy (through ControlAccount)
        budget_stmt = (
            select(func.coalesce(func.sum(WorkPackage.budget_amount), Decimal("0")))
            .select_from(wbs_hierarchy)
            .join(
                ControlAccount,
                ControlAccount.wbs_element_id == wbs_hierarchy.c.wbs_element_id,
            )
            .join(
                WorkPackage,
                WorkPackage.control_account_id == ControlAccount.control_account_id,
            )
            .where(
                ControlAccount.branch == branch,
                func.upper(cast(Any, ControlAccount).valid_time).is_(None),
                cast(Any, ControlAccount).deleted_at.is_(None),
                WorkPackage.branch == branch,
                func.upper(cast(Any, WorkPackage).valid_time).is_(None),
                cast(Any, WorkPackage).deleted_at.is_(None),
            )
        )
        budget_result = await self.session.execute(budget_stmt)
        budget = Decimal(str(budget_result.scalar_one()))

        # Sum actual cost registrations in the hierarchy
        spend_stmt = (
            select(func.coalesce(func.sum(CostRegistration.amount), Decimal("0")))
            .select_from(wbs_hierarchy)
            .join(
                ControlAccount,
                ControlAccount.wbs_element_id == wbs_hierarchy.c.wbs_element_id,
            )
            .join(
                WorkPackage,
                WorkPackage.control_account_id == ControlAccount.control_account_id,
            )
            .join(
                CostElement,
                CostElement.work_package_id == WorkPackage.work_package_id,
            )
            .join(
                CostRegistration,
                CostRegistration.cost_element_id == CostElement.cost_element_id,
            )
            .where(
                ControlAccount.branch == branch,
                func.upper(cast(Any, ControlAccount).valid_time).is_(None),
                cast(Any, ControlAccount).deleted_at.is_(None),
                WorkPackage.branch == branch,
                func.upper(cast(Any, WorkPackage).valid_time).is_(None),
                cast(Any, WorkPackage).deleted_at.is_(None),
                func.upper(cast(Any, CostElement).valid_time).is_(None),
                cast(Any, CostElement).deleted_at.is_(None),
            )
        )

        if as_of is not None:
            spend_stmt = self._apply_bitemporal_filter(spend_stmt, as_of)
        else:
            spend_stmt = spend_stmt.where(
                func.upper(CostRegistration.valid_time).is_(None)
            ).where(CostRegistration.deleted_at.is_(None))
        spend_result = await self.session.execute(spend_stmt)
        total_spend = Decimal(str(spend_result.scalar_one()))

        remaining = budget - total_spend
        percentage = (
            (total_spend / budget * Decimal("100")) if budget > 0 else Decimal("0")
        )

        return WBSElementBudgetStatus(
            wbs_element_id=wbs_element_id,
            budget=budget,
            total_spend=total_spend,
            remaining=remaining,
            percentage=percentage,
        )

    async def get_wbe_budget_status(
        self,
        wbe_id: UUID,
        branch: str = "main",
        as_of: datetime | None = None,
        branch_mode: BranchMode = BranchMode.MERGED,
    ) -> WBSElementBudgetStatus:
        """Backward-compatible alias for get_wbs_element_budget_status()."""
        return await self.get_wbs_element_budget_status(
            wbs_element_id=wbe_id,
            branch=branch,
            as_of=as_of,
            branch_mode=branch_mode,
        )

    async def validate_budget_status(
        self,
        work_package_id: UUID,
        project_id: UUID,
        user_id: UUID,
        branch: str = "main",
    ) -> BudgetWarning | None:
        """Validate budget status and return warning if threshold exceeded.

        Checks if the PROJECT's total budget usage exceeds the project's
        warning threshold.

        Args:
            work_package_id: The work package being charged (for context)
            project_id: The project context for validation
            user_id: The user making the registration (for admin override check)
            branch: Branch to check budget against (defaults to "main")

        Returns:
            BudgetWarning if project-level threshold exceeded, None otherwise
        """
        settings_service = ProjectBudgetSettingsService(self.session)
        threshold = await settings_service.get_warning_threshold(project_id)

        project_budget_status = await self.get_project_budget_status(
            project_id=project_id, branch=branch
        )

        if project_budget_status.percentage < threshold:
            return None

        return BudgetWarning(
            exceeds_threshold=True,
            threshold_percent=threshold,
            current_percent=project_budget_status.percentage,
            message=(
                f"Project budget usage at {project_budget_status.percentage:.1f}% "
                f"exceeds warning threshold of {threshold:.1f}% "
                f"(€{project_budget_status.total_spend:,.2f} of "
                f"€{project_budget_status.project_budget:,.2f})"
            ),
        )

    async def validate_work_package_budget(
        self,
        work_package_id: UUID,
        new_amount: Decimal,
        project_id: UUID,
        is_update: bool = False,
        old_amount: Decimal | None = None,
        actor_id: UUID | None = None,
        branch: str = "main",
    ) -> BudgetExceededError | None:
        """Validate that a cost registration won't exceed the work package budget.

        Only enforces when project budget settings have enforce_budget=True.

        Args:
            work_package_id: The work package being charged
            new_amount: Amount of the new/updated registration
            project_id: Project context for checking enforcement settings
            is_update: True if this is an update (old_amount will be subtracted)
            old_amount: Previous amount (required when is_update=True)
            actor_id: User performing the action (for admin override, not yet implemented)
            branch: Branch to resolve work package budget from

        Returns:
            BudgetExceededError if budget would be exceeded, None if allowed
        """
        settings_service = ProjectBudgetSettingsService(self.session)

        if not await settings_service.is_budget_enforced(project_id):
            return None

        # Get work package budget
        wp_stmt = select(WorkPackage.budget_amount).where(
            WorkPackage.work_package_id == work_package_id,
            func.upper(cast(Any, WorkPackage).valid_time).is_(None),
            cast(Any, WorkPackage).deleted_at.is_(None),
        )
        wp_result = await self.session.execute(
            wp_stmt.where(WorkPackage.branch == branch).limit(1)
        )
        budget_amount = wp_result.scalar_one_or_none()

        if budget_amount is None and branch != "main":
            wp_result_main = await self.session.execute(
                wp_stmt.where(WorkPackage.branch == "main").limit(1)
            )
            budget_amount = wp_result_main.scalar_one_or_none()

        if budget_amount is None or budget_amount == Decimal("0"):
            return None

        # Get current total spend for this work package (sum of CR through CostElements)
        current_spend = Decimal(
            str(await self.get_total_for_work_package(work_package_id))
        )

        effective_spend = current_spend
        if is_update and old_amount is not None:
            effective_spend -= old_amount

        projected = effective_spend + new_amount

        if projected > budget_amount:
            over_by = projected - budget_amount
            return BudgetExceededError(
                cost_element_id=work_package_id,
                budget=budget_amount,
                used=current_spend,
                projected=projected,
                over_by=over_by,
                message=(
                    f"Cost registration would exceed work package budget: "
                    f"€{projected:,.2f} > €{budget_amount:,.2f} "
                    f"(over by €{over_by:,.2f})"
                ),
            )

        return None

    async def validate_cost_element_budget(
        self,
        cost_element_id: UUID,
        new_amount: Decimal,
        project_id: UUID,
        is_update: bool = False,
        old_amount: Decimal | None = None,
        actor_id: UUID | None = None,
        branch: str = "main",
    ) -> BudgetExceededError | None:
        """Backward-compatible alias that resolves CE to WP for budget validation."""
        # Resolve CostElement -> WorkPackage
        ce_stmt = select(CostElement.work_package_id).where(
            CostElement.cost_element_id == cost_element_id,
            func.upper(cast(Any, CostElement).valid_time).is_(None),
            cast(Any, CostElement).deleted_at.is_(None),
        )
        ce_result = await self.session.execute(ce_stmt.limit(1))
        wp_id = ce_result.scalar_one_or_none()

        if wp_id is None:
            return None

        return await self.validate_work_package_budget(
            work_package_id=wp_id,
            new_amount=new_amount,
            project_id=project_id,
            is_update=is_update,
            old_amount=old_amount,
            actor_id=actor_id,
            branch=branch,
        )

    async def create_cost_registration(
        self,
        registration_in: CostRegistrationCreate,
        actor_id: UUID,
        branch: str = "main",
        control_date: datetime | None = None,
    ) -> CostRegistration:
        """Create new cost registration using CreateVersionCommand.

        Args:
            registration_in: The cost registration data
            actor_id: The user creating the registration
            control_date: Optional control date for valid_time (defaults to now).
            branch: Branch to check budget against (defaults to "main").
        """
        if control_date is None:
            control_date = getattr(registration_in, "control_date", None)

        registration_data = registration_in.model_dump(
            exclude_unset=True,
            exclude={"control_date"},
        )

        root_id = registration_in.cost_registration_id or uuid4()
        registration_data["cost_registration_id"] = root_id

        if (
            "registration_date" not in registration_data
            or registration_data["registration_date"] is None
        ):
            registration_data["registration_date"] = datetime.now(tz=UTC)

        actual_control_date = control_date

        # Validate Cost Element existence
        ce_exists = await self.session.execute(
            select(CostElement.id)
            .where(
                CostElement.cost_element_id == registration_in.cost_element_id,
                func.upper(cast(Any, CostElement).valid_time).is_(None),
                cast(Any, CostElement).deleted_at.is_(None),
            )
            .limit(1)
        )
        if not ce_exists.scalar_one_or_none():
            raise ValueError(
                f"Cost Element {registration_in.cost_element_id} not found"
            )

        # Get CostElement to find its WorkPackage
        ce_stmt = select(CostElement).where(
            CostElement.cost_element_id == registration_in.cost_element_id,
            func.upper(cast(Any, CostElement).valid_time).is_(None),
            cast(Any, CostElement).deleted_at.is_(None),
        )
        ce_result = await self.session.execute(ce_stmt.limit(1))
        cost_element = ce_result.scalar_one_or_none()

        if cost_element is None:
            raise ValueError(
                f"Cost Element {registration_in.cost_element_id} not found"
            )

        # Get WorkPackage for budget validation and project resolution
        wp_stmt = select(WorkPackage).where(
            WorkPackage.work_package_id == cost_element.work_package_id,
            WorkPackage.branch == branch,
            func.upper(cast(Any, WorkPackage).valid_time).is_(None),
            cast(Any, WorkPackage).deleted_at.is_(None),
        )
        wp_result = await self.session.execute(wp_stmt.limit(1))
        work_package = wp_result.scalar_one_or_none()

        if work_package is None and branch != "main":
            wp_stmt_main = select(WorkPackage).where(
                WorkPackage.work_package_id == cost_element.work_package_id,
                WorkPackage.branch == "main",
                func.upper(cast(Any, WorkPackage).valid_time).is_(None),
                cast(Any, WorkPackage).deleted_at.is_(None),
            )
            wp_result_main = await self.session.execute(wp_stmt_main.limit(1))
            work_package = wp_result_main.scalar_one_or_none()

        if work_package is None:
            raise ValueError(f"Work Package {cost_element.work_package_id} not found")

        # Resolve project_id through ControlAccount -> WBSElement
        project_id = await self._resolve_project_id(
            work_package.control_account_id, branch
        )

        if project_id:
            budget_error = await self.validate_work_package_budget(
                work_package_id=work_package.work_package_id,
                new_amount=registration_in.amount,
                project_id=project_id,
                actor_id=actor_id,
                branch=branch,
            )
            if budget_error:
                raise ValueError(budget_error.message)

        cmd = CreateVersionCommand(
            entity_class=CostRegistration,  # type: ignore[type-var,unused-ignore]
            root_id=root_id,
            actor_id=actor_id,
            control_date=actual_control_date,
            **registration_data,
        )
        return await cmd.execute(self.session)

    async def _resolve_project_id(
        self, control_account_id: UUID, branch: str = "main"
    ) -> UUID | None:
        """Resolve project_id from control_account_id through WBSElement.

        Args:
            control_account_id: Control Account root ID
            branch: Branch name

        Returns:
            Project ID if found, None otherwise
        """
        stmt = (
            select(WBSElement.project_id)
            .join(
                ControlAccount,
                ControlAccount.wbs_element_id == WBSElement.wbs_element_id,
            )
            .where(
                ControlAccount.control_account_id == control_account_id,
                ControlAccount.branch == branch,
                func.upper(cast(Any, ControlAccount).valid_time).is_(None),
                cast(Any, ControlAccount).deleted_at.is_(None),
                WBSElement.branch == branch,
                func.upper(cast(Any, WBSElement).valid_time).is_(None),
                cast(Any, WBSElement).deleted_at.is_(None),
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_cost_registration(
        self,
        cost_registration_id: UUID,
        registration_in: CostRegistrationUpdate,
        actor_id: UUID,
        control_date: datetime | None = None,
    ) -> CostRegistration:
        """Update cost registration using UpdateVersionCommand.

        Args:
            cost_registration_id: The cost registration to update
            registration_in: The update data
            actor_id: The user making the update
            control_date: Optional control date for valid_time (defaults to now)
        """
        if control_date is None:
            control_date = getattr(registration_in, "control_date", None)

        update_data = registration_in.model_dump(
            exclude_unset=True,
            exclude={"control_date"},
        )

        if registration_in.amount is not None:
            current = await self.get_by_id(cost_registration_id)
            if current is not None:
                ce_result = await self.session.execute(
                    select(CostElement)
                    .where(
                        CostElement.cost_element_id == current.cost_element_id,
                        func.upper(cast(Any, CostElement).valid_time).is_(None),
                        cast(Any, CostElement).deleted_at.is_(None),
                    )
                    .limit(1)
                )
                cost_element = ce_result.scalar_one_or_none()
                if cost_element:
                    wp_result = await self.session.execute(
                        select(WorkPackage)
                        .where(
                            WorkPackage.work_package_id == cost_element.work_package_id,
                            func.upper(cast(Any, WorkPackage).valid_time).is_(None),
                            cast(Any, WorkPackage).deleted_at.is_(None),
                        )
                        .limit(1)
                    )
                    work_package = wp_result.scalar_one_or_none()
                    if work_package:
                        project_id = await self._resolve_project_id(
                            work_package.control_account_id
                        )
                        if project_id:
                            budget_error = await self.validate_work_package_budget(
                                work_package_id=work_package.work_package_id,
                                new_amount=registration_in.amount,
                                project_id=project_id,
                                is_update=True,
                                old_amount=current.amount,
                                actor_id=actor_id,
                            )
                            if budget_error:
                                raise ValueError(budget_error.message)

        class CostRegistrationUpdateCommand(UpdateVersionCommand[CostRegistration]):  # type: ignore[type-var,unused-ignore]
            def _root_field_name(self) -> str:
                return "cost_registration_id"

        cmd = CostRegistrationUpdateCommand(
            entity_class=CostRegistration,  # type: ignore[type-var,unused-ignore]
            root_id=cost_registration_id,
            actor_id=actor_id,
            control_date=control_date,
            **update_data,
        )
        return await cmd.execute(self.session)

    async def soft_delete(
        self,
        cost_registration_id: UUID,
        actor_id: UUID,
        control_date: datetime | None = None,
    ) -> None:
        """Soft delete cost registration using SoftDeleteCommand."""

        class CostRegistrationSoftDeleteCommand(SoftDeleteCommand[CostRegistration]):  # type: ignore[type-var,unused-ignore]
            def _root_field_name(self) -> str:
                return "cost_registration_id"

        cmd = CostRegistrationSoftDeleteCommand(
            entity_class=CostRegistration,  # type: ignore[type-var,unused-ignore]
            root_id=cost_registration_id,
            actor_id=actor_id,
            control_date=control_date,
        )
        await cmd.execute(self.session)

    async def get_by_id(self, cost_registration_id: UUID) -> CostRegistration | None:
        """Get current cost registration by root ID with creator name."""
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
                CostRegistration,
                creator_subq.c.full_name.label("created_by_name"),
            )
            .outerjoin(
                creator_subq,
                CostRegistration.created_by == creator_subq.c.user_id,
            )
            .where(
                CostRegistration.cost_registration_id == cost_registration_id,
                func.upper(CostRegistration.valid_time).is_(None),
                CostRegistration.deleted_at.is_(None),
            )
            .order_by(CostRegistration.valid_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        row = result.first()
        if row is None:
            return None
        entity = row[0]
        entity.created_by_name = row[1]
        return entity

    async def get_cost_registrations(
        self,
        filters: dict[str, Any] | None = None,
        skip: int = 0,
        limit: int = 100,
        as_of: datetime | None = None,
        wbs_element_id: UUID | None = None,
        project_id: UUID | None = None,
        work_package_id: UUID | None = None,
    ) -> tuple[list[CostRegistration], int, dict[UUID, tuple[str, str]]]:
        """Get cost registrations with filtering, pagination, and time-travel support.

        Args:
            filters: Optional filters dict (e.g., {"cost_element_id": UUID})
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
            as_of: Optional timestamp for time-travel query (Valid Time Travel semantics)
            wbs_element_id: Optional WBS Element root ID to filter by
            project_id: Optional Project root ID to filter by
            work_package_id: Optional Work Package root ID to filter by

        Returns:
            Tuple of (list of cost registrations, total count, work package name/type map)
        """
        stmt = select(CostRegistration).where(
            CostRegistration.cost_element_id.isnot(None)
        )

        if as_of is not None:
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            stmt = stmt.where(func.upper(CostRegistration.valid_time).is_(None))
            stmt = stmt.where(CostRegistration.deleted_at.is_(None))

        if filters:
            if "cost_element_id" in filters:
                stmt = stmt.where(
                    CostRegistration.cost_element_id == filters["cost_element_id"]
                )

        # Filter by WBS Element (through CostElement -> WorkPackage -> ControlAccount)
        if wbs_element_id is not None:
            ce_subq = (
                select(CostElement.cost_element_id)
                .join(
                    WorkPackage,
                    CostElement.work_package_id == WorkPackage.work_package_id,
                )
                .join(
                    ControlAccount,
                    WorkPackage.control_account_id == ControlAccount.control_account_id,
                )
                .where(
                    ControlAccount.wbs_element_id == wbs_element_id,
                    func.upper(cast(Any, CostElement).valid_time).is_(None),
                    cast(Any, CostElement).deleted_at.is_(None),
                )
                .correlate(CostRegistration)
            )
            stmt = stmt.where(CostRegistration.cost_element_id.in_(ce_subq))

        # Filter by Project (through CostElement -> WorkPackage -> ControlAccount -> WBSElement)
        if project_id is not None:
            ce_subq = (
                select(CostElement.cost_element_id)
                .join(
                    WorkPackage,
                    CostElement.work_package_id == WorkPackage.work_package_id,
                )
                .join(
                    ControlAccount,
                    WorkPackage.control_account_id == ControlAccount.control_account_id,
                )
                .join(
                    WBSElement,
                    ControlAccount.wbs_element_id == WBSElement.wbs_element_id,
                )
                .where(
                    WBSElement.project_id == project_id,
                    func.upper(cast(Any, CostElement).valid_time).is_(None),
                    cast(Any, CostElement).deleted_at.is_(None),
                    func.upper(cast(Any, WBSElement).valid_time).is_(None),
                    cast(Any, WBSElement).deleted_at.is_(None),
                )
                .correlate(CostRegistration)
            )
            stmt = stmt.where(CostRegistration.cost_element_id.in_(ce_subq))

        # Filter by work_package_id (through CostElement)
        if work_package_id is not None:
            ce_subq = (
                select(CostElement.cost_element_id)
                .where(
                    CostElement.work_package_id == work_package_id,
                    func.upper(cast(Any, CostElement).valid_time).is_(None),
                    cast(Any, CostElement).deleted_at.is_(None),
                )
                .correlate(CostRegistration)
            )
            stmt = stmt.where(CostRegistration.cost_element_id.in_(ce_subq))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = stmt.order_by(CostRegistration.registration_date.desc())
        stmt = stmt.offset(skip).limit(limit)

        # Build a separate fetch statement with creator-name outerjoin so the
        # count above is unaffected and created_by_name is populated per row.
        from app.models.domain.user import User

        UserAlias = cast(Any, User)
        creator_subq = (
            select(UserAlias.user_id, UserAlias.full_name)
            .distinct(UserAlias.user_id)
            .order_by(UserAlias.user_id, UserAlias.transaction_time.desc())
            .subquery("creator_lookup")
        )
        fetch_stmt = stmt.with_only_columns(
            CostRegistration,
            creator_subq.c.full_name.label("created_by_name"),
        ).outerjoin(
            creator_subq,
            CostRegistration.created_by == creator_subq.c.user_id,
        )

        result = await self.session.execute(fetch_stmt)
        items: list[CostRegistration] = []
        for row in result.all():
            entity = row[0]
            entity.created_by_name = row[1]
            items.append(entity)

        # Build work package name map for denormalized response
        wp_ids: set[UUID] = set()
        for item in items:
            if item.cost_element_id is not None:
                wp_ids.add(item.cost_element_id)
        wp_map: dict[UUID, tuple[str, str]] = {}
        # Note: The wp_map is a placeholder since we no longer join directly to WP from CR

        return items, total, wp_map

    async def get_work_package_info(
        self, work_package_id: UUID | None
    ) -> tuple[str | None, str | None]:
        """Get work package name and type code for denormalized response."""
        if work_package_id is None:
            return None, None

        stmt = select(
            WorkPackage.name,
        ).where(
            WorkPackage.work_package_id == work_package_id,
            func.upper(cast(Any, WorkPackage).valid_time).is_(None),
            cast(Any, WorkPackage).deleted_at.is_(None),
        )
        result = await self.session.execute(stmt.limit(1))
        row = result.first()
        if row:
            return row.name, ""
        return None, None

    async def get_total_for_cost_element(
        self, cost_element_id: UUID, as_of: datetime | None = None
    ) -> Any:
        """Calculate total costs for a cost element (time-travel aware).

        Args:
            cost_element_id: The cost element to sum costs for
            as_of: Optional timestamp for historical query (time-travel)

        Returns:
            Sum of all cost registrations for the cost element
        """
        stmt = select(func.sum(CostRegistration.amount)).where(
            CostRegistration.cost_element_id == cost_element_id,
        )

        if as_of is not None:
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            stmt = stmt.where(func.upper(CostRegistration.valid_time).is_(None))
            stmt = stmt.where(CostRegistration.deleted_at.is_(None))

        result = await self.session.execute(stmt)
        return result.scalar_one() or 0

    async def get_total_for_work_package(
        self, work_package_id: UUID, as_of: datetime | None = None
    ) -> Any:
        """Calculate total costs for a work package (sum through all CostElements).

        Args:
            work_package_id: The work package to sum costs for
            as_of: Optional timestamp for historical query (time-travel)

        Returns:
            Sum of all cost registrations for the work package's cost elements
        """
        stmt = select(func.sum(CostRegistration.amount)).where(
            CostRegistration.cost_element_id.in_(
                select(CostElement.cost_element_id).where(
                    CostElement.work_package_id == work_package_id,
                    func.upper(cast(Any, CostElement).valid_time).is_(None),
                    cast(Any, CostElement).deleted_at.is_(None),
                )
            ),
        )

        if as_of is not None:
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            stmt = stmt.where(func.upper(CostRegistration.valid_time).is_(None))
            stmt = stmt.where(CostRegistration.deleted_at.is_(None))

        result = await self.session.execute(stmt)
        return result.scalar_one() or 0

    async def get_cost_registration_as_of(
        self,
        cost_registration_id: UUID,
        as_of: datetime,
        branch: str = "main",
        branch_mode: BranchMode | None = None,
    ) -> CostRegistration | None:
        """Get cost registration as it was at specific timestamp.

        Args:
            cost_registration_id: The unique identifier of the cost registration
            as_of: Timestamp to query (historical state based on valid_time)
            branch: Branch name (not applicable for non-branchable entities)
            branch_mode: Resolution mode (not applicable, kept for interface consistency)

        Returns:
            CostRegistration if found at the specified timestamp, None otherwise
        """
        stmt = select(CostRegistration).where(
            CostRegistration.cost_registration_id == cost_registration_id,
        )
        stmt = self._apply_bitemporal_filter(stmt, as_of)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_budget_status(
        self, work_package_id: UUID, as_of: datetime | None = None, branch: str = "main"
    ) -> BudgetStatus:
        """Get budget status for a work package with time-travel support.

        Args:
            work_package_id: The work package to get status for
            as_of: Optional timestamp for time-travel query (historical view)
            branch: Branch context to resolve Work Package budget (defaults to "main")

        Returns:
            BudgetStatus with budget, used, remaining, percentage
        """
        stmt = select(WorkPackage).where(
            WorkPackage.work_package_id == work_package_id,
            WorkPackage.branch == branch,
            func.upper(cast(Any, WorkPackage).valid_time).is_(None),
            cast(Any, WorkPackage).deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        work_package = result.scalar_one_or_none()

        if work_package is None and branch != "main":
            stmt_main = select(WorkPackage).where(
                WorkPackage.work_package_id == work_package_id,
                WorkPackage.branch == "main",
                func.upper(cast(Any, WorkPackage).valid_time).is_(None),
                cast(Any, WorkPackage).deleted_at.is_(None),
            )
            result_main = await self.session.execute(stmt_main)
            work_package = result_main.scalar_one_or_none()

        if work_package is None:
            raise ValueError(
                f"Work package {work_package_id} not found on branch {branch} or main"
            )

        budget = work_package.budget_amount

        used = await self.get_total_for_work_package(work_package_id, as_of=as_of)
        used = Decimal(str(used)) if used else Decimal("0")

        remaining = budget - used
        percentage = (used / budget * Decimal("100")) if budget > 0 else Decimal("0")

        return BudgetStatus(
            work_package_id=work_package_id,
            budget=budget,
            used=used,
            remaining=remaining,
            percentage=percentage,
        )

    async def get_costs_by_period(
        self,
        cost_element_id: UUID,
        period: str,
        start_date: datetime,
        end_date: datetime | None = None,
        as_of: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Get cost aggregations by time period.

        Args:
            cost_element_id: The cost element to aggregate costs for
            period: Period type ("daily", "weekly", "monthly")
            start_date: Start date for aggregation
            end_date: End date for aggregation (defaults to now)
            as_of: Optional timestamp for time-travel query

        Returns:
            List of dicts with period_start and total_amount
        """
        if end_date is None:
            end_date = datetime.now(tz=UTC)

        period_mapping = {
            "daily": "day",
            "weekly": "week",
            "monthly": "month",
        }
        pg_period = period_mapping.get(period, period)

        stmt = select(
            func.date_trunc(pg_period, CostRegistration.registration_date).label(
                "period_start"
            ),
            func.sum(CostRegistration.amount).label("total_amount"),
        ).where(
            CostRegistration.cost_element_id == cost_element_id,
            CostRegistration.registration_date >= start_date,
            CostRegistration.registration_date <= end_date,
        )

        if as_of is not None:
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            stmt = stmt.where(func.upper(CostRegistration.valid_time).is_(None))
            stmt = stmt.where(CostRegistration.deleted_at.is_(None))

        stmt = stmt.group_by("period_start").order_by("period_start")

        result = await self.session.execute(stmt)
        return [
            {
                "period_start": row.period_start.isoformat(),
                "total_amount": float(row.total_amount),
            }
            for row in result.all()
        ]

    async def get_cumulative_costs(
        self,
        cost_element_id: UUID,
        start_date: datetime,
        end_date: datetime | None = None,
        as_of: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Get cumulative costs over time.

        Args:
            cost_element_id: The cost element to get cumulative costs for
            start_date: Start date for calculation
            end_date: End date for calculation (defaults to now)
            as_of: Optional timestamp for time-travel query

        Returns:
            List of dicts with registration_date and cumulative_amount
        """
        if end_date is None:
            end_date = datetime.now(tz=UTC)

        stmt = select(
            CostRegistration.registration_date,
            CostRegistration.amount,
        ).where(
            CostRegistration.cost_element_id == cost_element_id,
            CostRegistration.registration_date >= start_date,
            CostRegistration.registration_date <= end_date,
        )

        if as_of is not None:
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            stmt = stmt.where(func.upper(CostRegistration.valid_time).is_(None))
            stmt = stmt.where(CostRegistration.deleted_at.is_(None))

        stmt = stmt.order_by(CostRegistration.registration_date)

        result = await self.session.execute(stmt)
        rows = result.all()

        cumulative_amount = Decimal("0")
        cumulative_costs = []
        for row in rows:
            cumulative_amount += row.amount
            cumulative_costs.append(
                {
                    "registration_date": row.registration_date.isoformat(),
                    "amount": float(row.amount),
                    "cumulative_amount": float(cumulative_amount),
                }
            )

        return cumulative_costs

    async def get_cumulative_costs_batch(
        self,
        cost_element_ids: list[UUID],
        start_date: datetime,
        end_date: datetime | None = None,
        as_of: datetime | None = None,
    ) -> dict[UUID, list[dict[str, Any]]]:
        """Get cumulative costs over time for multiple cost elements.

        Args:
            cost_element_ids: List of cost element UUIDs to query
            start_date: Start date for calculation
            end_date: End date for calculation (defaults to now)
            as_of: Optional timestamp for time-travel query

        Returns:
            Dictionary mapping each cost_element_id to its cumulative costs list.
        """
        if not cost_element_ids:
            return {}

        if end_date is None:
            end_date = datetime.now(tz=UTC)

        stmt = select(
            CostRegistration.cost_element_id,
            CostRegistration.registration_date,
            CostRegistration.amount,
        ).where(
            CostRegistration.cost_element_id.in_(cost_element_ids),
            CostRegistration.registration_date >= start_date,
            CostRegistration.registration_date <= end_date,
        )

        if as_of is not None:
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            stmt = stmt.where(func.upper(CostRegistration.valid_time).is_(None))
            stmt = stmt.where(CostRegistration.deleted_at.is_(None))

        stmt = stmt.order_by(
            CostRegistration.cost_element_id,
            CostRegistration.registration_date,
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        grouped: dict[UUID, list[Any]] = {}
        for row in rows:
            grouped.setdefault(row.cost_element_id, []).append(row)

        batch_result: dict[UUID, list[dict[str, Any]]] = {}
        for ce_id in cost_element_ids:
            ce_rows = grouped.get(ce_id, [])
            cumulative_amount = Decimal("0")
            costs: list[dict[str, Any]] = []
            for row in ce_rows:
                cumulative_amount += row.amount
                costs.append(
                    {
                        "registration_date": row.registration_date.isoformat(),
                        "amount": float(row.amount),
                        "cumulative_amount": float(cumulative_amount),
                    }
                )
            batch_result[ce_id] = costs

        return batch_result

    async def _get_costs_by_period_for_ces(
        self,
        ce_ids: list[UUID],
        period: str,
        start_date: datetime,
        end_date: datetime | None = None,
        as_of: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Batch version of get_costs_by_period for multiple cost elements."""
        if not ce_ids:
            return []

        if end_date is None:
            end_date = datetime.now(tz=UTC)

        period_mapping = {"daily": "day", "weekly": "week", "monthly": "month"}
        pg_period = period_mapping.get(period, period)

        stmt = select(
            func.date_trunc(pg_period, CostRegistration.registration_date).label(
                "period_start"
            ),
            func.sum(CostRegistration.amount).label("total_amount"),
        ).where(
            CostRegistration.cost_element_id.in_(ce_ids),
            CostRegistration.registration_date >= start_date,
            CostRegistration.registration_date <= end_date,
        )

        if as_of is not None:
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            stmt = stmt.where(func.upper(CostRegistration.valid_time).is_(None))
            stmt = stmt.where(CostRegistration.deleted_at.is_(None))

        stmt = stmt.group_by("period_start").order_by("period_start")

        result = await self.session.execute(stmt)
        return [
            {
                "period_start": row.period_start.isoformat(),
                "total_amount": float(row.total_amount),
            }
            for row in result.all()
        ]

    async def _resolve_cost_element_ids(
        self, entity_type: str, entity_id: UUID
    ) -> list[UUID]:
        """Resolve WBS element or project ID to child cost element root IDs.

        Args:
            entity_type: "wbs_element" or "project"
            entity_id: Root ID of the WBS element or project

        Returns:
            List of cost_element_id root UUIDs (current, non-deleted versions only).
        """
        if entity_type == "wbs_element":
            stmt = (
                select(CostElement.cost_element_id)
                .join(
                    WorkPackage,
                    CostElement.work_package_id == WorkPackage.work_package_id,
                )
                .join(
                    ControlAccount,
                    WorkPackage.control_account_id == ControlAccount.control_account_id,
                )
                .where(
                    ControlAccount.wbs_element_id == entity_id,
                    func.upper(cast(Any, CostElement).valid_time).is_(None),
                    cast(Any, CostElement).deleted_at.is_(None),
                )
            )
        elif entity_type == "project":
            stmt = (
                select(CostElement.cost_element_id)
                .join(
                    WorkPackage,
                    CostElement.work_package_id == WorkPackage.work_package_id,
                )
                .join(
                    ControlAccount,
                    WorkPackage.control_account_id == ControlAccount.control_account_id,
                )
                .join(
                    WBSElement,
                    ControlAccount.wbs_element_id == WBSElement.wbs_element_id,
                )
                .where(
                    WBSElement.project_id == entity_id,
                    func.upper(cast(Any, CostElement).valid_time).is_(None),
                    cast(Any, CostElement).deleted_at.is_(None),
                    func.upper(cast(Any, WBSElement).valid_time).is_(None),
                    cast(Any, WBSElement).deleted_at.is_(None),
                )
            )
        else:
            raise ValueError(
                f"Unsupported entity_type '{entity_type}' for cost element resolution"
            )

        result = await self.session.execute(stmt)
        return [row.cost_element_id for row in result.all()]

    async def get_aggregated_costs_by_entity(
        self,
        entity_type: str,
        entity_id: UUID,
        period: str,
        start_date: datetime,
        end_date: datetime | None = None,
        as_of: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Get cost aggregations by time period for a cost element, WBS element, or project.

        Args:
            entity_type: "cost_element", "wbs_element", or "project"
            entity_id: Root ID of the entity
            period: Period type ("daily", "weekly", "monthly")
            start_date: Start date for aggregation
            end_date: End date for aggregation (defaults to now)
            as_of: Optional timestamp for time-travel query

        Returns:
            List of dicts with period_start and total_amount, sorted by period_start.
        """
        if entity_type == "cost_element":
            return await self.get_costs_by_period(
                cost_element_id=entity_id,
                period=period,
                start_date=start_date,
                end_date=end_date,
                as_of=as_of,
            )

        ce_ids = await self._resolve_cost_element_ids(entity_type, entity_id)
        if not ce_ids:
            return []

        return await self._get_costs_by_period_for_ces(
            ce_ids=ce_ids,
            period=period,
            start_date=start_date,
            end_date=end_date,
            as_of=as_of,
        )

    async def get_cumulative_costs_by_entity(
        self,
        entity_type: str,
        entity_id: UUID,
        start_date: datetime,
        end_date: datetime | None = None,
        as_of: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Get cumulative costs over time for a cost element, WBS element, or project.

        Args:
            entity_type: "cost_element", "wbs_element", or "project"
            entity_id: Root ID of the entity
            start_date: Start date for calculation
            end_date: End date for calculation (defaults to now)
            as_of: Optional timestamp for time-travel query

        Returns:
            List of dicts with registration_date, amount, and cumulative_amount.
        """
        if entity_type == "cost_element":
            return await self.get_cumulative_costs(
                cost_element_id=entity_id,
                start_date=start_date,
                end_date=end_date,
                as_of=as_of,
            )

        ce_ids = await self._resolve_cost_element_ids(entity_type, entity_id)
        if not ce_ids:
            return []

        batch_result = await self.get_cumulative_costs_batch(
            cost_element_ids=ce_ids,
            start_date=start_date,
            end_date=end_date,
            as_of=as_of,
        )

        merged: dict[str, float] = {}
        for _ce_id, entries in batch_result.items():
            for entry in entries:
                key = entry["registration_date"]
                merged[key] = merged.get(key, 0.0) + entry["amount"]

        cumulative_amount = Decimal("0")
        result: list[dict[str, Any]] = []
        for date_key in sorted(merged.keys()):
            amount = merged[date_key]
            cumulative_amount += Decimal(str(amount))
            result.append(
                {
                    "registration_date": date_key,
                    "amount": amount,
                    "cumulative_amount": float(cumulative_amount),
                }
            )

        return result

    async def get_totals_for_cost_elements(
        self,
        cost_element_ids: list[UUID],
        as_of: datetime | None = None,
    ) -> dict[UUID, Decimal]:
        """Calculate total costs for multiple cost elements efficiently.

        Args:
            cost_element_ids: List of cost element UUIDs
            as_of: Optional timestamp for historical query (time-travel)

        Returns:
            Dictionary mapping cost_element_id to total cost (Decimal)
        """
        if not cost_element_ids:
            return {}

        stmt = (
            select(
                CostRegistration.cost_element_id,
                func.sum(CostRegistration.amount).label("total"),
            )
            .where(CostRegistration.cost_element_id.in_(cost_element_ids))
            .group_by(CostRegistration.cost_element_id)
        )

        if as_of is not None:
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            stmt = stmt.where(func.upper(CostRegistration.valid_time).is_(None))
            stmt = stmt.where(CostRegistration.deleted_at.is_(None))

        result = await self.session.execute(stmt)

        totals = {id: Decimal("0.00") for id in cost_element_ids}
        for row in result.all():
            totals[row.cost_element_id] = row.total or Decimal("0.00")

        return totals
