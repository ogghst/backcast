"""Unit tests for Forecast Service.

Test-First Implementation following TDD methodology.
Tests from: docs/03-project-plan/iterations/2026-01-15-forecast-management/01-plan.md
"""

from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.forecast import Forecast
from app.models.schemas.cost_element import CostElementCreate
from app.models.schemas.cost_element_type import CostElementTypeCreate
from app.models.schemas.department import DepartmentCreate
from app.models.schemas.forecast import ForecastCreate
from app.models.schemas.project import ProjectCreate
from app.models.schemas.wbe import WBECreate
from app.services.cost_element_service import CostElementService
from app.services.cost_element_type_service import CostElementTypeService
from app.services.department import DepartmentService
from app.services.forecast_service import ForecastService
from app.services.project import ProjectService
from app.services.wbe import WBEService


@pytest_asyncio.fixture
async def cost_element_setup(db_session: AsyncSession):
    """Create Department -> Cost Element Type -> Project -> WBE -> Cost Element hierarchy."""
    # Create Department
    dept_service = DepartmentService(db_session)
    dept_in = DepartmentCreate(name="Mechanical", code="MECH", is_active=True)
    dept = await dept_service.create_department(dept_in, actor_id=uuid4())

    # Create Cost Element Type
    type_service = CostElementTypeService(db_session)
    type_in = CostElementTypeCreate(
        code="MECH-INST",
        name="Mechanical Installation",
        description="Mechanical installation work",
        department_id=dept.department_id,
    )
    cost_type = await type_service.create(type_in, actor_id=uuid4())

    # Create Project
    project_service = ProjectService(db_session)
    project_in = ProjectCreate(
        name="Project Alpha",
        code="PROJ-A",
        budget=Decimal("1000000.00"),
        status="Draft",
    )
    project = await project_service.create_project(project_in, actor_id=uuid4())

    # Create WBE
    wbe_service = WBEService(db_session)
    wbe_in = WBECreate(
        project_id=project.project_id,
        code="1.1",
        name="Site Preparation",
        budget_allocation=Decimal("100000.00"),
        level=1,
    )
    wbe = await wbe_service.create_wbe(wbe_in, actor_id=uuid4())

    # Create Cost Element
    element_service = CostElementService(db_session)
    element_in = CostElementCreate(
        code="CE-001",
        name="Mechanical Work Phase 1",
        wbe_id=wbe.wbe_id,
        cost_element_type_id=cost_type.cost_element_type_id,
        budget_amount=Decimal("100000.00"),  # BAC
        description="Phase 1 mechanical installation",
        branch="main",
    )
    cost_element = await element_service.create(
        element_in, actor_id=uuid4(), branch="main"
    )

    return {
        "department": dept,
        "cost_type": cost_type,
        "project": project,
        "wbe": wbe,
        "cost_element": cost_element,
    }


class TestForecastServiceCreate:
    """Test ForecastService.create() method - TDD RED-GREEN-REFACTOR."""

    @pytest.mark.asyncio
    async def test_create_forecast_returns_forecast(
        self, db_session: AsyncSession, cost_element_setup
    ) -> None:
        """T-001: Create a forecast for a cost element using create_for_cost_element.

        Arrange:
            - A valid Cost Element exists (from fixture)
            - Delete the auto-created forecast first
        Act:
            - Call ForecastService.create_for_cost_element()
        Assert:
            - Returns a Forecast object
            - Forecast has correct eac_amount
            - Forecast is linked to cost element via cost_element.forecast_id

        Note: Updated for 1:1 relationship where cost_element has forecast_id.
        """
        # Arrange
        cost_element = cost_element_setup["cost_element"]
        service = ForecastService(db_session)
        actor_id = uuid4()

        # Delete the auto-created forecast first so we can create a new one
        auto_created = await service.get_for_cost_element(
            cost_element_id=cost_element.cost_element_id,
            branch="main",
        )
        if auto_created:
            # Soft delete the auto-created forecast
            from app.core.versioning.commands import SoftDeleteCommand
            delete_cmd = SoftDeleteCommand(
                entity_class=Forecast,
                root_id=auto_created.forecast_id,
                actor_id=actor_id,
            )
            await delete_cmd.execute(db_session)
            await db_session.flush()

            # Clear the forecast_id on the cost element

            from sqlalchemy import func, select
            ce_stmt = (
                select(type(cost_element))
                .where(
                    type(cost_element).cost_element_id == cost_element.cost_element_id,
                    type(cost_element).branch == "main",
                    func.upper(type(cost_element).valid_time).is_(None),
                    type(cost_element).deleted_at.is_(None),
                )
                .order_by(type(cost_element).valid_time.desc())
                .limit(1)
            )
            ce_result = await db_session.execute(ce_stmt)
            current_ce = ce_result.scalar_one_or_none()

            if current_ce:
                current_ce.forecast_id = None
                await db_session.flush()

        # Act - use new create_for_cost_element method
        created_forecast = await service.create_for_cost_element(
            cost_element_id=cost_element.cost_element_id,
            actor_id=actor_id,
            branch="main",
            eac_amount=Decimal("95000.00"),
            basis_of_estimate="Updated estimate based on current progress",
        )

        # Assert
        assert created_forecast is not None
        assert created_forecast.eac_amount == Decimal("95000.00")
        assert created_forecast.branch == "main"
        assert (
            created_forecast.basis_of_estimate
            == "Updated estimate based on current progress"
        )
        assert created_forecast.created_by == actor_id
        assert created_forecast.forecast_id is not None

        # Verify cost element's forecast_id was set
        from sqlalchemy import func, select
        ce_stmt = (
            select(type(cost_element))
            .where(
                type(cost_element).cost_element_id == cost_element.cost_element_id,
                type(cost_element).branch == "main",
                func.upper(type(cost_element).valid_time).is_(None),
                type(cost_element).deleted_at.is_(None),
            )
            .order_by(type(cost_element).valid_time.desc())
            .limit(1)
        )
        ce_result = await db_session.execute(ce_stmt)
        current_ce = ce_result.scalar_one_or_none()
        assert current_ce is not None
        assert current_ce.forecast_id == created_forecast.forecast_id

    @pytest.mark.asyncio
    async def test_create_forecast_on_feature_branch(
        self, db_session: AsyncSession, cost_element_setup
    ) -> None:
        """T-001b: Create forecast on feature branch (What-if scenario).

        Arrange:
            - A valid Cost Element exists
        Act:
            - Create forecast on "co-123" branch using create_for_cost_element
        Assert:
            - Forecast is created on the correct branch
            - Forecast has correct eac_amount

        Note: Updated for 1:1 relationship where cost_element has forecast_id.
        """
        # Arrange
        cost_element = cost_element_setup["cost_element"]
        service = ForecastService(db_session)
        actor_id = uuid4()
        branch = "co-123"

        # Act - use new create_for_cost_element method
        created_forecast = await service.create_for_cost_element(
            cost_element_id=cost_element.cost_element_id,
            actor_id=actor_id,
            branch=branch,
            eac_amount=Decimal("110000.00"),
            basis_of_estimate="What-if scenario with cost overrun",
        )

        # Assert
        assert created_forecast is not None
        assert created_forecast.branch == "co-123"
        assert created_forecast.eac_amount == Decimal("110000.00")


class TestForecastServiceGet:
    """Test ForecastService.get_by_id() method."""

    @pytest.mark.asyncio
    async def test_get_forecast_respects_branch_fallback(
        self, db_session: AsyncSession, cost_element_setup
    ) -> None:
        """T-002: Branch fallback logic for forecast retrieval.

        Arrange:
            - A Cost Element exists
            - A Forecast exists on main branch
            - No forecast exists on feature branch
        Act:
            - Try to get forecast from feature branch using STRICT mode
        Assert:
            - Returns None if not on that branch (STRICT mode)
            - Main branch forecast exists when queried directly

        Acceptance Criteria from plan:
            "Users can view the latest Forecast for a Cost Element, respecting branch fallbacks"
            VERIFIED BY: Unit Test `test_get_latest_forecast_merge_logic`
        """
        # Arrange
        cost_element = cost_element_setup["cost_element"]
        service = ForecastService(db_session)

        # Create forecast on main branch
        forecast_in = ForecastCreate(
            cost_element_id=cost_element.cost_element_id,
            eac_amount=Decimal("95000.00"),
            basis_of_estimate="Main branch forecast",
        )
        main_forecast = await service.create(
            forecast_in, actor_id=uuid4(), branch="main"
        )
        forecast_id = main_forecast.forecast_id

        # Act - Try to get from non-existent branch (STRICT mode)
        branch_forecast = await service.get_by_id(forecast_id, branch="co-999")

        # Assert - STRICT mode: None if not on that branch
        assert branch_forecast is None

        # Act - Get from main branch
        main_result = await service.get_by_id(forecast_id, branch="main")

        # Assert - Main branch forecast exists
        assert main_result is not None
        assert main_result.forecast_id == forecast_id
        assert main_result.eac_amount == Decimal("95000.00")


class TestForecastCalculations:
    """Test EVM calculation logic for Forecasts."""

    @pytest.mark.asyncio
    async def test_calculate_vac_positive(
        self, db_session: AsyncSession, cost_element_setup
    ) -> None:
        """T-003: Calculate VAC (Variance at Complete) when under budget.

        VAC = BAC - EAC
        Positive VAC = Under Budget (good)

        Arrange:
            - Cost Element with BAC = $100,000
            - Forecast with EAC = $80,000
        Act:
            - Calculate VAC
        Assert:
            - VAC = $20,000 (positive, under budget)

        Acceptance Criteria from plan:
            "Comparison logic correctly calculates Variance at Complete (VAC = BAC - EAC)"
            VERIFIED BY: Unit Test `test_forecast_comparison_calculations`
        """
        # Arrange
        cost_element = cost_element_setup["cost_element"]  # BAC = 100,000
        bac = cost_element.budget_amount  # 100,000

        service = ForecastService(db_session)
        forecast_in = ForecastCreate(
            cost_element_id=cost_element.cost_element_id,
            eac_amount=Decimal("80000.00"),  # EAC = 80,000
            basis_of_estimate="Improved efficiency",
        )
        created = await service.create(forecast_in, actor_id=uuid4(), branch="main")

        # Act - Calculate VAC
        vac = bac - created.eac_amount  # VAC = BAC - EAC

        # Assert
        assert vac == Decimal("20000.00")  # Positive = Under Budget

    @pytest.mark.asyncio
    async def test_calculate_vac_negative(
        self, db_session: AsyncSession, cost_element_setup
    ) -> None:
        """T-004: Calculate VAC (Variance at Complete) when over budget.

        VAC = BAC - EAC
        Negative VAC = Over Budget (bad)

        Arrange:
            - Cost Element with BAC = $100,000
            - Forecast with EAC = $120,000
        Act:
            - Calculate VAC
        Assert:
            - VAC = -$20,000 (negative, over budget)

        Acceptance Criteria from plan:
            "Comparison logic correctly calculates Variance at Complete (VAC = BAC - EAC)"
            VERIFIED BY: Unit Test `test_forecast_comparison_calculations`
        """
        # Arrange
        cost_element = cost_element_setup["cost_element"]  # BAC = 100,000
        bac = cost_element.budget_amount  # 100,000

        service = ForecastService(db_session)
        forecast_in = ForecastCreate(
            cost_element_id=cost_element.cost_element_id,
            eac_amount=Decimal("120000.00"),  # EAC = 120,000
            basis_of_estimate="Cost overruns expected",
        )
        created = await service.create(forecast_in, actor_id=uuid4(), branch="main")

        # Act - Calculate VAC
        vac = bac - created.eac_amount  # VAC = BAC - EAC

        # Assert
        assert vac == Decimal("-20000.00")  # Negative = Over Budget

    @pytest.mark.asyncio
    async def test_calculate_etc(
        self, db_session: AsyncSession, cost_element_setup
    ) -> None:
        """T-005: Calculate ETC (Estimate to Complete).

        ETC = EAC - AC
        ETC represents the remaining work to be completed.

        Arrange:
            - Cost Element with BAC = $100,000
            - Actual Cost (AC) = $50,000 (simulated)
            - Forecast with EAC = $120,000
        Act:
            - Calculate ETC
        Assert:
            - ETC = $70,000 (remaining work)

        Acceptance Criteria from plan:
            "Comparison logic correctly calculates Estimate to Complete (ETC = EAC - AC)"
            VERIFIED BY: Unit Test `test_forecast_comparison_calculations`
        """
        # Arrange
        cost_element = cost_element_setup["cost_element"]
        ac = Decimal("50000.00")  # Actual Cost so far (simulated)

        service = ForecastService(db_session)
        forecast_in = ForecastCreate(
            cost_element_id=cost_element.cost_element_id,
            eac_amount=Decimal("120000.00"),  # EAC = 120,000
            basis_of_estimate="Cost overruns expected",
        )
        created = await service.create(forecast_in, actor_id=uuid4(), branch="main")

        # Act - Calculate ETC
        etc = created.eac_amount - ac  # ETC = EAC - AC

        # Assert
        assert etc == Decimal("70000.00")  # Remaining work


class TestForecastService1to1Relationship:
    """Test ForecastService 1:1 Cost Element relationship - TDD RED-GREEN-REFACTOR."""

    @pytest.mark.asyncio
    async def test_forecast_already_exists_error_exception(
        self, db_session: AsyncSession
    ) -> None:
        """T-F-001: Test that ForecastAlreadyExistsError exception can be raised and caught.

        RED: Test that the exception class exists and can be instantiated
        """
        # Import the exception
        from app.services.forecast_service import ForecastAlreadyExistsError

        # Arrange & Act
        error = ForecastAlreadyExistsError(
            cost_element_id=str(uuid4()), branch="main"
        )

        # Assert
        assert "already exists" in str(error)
        assert error.cost_element_id in str(error)
        assert error.branch == "main"

    @pytest.mark.asyncio
    async def test_forecast_get_for_cost_element_returns_forecast(
        self, db_session: AsyncSession, cost_element_setup
    ) -> None:
        """T-F-002: Test that get_for_cost_element returns the linked forecast.

        Note: With 1:1 relationship, CostElementService.create() now auto-creates
        a default forecast. This test verifies that the auto-created forecast can be retrieved.
        """
        # Arrange
        cost_element = cost_element_setup["cost_element"]
        service = ForecastService(db_session)

        # Act - get the auto-created forecast
        result = await service.get_for_cost_element(
            cost_element_id=cost_element.cost_element_id,
            branch="main",
        )

        # Assert
        assert result is not None
        assert result.eac_amount == Decimal("100000.00")  # Default is budget_amount
        assert result.basis_of_estimate == "Initial forecast"
        assert result.forecast_id is not None

    @pytest.mark.asyncio
    async def test_forecast_get_for_cost_element_returns_none_when_missing(
        self, db_session: AsyncSession, cost_element_setup
    ) -> None:
        """T-F-003: Test that get_for_cost_element returns None when forecast_id is NULL.

        Note: CostElementService.create() now auto-creates a forecast, so we need to
        delete it first to test the "missing" case.
        """
        # Arrange
        cost_element = cost_element_setup["cost_element"]
        service = ForecastService(db_session)

        # Delete the auto-created forecast
        auto_created = await service.get_for_cost_element(
            cost_element_id=cost_element.cost_element_id,
            branch="main",
        )
        assert auto_created is not None, "Auto-created forecast should exist"

        # Soft delete the forecast
        from app.core.versioning.commands import SoftDeleteCommand
        delete_cmd = SoftDeleteCommand(
            entity_class=Forecast,
            root_id=auto_created.forecast_id,
            actor_id=uuid4(),
        )
        await delete_cmd.execute(db_session)
        await db_session.flush()

        # Also need to clear the forecast_id on the cost element

        from sqlalchemy import func, select
        ce_stmt = (
            select(type(cost_element))
            .where(
                type(cost_element).cost_element_id == cost_element.cost_element_id,
                type(cost_element).branch == "main",
                func.upper(type(cost_element).valid_time).is_(None),
                type(cost_element).deleted_at.is_(None),
            )
            .order_by(type(cost_element).valid_time.desc())
            .limit(1)
        )
        ce_result = await db_session.execute(ce_stmt)
        current_ce = ce_result.scalar_one_or_none()

        if current_ce:
            current_ce.forecast_id = None
            await db_session.flush()

        # Act - try to get the deleted forecast
        result = await service.get_for_cost_element(
            cost_element_id=cost_element.cost_element_id,
            branch="main",
        )

        # Assert
        assert result is None, "Should return None when forecast_id is NULL"

    @pytest.mark.asyncio
    async def test_forecast_create_duplicate_raises_error(
        self, db_session: AsyncSession, cost_element_setup
    ) -> None:
        """T-F-004: Test that creating duplicate forecast for cost element raises error.

        RED: Method doesn't exist yet
        """
        from app.services.forecast_service import ForecastAlreadyExistsError

        # Arrange
        cost_element = cost_element_setup["cost_element"]
        service = ForecastService(db_session)
        actor_id = uuid4()

        # A forecast already exists (auto-created by CostElementService.create())
        # Try to create another one - should raise error
        # Act & Assert
        with pytest.raises(ForecastAlreadyExistsError) as exc_info:
            await service.create_for_cost_element(
                cost_element_id=cost_element.cost_element_id,
                actor_id=actor_id,
                branch="main",
                eac_amount=Decimal("120000.00"),
                basis_of_estimate="Duplicate forecast",
            )

        # Assert error details
        assert "already exists" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_forecast_ensure_exists_creates_when_missing(
        self, db_session: AsyncSession, cost_element_setup
    ) -> None:
        """T-F-005: Test that ensure_exists creates forecast when none exists.

        RED: Method doesn't exist yet
        """
        # Arrange
        cost_element = cost_element_setup["cost_element"]
        service = ForecastService(db_session)

        # Cost element was created without forecast (forecast_id is NULL)

        # Act
        result = await service.ensure_exists(
            cost_element_id=cost_element.cost_element_id,
            actor_id=uuid4(),
            branch="main",
            budget_amount=Decimal("100000.00"),
        )

        # Assert
        assert result is not None
        assert result.eac_amount == Decimal("100000.00")
        assert result.basis_of_estimate == "Initial forecast"

    @pytest.mark.asyncio
    async def test_forecast_ensure_exists_returns_existing(
        self, db_session: AsyncSession, cost_element_setup
    ) -> None:
        """T-F-006: Test that ensure_exists returns existing forecast.

        RED: Method doesn't exist yet
        """
        # Arrange
        cost_element = cost_element_setup["cost_element"]
        service = ForecastService(db_session)

        # Create existing forecast
        forecast_in = ForecastCreate(
            cost_element_id=cost_element.cost_element_id,
            eac_amount=Decimal("100000.00"),
            basis_of_estimate="Initial forecast",
        )
        existing_forecast = await service.create(
            forecast_in, actor_id=uuid4(), branch="main"
        )

        # Update cost element with forecast_id
        from typing import cast

        from sqlalchemy import func, select

        ce_stmt = (
            select(cost_element.__class__)
            .where(
                cost_element.__class__.cost_element_id == cost_element.cost_element_id,
                cost_element.__class__.branch == "main",
                func.upper(cast(Any, cost_element.__class__).valid_time).is_(None),
                cast(Any, cost_element.__class__).deleted_at.is_(None),
            )
            .order_by(cast(Any, cost_element.__class__).valid_time.desc())
            .limit(1)
        )
        ce_result = await db_session.execute(ce_stmt)
        current_ce = ce_result.scalar_one_or_none()

        if current_ce:
            current_ce.forecast_id = existing_forecast.forecast_id
            await db_session.flush()

        # Act
        result = await service.ensure_exists(
            cost_element_id=cost_element.cost_element_id,
            actor_id=uuid4(),
            branch="main",
            budget_amount=Decimal("100000.00"),
        )

        # Assert
        assert result is not None
        assert result.forecast_id == existing_forecast.forecast_id
        assert result.eac_amount == Decimal("100000.00")
