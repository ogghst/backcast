"""Tests for Quality Event Service."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.models.schemas.quality_event import QualityEventCreate, QualityEventUpdate
from app.services.quality_event_service import QualityEventService


async def create_test_project(db_session: AsyncSession, admin_user, project_id: uuid4):
    """Create a test project with proper temporal fields."""
    stmt = text("""
        INSERT INTO projects (id, project_id, name, code, status, branch, valid_time, transaction_time, created_by)
        VALUES (:id, :project_id, :name, :code, :status, :branch, tstzrange(:now, NULL), tstzrange(clock_timestamp(), NULL), :created_by)
        RETURNING id
    """)
    result = await db_session.execute(stmt, {
        "id": uuid4(),
        "project_id": str(project_id),
        "name": "Test Project",
        "code": "TEST-PROJ",
        "status": "Active",
        "branch": "main",
        "now": datetime.now(UTC),
        "created_by": str(admin_user.id)
    })
    return result.scalar_one()


async def create_test_wbe(db_session: AsyncSession, admin_user, wbe_id: uuid4, project_id: uuid4):
    """Create a test WBE with proper temporal fields."""
    stmt = text("""
        INSERT INTO wbes (id, wbe_id, project_id, name, code, level, branch, valid_time, transaction_time, created_by)
        VALUES (:id, :wbe_id, :project_id, :name, :code, :level, :branch, tstzrange(:now, NULL), tstzrange(clock_timestamp(), NULL), :created_by)
        RETURNING id
    """)
    result = await db_session.execute(stmt, {
        "id": uuid4(),
        "wbe_id": str(wbe_id),
        "project_id": str(project_id),
        "name": "Test WBE",
        "code": "TEST-WBE",
        "level": 1,
        "branch": "main",
        "now": datetime.now(UTC),
        "created_by": str(admin_user.id)
    })
    return result.scalar_one()


async def create_test_cost_element(db_session: AsyncSession, admin_user, cost_element_id: uuid4, wbe_id: uuid4):
    """Create a test cost element with proper temporal fields."""
    stmt = text("""
        INSERT INTO cost_elements (id, cost_element_id, wbe_id, name, budget_amount, branch, valid_time, transaction_time, created_by)
        VALUES (:id, :cost_element_id, :wbe_id, :name, :budget_amount, :branch, tstzrange(:now, NULL), tstzrange(clock_timestamp(), NULL), :created_by)
        RETURNING id
    """)
    result = await db_session.execute(stmt, {
        "id": uuid4(),
        "cost_element_id": str(cost_element_id),
        "wbe_id": str(wbe_id),
        "name": "Test Cost Element",
        "budget_amount": Decimal("10000.00"),
        "branch": "main",
        "now": datetime.now(UTC),
        "created_by": str(admin_user.id)
    })
    return result.scalar_one()


@pytest.mark.asyncio
async def test_create_quality_event(db_session: AsyncSession, admin_user):
    """Test creating a quality event."""
    service = QualityEventService(db_session)

    cost_element_id = uuid4()
    project_id = uuid4()
    wbe_id = uuid4()

    # Create test hierarchy
    await create_test_project(db_session, admin_user, project_id)
    await create_test_wbe(db_session, admin_user, wbe_id, project_id)
    await create_test_cost_element(db_session, admin_user, cost_element_id, wbe_id)
    await db_session.flush()

    event_in = QualityEventCreate(
        cost_element_id=cost_element_id,
        description="Defective welding requiring rework",
        cost_impact=Decimal("500.00"),
        event_type="defect",
        severity="high",
        root_cause="Insufficient weld penetration",
    )

    # Create quality event
    event = await service.create_quality_event(
        event_in=event_in,
        actor_id=admin_user.id,
        branch="main",
    )

    assert event is not None
    assert event.quality_event_id is not None
    assert event.cost_element_id == cost_element_id
    assert event.description == "Defective welding requiring rework"
    assert event.cost_impact == Decimal("500.00")
    assert event.event_type == "defect"
    assert event.severity == "high"
    assert event.root_cause == "Insufficient weld penetration"
    assert event.created_by == admin_user.id


@pytest.mark.asyncio
async def test_update_quality_event(db_session: AsyncSession, admin_user):
    """Test updating a quality event creates a new version."""
    service = QualityEventService(db_session)

    cost_element_id = uuid4()
    quality_event_id = uuid4()
    project_id = uuid4()
    wbe_id = uuid4()

    # Create test hierarchy
    await create_test_project(db_session, admin_user, project_id)
    await create_test_wbe(db_session, admin_user, wbe_id, project_id)
    await create_test_cost_element(db_session, admin_user, cost_element_id, wbe_id)
    await db_session.flush()

    # Create initial event
    event_in = QualityEventCreate(
        quality_event_id=quality_event_id,
        cost_element_id=cost_element_id,
        description="Initial description",
        cost_impact=Decimal("100.00"),
        event_type="defect",
        severity="low",
    )

    created = await service.create_quality_event(
        event_in=event_in,
        actor_id=admin_user.id,
        branch="main",
    )

    # Update event
    update_data = QualityEventUpdate(
        description="Updated: Additional rework needed",
        cost_impact=Decimal("250.00"),
        severity="high",
    )

    updated = await service.update_quality_event(
        quality_event_id=quality_event_id,
        registration_in=update_data,
        actor_id=admin_user.id,
    )

    assert updated.description == "Updated: Additional rework needed"
    assert updated.cost_impact == Decimal("250.00")
    assert updated.severity == "high"


@pytest.mark.asyncio
async def test_soft_delete_quality_event(db_session: AsyncSession, admin_user):
    """Test soft deleting a quality event."""
    service = QualityEventService(db_session)

    cost_element_id = uuid4()
    quality_event_id = uuid4()
    project_id = uuid4()
    wbe_id = uuid4()

    # Create test hierarchy
    await create_test_project(db_session, admin_user, project_id)
    await create_test_wbe(db_session, admin_user, wbe_id, project_id)
    await create_test_cost_element(db_session, admin_user, cost_element_id, wbe_id)
    await db_session.flush()

    # Create event
    event_in = QualityEventCreate(
        quality_event_id=quality_event_id,
        cost_element_id=cost_element_id,
        description="To be deleted",
        cost_impact=Decimal("100.00"),
    )

    await service.create_quality_event(
        event_in=event_in,
        actor_id=admin_user.id,
        branch="main",
    )

    # Soft delete
    await service.soft_delete(
        quality_event_id=quality_event_id,
        actor_id=admin_user.id,
    )

    # Verify deleted
    retrieved = await service.get_by_id(quality_event_id)
    assert retrieved is None


@pytest.mark.asyncio
async def test_get_quality_events(db_session: AsyncSession, admin_user):
    """Test retrieving quality events with pagination."""
    service = QualityEventService(db_session)

    cost_element_id = uuid4()
    project_id = uuid4()
    wbe_id = uuid4()

    # Create test hierarchy
    await create_test_project(db_session, admin_user, project_id)
    await create_test_wbe(db_session, admin_user, wbe_id, project_id)
    await create_test_cost_element(db_session, admin_user, cost_element_id, wbe_id)
    await db_session.flush()

    # Create multiple events
    for i in range(3):
        event_in = QualityEventCreate(
            cost_element_id=cost_element_id,
            description=f"Event {i+1}",
            cost_impact=Decimal(f"{100 * (i+1)}.00"),
            event_type="defect",
        )
        await service.create_quality_event(
            event_in=event_in,
            actor_id=admin_user.id,
            branch="main",
        )

    # Get events
    events, total = await service.get_quality_events(
        filters={"cost_element_id": cost_element_id},
        skip=0,
        limit=10,
    )

    assert total == 3
    assert len(events) == 3


@pytest.mark.asyncio
async def test_get_total_for_cost_element(db_session: AsyncSession, admin_user):
    """Test getting total cost impact for a cost element."""
    service = QualityEventService(db_session)

    cost_element_id = uuid4()
    project_id = uuid4()
    wbe_id = uuid4()

    # Create test hierarchy
    await create_test_project(db_session, admin_user, project_id)
    await create_test_wbe(db_session, admin_user, wbe_id, project_id)
    await create_test_cost_element(db_session, admin_user, cost_element_id, wbe_id)
    await db_session.flush()

    # Create events with known costs
    costs = [Decimal("100.00"), Decimal("250.00"), Decimal("150.00")]
    for cost in costs:
        event_in = QualityEventCreate(
            cost_element_id=cost_element_id,
            description="Test defect",
            cost_impact=cost,
        )
        await service.create_quality_event(
            event_in=event_in,
            actor_id=admin_user.id,
            branch="main",
        )

    # Get total
    total = await service.get_total_for_cost_element(cost_element_id)
    expected_total = sum(costs)
    assert total == expected_total


@pytest.mark.asyncio
async def test_get_quality_events_by_period(db_session: AsyncSession, admin_user):
    """Test getting quality events aggregated by period."""
    service = QualityEventService(db_session)

    cost_element_id = uuid4()
    project_id = uuid4()
    wbe_id = uuid4()

    # Create test hierarchy
    await create_test_project(db_session, admin_user, project_id)
    await create_test_wbe(db_session, admin_user, wbe_id, project_id)
    await create_test_cost_element(db_session, admin_user, cost_element_id, wbe_id)
    await db_session.flush()

    # Create events on different dates
    start_date = datetime.now(UTC)
    for i in range(3):
        event_in = QualityEventCreate(
            cost_element_id=cost_element_id,
            description=f"Event {i+1}",
            cost_impact=Decimal("100.00"),
            event_date=start_date + timedelta(days=i),
        )
        await service.create_quality_event(
            event_in=event_in,
            actor_id=admin_user.id,
            branch="main",
        )

    # Get by period
    end_date = start_date + timedelta(days=7)
    result = await service.get_quality_events_by_period(
        cost_element_id=cost_element_id,
        period="daily",
        start_date=start_date,
        end_date=end_date,
    )

    assert len(result) == 3
    assert all("period_start" in item and "total_amount" in item for item in result)


@pytest.mark.asyncio
async def test_time_travel_query(db_session: AsyncSession, admin_user):
    """Test querying quality events as of a specific timestamp."""
    service = QualityEventService(db_session)

    cost_element_id = uuid4()
    quality_event_id = uuid4()
    project_id = uuid4()
    wbe_id = uuid4()

    # Create test hierarchy
    await create_test_project(db_session, admin_user, project_id)
    await create_test_wbe(db_session, admin_user, wbe_id, project_id)
    await create_test_cost_element(db_session, admin_user, cost_element_id, wbe_id)
    await db_session.flush()

    # Create event
    event_in = QualityEventCreate(
        quality_event_id=quality_event_id,
        cost_element_id=cost_element_id,
        description="Original description",
        cost_impact=Decimal("100.00"),
        control_date=datetime.now(UTC) - timedelta(days=1),
    )

    await service.create_quality_event(
        event_in=event_in,
        actor_id=admin_user.id,
        branch="main",
    )

    # Update event
    update_data = QualityEventUpdate(
        description="Updated description",
        cost_impact=Decimal("200.00"),
    )

    await service.update_quality_event(
        quality_event_id=quality_event_id,
        registration_in=update_data,
        actor_id=admin_user.id,
    )

    # Query as of yesterday (should get original version)
    as_of = datetime.now(UTC) - timedelta(hours=12)
    historical = await service.get_quality_event_as_of(
        quality_event_id=quality_event_id,
        as_of=as_of,
    )

    assert historical is not None
    assert historical.description == "Original description"
    assert historical.cost_impact == Decimal("100.00")
