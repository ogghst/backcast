"""Unit tests for Project-Level Budget Validation.

Tests the fix for the critical bug where project-level budget threshold
validation was not working during cost registration submission.

Bug Description:
- Cost registration submission was only validating individual cost element budgets
- Project-level budget threshold (configured in Admin tab) was being ignored
- Total project spend against project budget was not being checked

Expected Behavior:
- When total project spend exceeds project budget × threshold (e.g., 80%)
- System should warn during cost registration submission
- Warning should show total project spend vs project budget
"""

from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.cost_element import CostElement
from app.models.domain.cost_element_type import CostElementType
from app.models.domain.department import Department
from app.models.domain.project import Project
from app.models.domain.wbe import WBE
from app.models.schemas.cost_registration import CostRegistrationCreate
from app.services.cost_registration_service import CostRegistrationService
from app.services.project_budget_settings_service import (
    ProjectBudgetSettingsService,
)


@pytest_asyncio.fixture
async def sample_project(db_session: AsyncSession) -> Project:
    """Create a sample project with budget for testing."""
    project = Project(
        project_id=uuid4(),
        code="TEST-PROJ",
        name="Test Project",
        description="Test project for budget validation",
        budget=Decimal("620000.00"),  # €620K budget
        created_by=uuid4(),
    )
    db_session.add(project)
    await db_session.flush()
    return project


@pytest_asyncio.fixture
async def sample_department(db_session: AsyncSession) -> Department:
    """Create a sample department for testing."""
    department = Department(
        department_id=uuid4(),
        code="ENG",
        name="Engineering",
        description="Engineering Department",
        created_by=uuid4(),
    )
    db_session.add(department)
    await db_session.flush()
    return department


@pytest_asyncio.fixture
async def sample_cost_element_type(sample_department: Department) -> CostElementType:
    """Create a sample cost element type for testing."""
    cost_element_type = CostElementType(
        cost_element_type_id=uuid4(),
        department_id=sample_department.department_id,
        code="LABOR",
        name="Labor Hours",
        description="Labor cost tracking",
        created_by=uuid4(),
    )
    return cost_element_type


@pytest_asyncio.fixture
async def sample_wbe(db_session: AsyncSession, sample_project: Project) -> WBE:
    """Create a sample WBE for testing."""
    wbe = WBE(
        wbe_id=uuid4(),
        project_id=sample_project.project_id,
        code="1.1",
        name="Site Preparation",
        description="Initial site preparation work",
        created_by=uuid4(),
    )
    db_session.add(wbe)
    await db_session.flush()
    return wbe


@pytest_asyncio.fixture
async def sample_cost_element_with_budget(
    db_session: AsyncSession,
    sample_wbe: WBE,
    sample_cost_element_type: CostElementType,
) -> CostElement:
    """Create a sample cost element with budget for testing."""
    cost_element = CostElement(
        cost_element_id=uuid4(),
        wbe_id=sample_wbe.wbe_id,
        cost_element_type_id=sample_cost_element_type.cost_element_type_id,
        code="TEST-001",
        name="Test Cost Element",
        budget_amount=Decimal("1000.00"),
        description="Test cost element with budget",
        created_by=uuid4(),
    )
    db_session.add(cost_element)
    await db_session.flush()
    return cost_element


class TestProjectBudgetValidation:
    """Test project-level budget validation (the fix for the critical bug)."""

    @pytest.mark.asyncio
    async def test_get_project_budget_status_returns_aggregated_spend(
        self,
        db_session: AsyncSession,
        sample_project: Project,
        sample_cost_element_with_budget: CostElement,
    ) -> None:
        """Test that project budget status aggregates spend across all cost elements."""
        # Arrange
        service = CostRegistrationService(db_session)

        # Create cost registrations totaling 500
        for _ in range(5):
            await service.create_cost_registration(
                CostRegistrationCreate(
                    cost_element_id=sample_cost_element_with_budget.cost_element_id,
                    amount=Decimal("100.00"),
                ),
                actor_id=uuid4(),
            )

        # Act
        project_status = await service.get_project_budget_status(
            project_id=sample_project.project_id
        )

        # Assert
        assert project_status.project_id == sample_project.project_id
        assert project_status.project_budget == Decimal("620000.00")
        assert project_status.total_spend == Decimal("500.00")
        assert project_status.remaining == Decimal("619500.00")
        assert project_status.percentage < Decimal("1.0")  # Less than 1%

    @pytest.mark.asyncio
    async def test_validate_budget_status_checks_project_level_not_cost_element(
        self,
        db_session: AsyncSession,
        sample_project: Project,
        sample_cost_element_with_budget: CostElement,
    ) -> None:
        """Test that validation checks project-level budget, not individual cost element.

        This is the core fix for the bug. Even if a cost element is under budget,
        if the total project spend exceeds the threshold, a warning should be returned.
        """
        # Arrange
        service = CostRegistrationService(db_session)
        settings_service = ProjectBudgetSettingsService(db_session)

        # Set warning threshold to 80%
        await settings_service.upsert_settings(
            project_id=sample_project.project_id,
            actor_id=uuid4(),
            warning_threshold_percent=Decimal("80.0"),
        )

        # Spend enough to exceed 80% of project budget
        # 80% of €620K = €496K
        amount_to_spend = Decimal("500000.00")
        await service.create_cost_registration(
            CostRegistrationCreate(
                cost_element_id=sample_cost_element_with_budget.cost_element_id,
                amount=amount_to_spend,
            ),
            actor_id=uuid4(),
        )

        # Act - Validate budget status
        warning = await service.validate_budget_status(
            cost_element_id=sample_cost_element_with_budget.cost_element_id,
            project_id=sample_project.project_id,
            user_id=uuid4(),
        )

        # Assert - Warning should be returned because project budget threshold exceeded
        assert warning is not None
        assert warning.exceeds_threshold is True
        assert warning.threshold_percent == Decimal("80.0")
        assert warning.current_percent > Decimal("80.0")
        assert "Project budget usage" in warning.message
        assert "500,000" in warning.message  # Total spend shown
        assert "620,000" in warning.message  # Project budget shown

    @pytest.mark.asyncio
    async def test_validate_budget_status_no_warning_when_below_threshold(
        self,
        db_session: AsyncSession,
        sample_project: Project,
        sample_cost_element_with_budget: CostElement,
    ) -> None:
        """Test that no warning is returned when project spend is below threshold."""
        # Arrange
        service = CostRegistrationService(db_session)
        settings_service = ProjectBudgetSettingsService(db_session)

        # Set warning threshold to 80%
        await settings_service.upsert_settings(
            project_id=sample_project.project_id,
            actor_id=uuid4(),
            warning_threshold_percent=Decimal("80.0"),
        )

        # Spend only 10% of project budget
        await service.create_cost_registration(
            CostRegistrationCreate(
                cost_element_id=sample_cost_element_with_budget.cost_element_id,
                amount=Decimal("62000.00"),  # 10% of €620K
            ),
            actor_id=uuid4(),
        )

        # Act - Validate budget status
        warning = await service.validate_budget_status(
            cost_element_id=sample_cost_element_with_budget.cost_element_id,
            project_id=sample_project.project_id,
            user_id=uuid4(),
        )

        # Assert - No warning when below threshold
        assert warning is None

    @pytest.mark.asyncio
    async def test_validate_budget_status_uses_custom_threshold(
        self,
        db_session: AsyncSession,
        sample_project: Project,
        sample_cost_element_with_budget: CostElement,
    ) -> None:
        """Test that validation uses custom project threshold when set."""
        # Arrange
        service = CostRegistrationService(db_session)
        settings_service = ProjectBudgetSettingsService(db_session)

        # Set custom threshold to 90%
        await settings_service.upsert_settings(
            project_id=sample_project.project_id,
            actor_id=uuid4(),
            warning_threshold_percent=Decimal("90.0"),
        )

        # Spend 85% of project budget (above default 80%, but below custom 90%)
        await service.create_cost_registration(
            CostRegistrationCreate(
                cost_element_id=sample_cost_element_with_budget.cost_element_id,
                amount=Decimal("527000.00"),  # 85% of €620K
            ),
            actor_id=uuid4(),
        )

        # Act - Validate budget status
        warning = await service.validate_budget_status(
            cost_element_id=sample_cost_element_with_budget.cost_element_id,
            project_id=sample_project.project_id,
            user_id=uuid4(),
        )

        # Assert - No warning when below custom threshold (90%)
        assert warning is None

    @pytest.mark.asyncio
    async def test_validate_budget_status_threshold_exactly_at_limit(
        self,
        db_session: AsyncSession,
        sample_project: Project,
        sample_cost_element_with_budget: CostElement,
    ) -> None:
        """Test validation behavior when usage exactly equals threshold."""
        # Arrange
        service = CostRegistrationService(db_session)
        settings_service = ProjectBudgetSettingsService(db_session)

        # Set warning threshold to 80%
        await settings_service.upsert_settings(
            project_id=sample_project.project_id,
            actor_id=uuid4(),
            warning_threshold_percent=Decimal("80.0"),
        )

        # Spend exactly 80% of project budget
        await service.create_cost_registration(
            CostRegistrationCreate(
                cost_element_id=sample_cost_element_with_budget.cost_element_id,
                amount=Decimal("496000.00"),  # Exactly 80% of €620K
            ),
            actor_id=uuid4(),
        )

        # Act - Validate budget status
        warning = await service.validate_budget_status(
            cost_element_id=sample_cost_element_with_budget.cost_element_id,
            project_id=sample_project.project_id,
            user_id=uuid4(),
        )

        # Assert - Warning when at or above threshold
        assert warning is not None
        assert warning.exceeds_threshold is True
        assert warning.current_percent == Decimal("80.0")

    @pytest.mark.asyncio
    async def test_project_budget_validation_bug_scenario(
        self,
        db_session: AsyncSession,
        sample_project: Project,
        sample_cost_element_with_budget: CostElement,
    ) -> None:
        """Test the exact bug scenario reported by the user.

        User's Test Results:
        - Project: VBM-ALB-2026 (budget: €620K, threshold: 80%)
        - Cost registration added: moved cost element from 78% to 92% of budget
        - EXPECTED: Budget warning upon submission (should trigger at 80%)
        - ACTUAL (before fix): NO warning appeared during submission

        This test reproduces the scenario and verifies the fix works.
        """
        # Arrange
        service = CostRegistrationService(db_session)
        settings_service = ProjectBudgetSettingsService(db_session)

        # Configure project with €620K budget and 80% threshold (like VBM-ALB-2026)
        await settings_service.upsert_settings(
            project_id=sample_project.project_id,
            actor_id=uuid4(),
            warning_threshold_percent=Decimal("80.0"),
        )

        # Simulate existing project spend at 78% of budget
        # 78% of €620K = €483.6K
        existing_spend = Decimal("483600.00")
        await service.create_cost_registration(
            CostRegistrationCreate(
                cost_element_id=sample_cost_element_with_budget.cost_element_id,
                amount=existing_spend,
            ),
            actor_id=uuid4(),
        )

        # Verify no warning at 78%
        warning_before = await service.validate_budget_status(
            cost_element_id=sample_cost_element_with_budget.cost_element_id,
            project_id=sample_project.project_id,
            user_id=uuid4(),
        )
        assert warning_before is None, "Should not warn at 78%"

        # Act: Add cost registration that pushes project to 92% of budget
        # Additional amount to go from 78% to 92% = 14% = €86.8K
        additional_amount = Decimal("86800.00")
        await service.create_cost_registration(
            CostRegistrationCreate(
                cost_element_id=sample_cost_element_with_budget.cost_element_id,
                amount=additional_amount,
            ),
            actor_id=uuid4(),
        )

        # Assert - Warning SHOULD be returned at 92% (this is the fix!)
        warning_after = await service.validate_budget_status(
            cost_element_id=sample_cost_element_with_budget.cost_element_id,
            project_id=sample_project.project_id,
            user_id=uuid4(),
        )

        assert warning_after is not None, "MUST warn when project exceeds 80% threshold"
        assert warning_after.exceeds_threshold is True
        assert warning_after.threshold_percent == Decimal("80.0")
        assert warning_after.current_percent == Decimal("92.0")
        assert "Project budget usage at 92.0%" in warning_after.message
        assert "exceeds warning threshold of 80.0%" in warning_after.message

    @pytest.mark.asyncio
    async def test_project_budget_aggregates_multiple_cost_elements(
        self,
        db_session: AsyncSession,
        sample_project: Project,
        sample_wbe: WBE,
        sample_cost_element_type: CostElementType,
    ) -> None:
        """Test that project budget status correctly aggregates across multiple cost elements."""
        # Arrange
        service = CostRegistrationService(db_session)

        # Create multiple cost elements
        ce1 = CostElement(
            cost_element_id=uuid4(),
            wbe_id=sample_wbe.wbe_id,
            cost_element_type_id=sample_cost_element_type.cost_element_type_id,
            code="CE-001",
            name="Cost Element 1",
            budget_amount=Decimal("100000.00"),
            created_by=uuid4(),
        )
        ce2 = CostElement(
            cost_element_id=uuid4(),
            wbe_id=sample_wbe.wbe_id,
            cost_element_type_id=sample_cost_element_type.cost_element_type_id,
            code="CE-002",
            name="Cost Element 2",
            budget_amount=Decimal("200000.00"),
            created_by=uuid4(),
        )
        db_session.add(ce1)
        db_session.add(ce2)
        await db_session.flush()

        # Spend on both cost elements
        await service.create_cost_registration(
            CostRegistrationCreate(
                cost_element_id=ce1.cost_element_id,
                amount=Decimal("50000.00"),  # 50% of CE1 budget
            ),
            actor_id=uuid4(),
        )
        await service.create_cost_registration(
            CostRegistrationCreate(
                cost_element_id=ce2.cost_element_id,
                amount=Decimal("100000.00"),  # 50% of CE2 budget
            ),
            actor_id=uuid4(),
        )

        # Act
        project_status = await service.get_project_budget_status(
            project_id=sample_project.project_id
        )

        # Assert - Total spend should be aggregated across both cost elements
        assert project_status.total_spend == Decimal("150000.00")  # 50K + 100K
        assert project_status.percentage > Decimal("24.0")  # ~24.19%

    @pytest.mark.asyncio
    async def test_project_budget_threshold_with_default_settings(
        self,
        db_session: AsyncSession,
        sample_project: Project,
        sample_cost_element_with_budget: CostElement,
    ) -> None:
        """Test that default threshold (80%) is used when no custom settings exist."""
        # Arrange
        service = CostRegistrationService(db_session)

        # Don't set custom settings - should use default 80%

        # Spend 85% of project budget
        await service.create_cost_registration(
            CostRegistrationCreate(
                cost_element_id=sample_cost_element_with_budget.cost_element_id,
                amount=Decimal("527000.00"),  # 85% of €620K
            ),
            actor_id=uuid4(),
        )

        # Act - Validate budget status
        warning = await service.validate_budget_status(
            cost_element_id=sample_cost_element_with_budget.cost_element_id,
            project_id=sample_project.project_id,
            user_id=uuid4(),
        )

        # Assert - Should use default 80% threshold and warn
        assert warning is not None
        assert warning.threshold_percent == Decimal("80.0")
        assert warning.current_percent > Decimal("80.0")
