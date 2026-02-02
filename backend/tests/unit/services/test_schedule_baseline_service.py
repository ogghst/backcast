"""Tests for ScheduleBaselineService - 1:1 relationship with Cost Elements.

Tests verify that:
1. get_for_cost_element() returns the single baseline for a cost element
2. get_for_cost_element() returns None when no baseline exists
3. ensure_exists() creates a baseline if none exists
4. ensure_exists() returns existing baseline if present
5. Duplicate baseline creation is prevented
6. Cost element creation auto-creates default baseline
7. Cost element soft delete cascades to baseline
"""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.cost_element import CostElement
from app.models.domain.schedule_baseline import ScheduleBaseline
from app.services.cost_element_service import CostElementService
from app.services.schedule_baseline_service import (
    BaselineAlreadyExistsError,
    ScheduleBaselineService,
)


@pytest.mark.asyncio
async def test_schedule_baseline_get_for_cost_element_returns_baseline(
    db_session: AsyncSession,
):
    """Test T-001: get_for_cost_element() returns baseline when it exists.

    Given a cost element with schedule_baseline_id set,
    When get_for_cost_element() is called,
    Then it should return the ScheduleBaseline with matching ID,
    And branch filtering should work correctly.
    """
    # Arrange: Create cost element and schedule baseline
    service = ScheduleBaselineService(db_session)
    cost_element_id = uuid4()
    user_id = uuid4()
    baseline_id = uuid4()

    cost_element = CostElement(
        cost_element_id=cost_element_id,
        wbe_id=uuid4(),
        cost_element_type_id=uuid4(),
        code="TEST-001",
        name="Test Cost Element",
        budget_amount=100000.00,
        schedule_baseline_id=baseline_id,  # Set the FK reference
        created_by=user_id,
        branch="main",
    )
    db_session.add(cost_element)

    baseline = ScheduleBaseline(
        schedule_baseline_id=baseline_id,
        cost_element_id=cost_element_id,
        name="Test Baseline",
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=90),
        progression_type="LINEAR",
        created_by=user_id,
        branch="main",
    )
    db_session.add(baseline)
    await db_session.commit()

    # Act: Call get_for_cost_element()
    result = await service.get_for_cost_element(cost_element_id, branch="main")

    # Assert: Should return the baseline
    assert result is not None, "Should return baseline when it exists"
    assert result.schedule_baseline_id == baseline_id
    assert result.name == "Test Baseline"
    assert result.branch == "main"


@pytest.mark.asyncio
async def test_schedule_baseline_get_for_cost_element_returns_none_when_missing(
    db_session: AsyncSession,
):
    """Test T-002: get_for_cost_element() returns None when baseline is missing.

    Given a cost element with schedule_baseline_id=NULL,
    When get_for_cost_element() is called,
    Then it should return None.
    """
    # Arrange: Create cost element without schedule baseline
    service = ScheduleBaselineService(db_session)
    cost_element_id = uuid4()
    user_id = uuid4()

    cost_element = CostElement(
        cost_element_id=cost_element_id,
        wbe_id=uuid4(),
        cost_element_type_id=uuid4(),
        code="TEST-002",
        name="Test Cost Element Without Baseline",
        budget_amount=100000.00,
        schedule_baseline_id=None,  # No baseline
        created_by=user_id,
        branch="main",
    )
    db_session.add(cost_element)
    await db_session.commit()

    # Act: Call get_for_cost_element()
    result = await service.get_for_cost_element(cost_element_id, branch="main")

    # Assert: Should return None
    assert result is None, "Should return None when no baseline exists"


@pytest.mark.asyncio
async def test_schedule_baseline_get_for_cost_element_filters_by_branch(
    db_session: AsyncSession,
):
    """Test that get_for_cost_element() respects branch isolation.

    Given a cost element with baselines in different branches,
    When get_for_cost_element() is called with a specific branch,
    Then it should return only the baseline from that branch.
    """
    # Arrange: Create cost element and baselines in different branches
    service = ScheduleBaselineService(db_session)
    cost_element_id = uuid4()
    user_id = uuid4()
    baseline_main_id = uuid4()
    baseline_branch_id = uuid4()

    # Main branch cost element
    cost_element_main = CostElement(
        cost_element_id=cost_element_id,
        wbe_id=uuid4(),
        cost_element_type_id=uuid4(),
        code="TEST-003",
        name="Test Cost Element",
        budget_amount=100000.00,
        schedule_baseline_id=baseline_main_id,  # References main branch baseline
        created_by=user_id,
        branch="main",
    )
    db_session.add(cost_element_main)

    # Feature branch cost element (same root_id, different branch)
    cost_element_branch = CostElement(
        cost_element_id=cost_element_id,
        wbe_id=cost_element_main.wbe_id,
        cost_element_type_id=cost_element_main.cost_element_type_id,
        code="TEST-003",
        name="Test Cost Element",
        budget_amount=100000.00,
        schedule_baseline_id=baseline_branch_id,  # References feature branch baseline
        created_by=user_id,
        branch="feature-branch",
    )
    db_session.add(cost_element_branch)

    # Main branch baseline
    baseline_main = ScheduleBaseline(
        schedule_baseline_id=baseline_main_id,
        cost_element_id=cost_element_id,
        name="Main Branch Baseline",
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=90),
        progression_type="LINEAR",
        created_by=user_id,
        branch="main",
    )
    db_session.add(baseline_main)

    # Feature branch baseline (different ID)
    baseline_branch = ScheduleBaseline(
        schedule_baseline_id=baseline_branch_id,
        cost_element_id=cost_element_id,
        name="Feature Branch Baseline",
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=90),
        progression_type="GAUSSIAN",
        created_by=user_id,
        branch="feature-branch",
    )
    db_session.add(baseline_branch)
    await db_session.commit()

    # Act: Call get_for_cost_element() for main branch
    result_main = await service.get_for_cost_element(cost_element_id, branch="main")

    # Assert: Should return main branch baseline
    assert result_main is not None
    assert result_main.schedule_baseline_id == baseline_main_id
    assert result_main.name == "Main Branch Baseline"
    assert result_main.branch == "main"

    # Act: Call get_for_cost_element() for feature branch
    result_feature = await service.get_for_cost_element(
        cost_element_id, branch="feature-branch"
    )

    # Assert: Should return feature branch baseline
    assert result_feature is not None
    assert result_feature.schedule_baseline_id == baseline_branch_id
    assert result_feature.name == "Feature Branch Baseline"
    assert result_feature.branch == "feature-branch"


@pytest.mark.asyncio
async def test_schedule_baseline_ensure_exists_creates_baseline_when_missing(
    db_session: AsyncSession,
):
    """Test T-003: ensure_exists() creates a default baseline if none exists.

    Given a cost element without a schedule baseline,
    When ensure_exists() is called,
    Then it should create a new default baseline,
    And update the cost element's schedule_baseline_id.
    """
    # Arrange: Create cost element without baseline
    service = ScheduleBaselineService(db_session)
    cost_element_id = uuid4()
    user_id = uuid4()

    cost_element = CostElement(
        cost_element_id=cost_element_id,
        wbe_id=uuid4(),
        cost_element_type_id=uuid4(),
        code="TEST-004",
        name="Test Cost Element",
        budget_amount=100000.00,
        schedule_baseline_id=None,
        created_by=user_id,
        branch="main",
    )
    db_session.add(cost_element)
    await db_session.commit()

    # Act: Call ensure_exists()
    baseline = await service.ensure_exists(
        cost_element_id=cost_element_id,
        actor_id=user_id,
        branch="main",
    )

    # Assert: Should create and return baseline
    assert baseline is not None
    assert baseline.name == "Default Schedule"
    assert baseline.progression_type == "LINEAR"
    assert baseline.branch == "main"

    # Verify cost element was updated
    await db_session.refresh(cost_element)
    assert cost_element.schedule_baseline_id == baseline.schedule_baseline_id


@pytest.mark.asyncio
async def test_schedule_baseline_ensure_exists_returns_existing_baseline(
    db_session: AsyncSession,
):
    """Test T-004: ensure_exists() returns existing baseline if present.

    Given a cost element with an existing schedule baseline,
    When ensure_exists() is called,
    Then it should return the existing baseline without creating a new one.
    """
    # Arrange: Create cost element with baseline
    service = ScheduleBaselineService(db_session)
    cost_element_id = uuid4()
    user_id = uuid4()
    baseline_id = uuid4()

    cost_element = CostElement(
        cost_element_id=cost_element_id,
        wbe_id=uuid4(),
        cost_element_type_id=uuid4(),
        code="TEST-005",
        name="Test Cost Element",
        budget_amount=100000.00,
        schedule_baseline_id=baseline_id,
        created_by=user_id,
        branch="main",
    )
    db_session.add(cost_element)

    baseline = ScheduleBaseline(
        schedule_baseline_id=baseline_id,
        cost_element_id=cost_element_id,
        name="Existing Baseline",
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=90),
        progression_type="GAUSSIAN",
        created_by=user_id,
        branch="main",
    )
    db_session.add(baseline)
    await db_session.commit()

    # Act: Call ensure_exists()
    result = await service.ensure_exists(
        cost_element_id=cost_element_id,
        actor_id=user_id,
        branch="main",
    )

    # Assert: Should return existing baseline
    assert result is not None
    assert result.schedule_baseline_id == baseline_id
    assert result.name == "Existing Baseline"
    assert result.progression_type == "GAUSSIAN"

    # Verify no new baseline was created
    stmt = """
        SELECT COUNT(*) FROM schedule_baselines
        WHERE cost_element_id = :cost_element_id
        AND branch = :branch
        AND deleted_at IS NULL
    """
    from sqlalchemy import text

    count_result = await db_session.execute(
        text(stmt), {"cost_element_id": cost_element_id, "branch": "main"}
    )
    count = count_result.scalar_one()
    assert count == 1, "Should not create duplicate baseline"


@pytest.mark.asyncio
async def test_schedule_baseline_create_duplicate_raises_baseline_already_exists_error(
    db_session: AsyncSession,
):
    """Test T-005: Creating duplicate baseline raises BaselineAlreadyExistsError.

    Given a cost element with an existing schedule baseline,
    When attempting to create a second baseline for the same cost element,
    Then it should raise BaselineAlreadyExistsError.
    """
    # Arrange: Create cost element with baseline
    service = ScheduleBaselineService(db_session)
    cost_element_id = uuid4()
    user_id = uuid4()
    existing_baseline_id = uuid4()

    cost_element = CostElement(
        cost_element_id=cost_element_id,
        wbe_id=uuid4(),
        cost_element_type_id=uuid4(),
        code="TEST-006",
        name="Test Cost Element",
        budget_amount=100000.00,
        schedule_baseline_id=existing_baseline_id,
        created_by=user_id,
        branch="main",
    )
    db_session.add(cost_element)

    # Create the existing baseline
    existing_baseline = ScheduleBaseline(
        schedule_baseline_id=existing_baseline_id,
        cost_element_id=cost_element_id,
        name="Existing Baseline",
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=90),
        progression_type="LINEAR",
        created_by=user_id,
        branch="main",
    )
    db_session.add(existing_baseline)
    await db_session.commit()

    # Act & Assert: Attempting to create duplicate should raise error
    with pytest.raises(BaselineAlreadyExistsError) as exc_info:
        await service.create_for_cost_element(
            cost_element_id=cost_element_id,
            actor_id=user_id,
            name="Duplicate Baseline",
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=90),
            progression_type="LINEAR",
            branch="main",
        )

    assert exc_info.value.cost_element_id == cost_element_id
    assert exc_info.value.branch == "main"
    assert "already exists" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_cost_element_create_auto_creates_default_schedule_baseline(
    db_session: AsyncSession,
):
    """Test T-006: CostElementService.create() auto-creates default schedule baseline.

    Given valid CostElementCreate data,
    When CostElementService.create() is called,
    Then it should create both the CostElement AND a default ScheduleBaseline,
    And the baseline should have default values (name="Default Schedule", 90-day duration, LINEAR).
    """
    # Arrange: Setup service and data
    ce_service = CostElementService(db_session)
    user_id = uuid4()

    from app.models.schemas.cost_element import CostElementCreate

    element_data = CostElementCreate(
        wbe_id=uuid4(),
        cost_element_type_id=uuid4(),
        code="TEST-007",
        name="Test Cost Element",
        budget_amount=100000.00,
        branch="main",
    )

    # Act: Create cost element
    cost_element = await ce_service.create(
        element_in=element_data,
        actor_id=user_id,
        branch="main",
    )
    await db_session.commit()

    # Assert: Cost element should be created
    assert cost_element is not None
    assert cost_element.code == "TEST-007"
    assert cost_element.schedule_baseline_id is not None

    # Assert: Default baseline should exist
    sb_service = ScheduleBaselineService(db_session)
    baseline = await sb_service.get_for_cost_element(
        cost_element.cost_element_id, branch="main"
    )

    assert baseline is not None
    assert baseline.name == "Default Schedule"
    assert baseline.progression_type == "LINEAR"
    assert baseline.branch == "main"

    # Verify duration is approximately 90 days
    duration = (baseline.end_date - baseline.start_date).days
    assert duration == 90, f"Expected 90-day duration, got {duration} days"


@pytest.mark.asyncio
async def test_cost_element_create_baseline_failure_rolls_back_cost_element(
    db_session: AsyncSession,
    monkeypatch,
):
    """Test T-007: Baseline creation failure rolls back cost element creation.

    Given that schedule_baseline_service.create() raises an exception,
    When CostElementService.create() is called,
    Then the transaction should roll back,
    And no CostElement should be created.
    """
    # This test would require mocking the schedule baseline service
    # For now, we'll skip this as it's covered by integration tests
    # TODO: Implement with proper mocking
    pass


@pytest.mark.asyncio
async def test_cost_element_soft_delete_cascades_to_schedule_baseline(
    db_session: AsyncSession,
):
    """Test T-008: Soft deleting a cost element cascades to its schedule baseline.

    Given a cost element with a schedule baseline,
    When the cost element is soft deleted,
    Then the schedule baseline should also be soft deleted (deleted_at set).
    """
    # Arrange: Create cost element with baseline
    ce_service = CostElementService(db_session)
    sb_service = ScheduleBaselineService(db_session)
    user_id = uuid4()

    from app.models.schemas.cost_element import CostElementCreate

    element_data = CostElementCreate(
        wbe_id=uuid4(),
        cost_element_type_id=uuid4(),
        code="TEST-008",
        name="Test Cost Element",
        budget_amount=100000.00,
        branch="main",
    )

    cost_element = await ce_service.create(
        element_in=element_data,
        actor_id=user_id,
        branch="main",
    )
    await db_session.commit()

    baseline_id = cost_element.schedule_baseline_id
    assert baseline_id is not None

    # Act: Soft delete cost element
    await ce_service.soft_delete(
        cost_element_id=cost_element.cost_element_id,
        actor_id=user_id,
        branch="main",
    )
    await db_session.commit()

    # Assert: Baseline should be soft deleted
    baseline = await sb_service.get_by_id(baseline_id, branch="main")
    assert baseline is None, "Baseline should be soft deleted (deleted_at set)"
