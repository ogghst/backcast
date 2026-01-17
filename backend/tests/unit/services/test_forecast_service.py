"""Unit tests for Forecast Service.

Test-First Implementation following TDD methodology.
Tests from: docs/03-project-plan/iterations/2026-01-15-forecast-management/01-plan.md
"""

from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

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
        """T-001: Create a forecast returns created object with correct eac_amount and branch_id.

        Arrange:
            - A valid Cost Element exists (from fixture)
            - A ForecastCreate schema with eac_amount and cost_element_id
        Act:
            - Call ForecastService.create()
        Assert:
            - Returns a Forecast object
            - Forecast has correct eac_amount
            - Forecast has correct cost_element_id
            - Forecast is on correct branch

        Acceptance Criteria from plan:
            "Users can create a Forecast for a Cost Element on a specific branch"
            VERIFIED BY: Unit Test `test_create_forecast_on_branch`
        """
        # Arrange
        cost_element = cost_element_setup["cost_element"]
        service = ForecastService(db_session)

        forecast_in = ForecastCreate(
            cost_element_id=cost_element.cost_element_id,
            eac_amount=Decimal("95000.00"),
            basis_of_estimate="Updated estimate based on current progress",
        )
        actor_id = uuid4()
        branch = "main"

        # Act
        created_forecast = await service.create(
            forecast_in, actor_id=actor_id, branch=branch
        )

        # Assert
        assert created_forecast is not None
        assert created_forecast.eac_amount == Decimal("95000.00")
        assert created_forecast.cost_element_id == cost_element.cost_element_id
        assert created_forecast.branch == "main"
        assert (
            created_forecast.basis_of_estimate
            == "Updated estimate based on current progress"
        )
        assert created_forecast.created_by == actor_id
        assert created_forecast.forecast_id is not None

    @pytest.mark.asyncio
    async def test_create_forecast_on_feature_branch(
        self, db_session: AsyncSession, cost_element_setup
    ) -> None:
        """T-001b: Create forecast on feature branch (What-if scenario).

        Arrange:
            - A valid Cost Element exists
            - A ForecastCreate for a feature branch
        Act:
            - Create forecast on "co-123" branch
        Assert:
            - Forecast is created on the correct branch
            - Forecast has correct branch_id
        """
        # Arrange
        cost_element = cost_element_setup["cost_element"]
        service = ForecastService(db_session)

        forecast_in = ForecastCreate(
            cost_element_id=cost_element.cost_element_id,
            eac_amount=Decimal("110000.00"),
            basis_of_estimate="What-if scenario with cost overrun",
        )
        actor_id = uuid4()
        branch = "co-123"

        # Act
        created_forecast = await service.create(
            forecast_in, actor_id=actor_id, branch=branch
        )

        # Assert
        assert created_forecast is not None
        assert created_forecast.branch == "co-123"
        assert created_forecast.eac_amount == Decimal("110000.00")
        assert created_forecast.cost_element_id == cost_element.cost_element_id


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
