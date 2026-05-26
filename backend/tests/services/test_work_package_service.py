"""Tests for WorkPackageService CRUD, queries, summaries, cost allocations, and type/status validation."""

import json
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio

# Pydantic ValidationError for schema-level validation tests
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.versioning.commands import CreateVersionCommand
from app.models.domain.cost_registration import CostRegistration
from app.models.domain.work_package import WorkPackage
from app.models.schemas.package_type import PackageTypeCreate
from app.models.schemas.work_package import (
    QualityCostAllocation,
    WorkPackageCreate,
    WorkPackageUpdate,
)
from app.services.package_type_service import PackageTypeService
from app.services.work_package_service import WorkPackageService


@pytest.fixture
def actor_id() -> tuple:
    """Return a consistent actor_id for tests."""
    return uuid4()


@pytest_asyncio.fixture(autouse=True)
async def seed_package_types(db_session: AsyncSession) -> None:
    """Seed PackageType rows required by _validate_package_type()."""
    seed_path = Path(__file__).resolve().parent.parent.parent / "seed" / "package_types.json"
    with open(seed_path) as f:
        types_data = json.load(f)

    service = PackageTypeService(db_session)
    for item in types_data:
        pt_in = PackageTypeCreate(**item)
        await service.create(pt_in, actor_id=uuid4())
    await db_session.flush()


# --- CRUD Tests ---


@pytest.mark.asyncio
async def test_create_work_package(
    db_session: AsyncSession,
    test_project,
    actor_id: tuple,
) -> None:
    """Create a basic quality_impact-typed work package and verify stored values."""
    service = WorkPackageService(db_session)

    data = WorkPackageCreate(
        name="NCR-2026-0042",
        package_type="quality_impact",
        external_event_id="NCR-2026-0042",
        project_id=test_project.project_id,
        coq_category="internal_failure",
        cost_impact=Decimal("5000.00"),
        schedule_impact_days=3,
    )

    wp = await service.create_work_package(data, actor_id=actor_id)
    await db_session.flush()

    assert wp.work_package_id == data.work_package_id
    assert wp.name == "NCR-2026-0042"
    assert wp.package_type == "quality_impact"
    assert wp.external_event_id == "NCR-2026-0042"
    assert wp.project_id == test_project.project_id
    assert wp.coq_category == "internal_failure"
    assert wp.cost_impact == Decimal("5000.00")
    assert wp.schedule_impact_days == 3
    assert wp.status == "open"
    assert wp.created_by == actor_id


@pytest.mark.asyncio
async def test_create_work_package_with_cost_allocations(
    db_session: AsyncSession,
    test_entity_hierarchy,
    actor_id: tuple,
) -> None:
    """Create a quality_impact work package with cost allocations and verify CostRegistrations."""
    service = WorkPackageService(db_session)
    hierarchy = test_entity_hierarchy
    project_id = hierarchy["project"].project_id
    ce_id = hierarchy["cost_element"].cost_element_id

    data = WorkPackageCreate(
        name="NCR-2026-0099",
        package_type="quality_impact",
        external_event_id="NCR-2026-0099",
        project_id=project_id,
        coq_category="prevention",
        cost_impact=Decimal("10000.00"),
        cost_allocations=[
            QualityCostAllocation(
                cost_element_id=ce_id,
                amount=Decimal("6000.00"),
            ),
            QualityCostAllocation(
                cost_element_id=ce_id,
                amount=Decimal("4000.00"),
            ),
        ],
    )

    wp = await service.create_work_package(data, actor_id=actor_id)
    await db_session.flush()

    assert wp is not None

    allocations = await service.get_allocations(wp.work_package_id)
    assert len(allocations) == 2

    amounts = {alloc.amount for alloc in allocations}
    assert Decimal("6000.00") in amounts
    assert Decimal("4000.00") in amounts

    # Verify both allocations point to the correct cost element
    for alloc in allocations:
        assert alloc.cost_element_id == ce_id
        assert alloc.cost_registration_id is not None


@pytest.mark.asyncio
async def test_update_work_package(
    db_session: AsyncSession,
    test_project,
    actor_id: tuple,
) -> None:
    """Create then update a work package, verify new version created."""
    service = WorkPackageService(db_session)

    create_data = WorkPackageCreate(
        name="NCR-2026-0050",
        package_type="quality_impact",
        external_event_id="NCR-2026-0050",
        project_id=test_project.project_id,
        coq_category="internal_failure",
        cost_impact=Decimal("3000.00"),
    )
    wp = await service.create_work_package(create_data, actor_id=actor_id)
    await db_session.flush()

    root_id = wp.work_package_id
    original_id = wp.id

    # Update
    update_data = WorkPackageUpdate(
        cost_impact=Decimal("7000.00"),
        schedule_impact_days=5,
    )
    updated = await service.update_work_package(
        root_id, update_data, actor_id=actor_id
    )
    await db_session.flush()

    assert updated.work_package_id == root_id
    assert updated.id != original_id  # new version
    assert updated.cost_impact == Decimal("7000.00")
    assert updated.schedule_impact_days == 5

    # Verify the old version is closed (get_by_id returns only current)
    current = await service.get_by_id(root_id)
    assert current is not None
    assert current.id == updated.id
    assert current.cost_impact == Decimal("7000.00")


@pytest.mark.asyncio
async def test_soft_delete_work_package(
    db_session: AsyncSession,
    test_project,
    actor_id: tuple,
) -> None:
    """Create then soft delete a work package, verify it is marked deleted."""
    service = WorkPackageService(db_session)

    data = WorkPackageCreate(
        name="NCR-2026-0060",
        package_type="quality_impact",
        external_event_id="NCR-2026-0060",
        project_id=test_project.project_id,
        coq_category="prevention",
        cost_impact=Decimal("2000.00"),
    )
    wp = await service.create_work_package(data, actor_id=actor_id)
    await db_session.flush()

    root_id = wp.work_package_id

    await service.soft_delete(root_id, actor_id=actor_id)
    await db_session.flush()

    # get_by_id should return None for soft-deleted
    deleted = await service.get_by_id(root_id)
    assert deleted is None

    # Verify deleted_at is set via raw query
    from sqlalchemy import select

    stmt = select(WorkPackage).where(
        WorkPackage.work_package_id == root_id,
        WorkPackage.id == wp.id,
    )
    result = await db_session.execute(stmt)
    row = result.scalar_one()
    assert row.deleted_at is not None


# --- Query Tests ---


@pytest.mark.asyncio
async def test_get_work_packages_by_project(
    db_session: AsyncSession,
    test_project,
    actor_id: tuple,
) -> None:
    """Create multiple packages for a project and verify listing with pagination."""
    service = WorkPackageService(db_session)
    project_id = test_project.project_id

    for i in range(5):
        data = WorkPackageCreate(
            name=f"WP-{i:04d}",
            package_type="quality_impact",
            external_event_id=f"NCR-2026-{i:04d}",
            project_id=project_id,
            coq_category="internal_failure",
            cost_impact=Decimal("1000.00") * (i + 1),
        )
        await service.create_work_package(data, actor_id=actor_id)
    await db_session.flush()

    # Get all
    packages, total = await service.get_work_packages(project_id)
    assert total == 5
    assert len(packages) == 5

    # Pagination: first page
    page1, total1 = await service.get_work_packages(project_id, skip=0, limit=2)
    assert total1 == 5
    assert len(page1) == 2

    # Pagination: second page
    page2, total2 = await service.get_work_packages(project_id, skip=2, limit=2)
    assert total2 == 5
    assert len(page2) == 2


@pytest.mark.asyncio
async def test_get_work_packages_filter_by_coq_category(
    db_session: AsyncSession,
    test_project,
    actor_id: tuple,
) -> None:
    """Create prevention and internal_failure packages, verify filtering."""
    service = WorkPackageService(db_session)
    project_id = test_project.project_id

    # Create 2 internal_failure
    for i in range(2):
        data = WorkPackageCreate(
            name=f"NC-{i:04d}",
            package_type="quality_impact",
            external_event_id=f"NCR-NC-{i:04d}",
            project_id=project_id,
            coq_category="internal_failure",
            cost_impact=Decimal("3000.00"),
        )
        await service.create_work_package(data, actor_id=actor_id)

    # Create 3 prevention
    for i in range(3):
        data = WorkPackageCreate(
            name=f"CF-{i:04d}",
            package_type="quality_impact",
            external_event_id=f"NCR-CF-{i:04d}",
            project_id=project_id,
            coq_category="prevention",
            cost_impact=Decimal("1500.00"),
        )
        await service.create_work_package(data, actor_id=actor_id)
    await db_session.flush()

    # Filter internal_failure
    nc_wps, nc_total = await service.get_work_packages(
        project_id, coq_category="internal_failure"
    )
    assert nc_total == 2
    assert all(wp.coq_category == "internal_failure" for wp in nc_wps)

    # Filter prevention
    cf_wps, cf_total = await service.get_work_packages(
        project_id, coq_category="prevention"
    )
    assert cf_total == 3
    assert all(wp.coq_category == "prevention" for wp in cf_wps)


# --- Summary Tests ---


@pytest.mark.asyncio
async def test_get_summary(
    db_session: AsyncSession,
    test_project,
    actor_id: tuple,
) -> None:
    """Create several packages and verify summary aggregation."""
    service = WorkPackageService(db_session)
    project_id = test_project.project_id

    # 2 internal_failure @ 5000 each = 10000
    for i in range(2):
        data = WorkPackageCreate(
            name=f"SUM-NC-{i}",
            package_type="quality_impact",
            external_event_id=f"NCR-SUM-NC-{i}",
            project_id=project_id,
            coq_category="internal_failure",
            cost_impact=Decimal("5000.00"),
            schedule_impact_days=3,
        )
        await service.create_work_package(data, actor_id=actor_id)

    # 1 prevention @ 2000
    data_cf = WorkPackageCreate(
        name="SUM-CF-0",
        package_type="quality_impact",
        external_event_id="NCR-SUM-CF-0",
        project_id=project_id,
        coq_category="prevention",
        cost_impact=Decimal("2000.00"),
        schedule_impact_days=1,
    )
    await service.create_work_package(data_cf, actor_id=actor_id)
    await db_session.flush()

    summary = await service.get_summary(project_id)

    assert summary.total_cost == Decimal("12000.00")
    assert summary.conformance_cost == Decimal("2000.00")
    assert summary.nonconformance_cost == Decimal("10000.00")
    assert summary.total_schedule_days == 7  # 3+3+1
    assert summary.impact_count == 3


# --- Allocation Tests ---


@pytest.mark.asyncio
async def test_get_allocations(
    db_session: AsyncSession,
    test_entity_hierarchy,
    actor_id: tuple,
) -> None:
    """Create package with cost allocations, verify get_allocations returns them."""
    service = WorkPackageService(db_session)
    hierarchy = test_entity_hierarchy
    project_id = hierarchy["project"].project_id
    ce_id = hierarchy["cost_element"].cost_element_id

    data = WorkPackageCreate(
        name="BD-001",
        package_type="quality_impact",
        external_event_id="NCR-BD-001",
        project_id=project_id,
        coq_category="internal_failure",
        cost_impact=Decimal("8000.00"),
        cost_allocations=[
            QualityCostAllocation(
                cost_element_id=ce_id, amount=Decimal("5000.00")
            ),
            QualityCostAllocation(
                cost_element_id=ce_id, amount=Decimal("3000.00")
            ),
        ],
    )

    wp = await service.create_work_package(data, actor_id=actor_id)
    await db_session.flush()

    allocations = await service.get_allocations(wp.work_package_id)
    assert len(allocations) == 2

    amounts = [alloc.amount for alloc in allocations]
    assert Decimal("5000.00") in amounts
    assert Decimal("3000.00") in amounts

    # Verify cost_element_id is set
    for alloc in allocations:
        assert alloc.cost_element_id == ce_id
        assert alloc.cost_registration_id is not None


@pytest.mark.asyncio
async def test_upsert_allocations(
    db_session: AsyncSession,
    test_entity_hierarchy,
    actor_id: tuple,
) -> None:
    """Create package, add allocations, then replace them via upsert."""
    service = WorkPackageService(db_session)
    hierarchy = test_entity_hierarchy
    project_id = hierarchy["project"].project_id
    ce_id = hierarchy["cost_element"].cost_element_id

    # Create with initial allocations
    data = WorkPackageCreate(
        name="UPS-001",
        package_type="quality_impact",
        external_event_id="NCR-UPS-001",
        project_id=project_id,
        coq_category="internal_failure",
        cost_impact=Decimal("9000.00"),
        cost_allocations=[
            QualityCostAllocation(
                cost_element_id=ce_id, amount=Decimal("9000.00")
            ),
        ],
    )

    wp = await service.create_work_package(data, actor_id=actor_id)
    await db_session.flush()

    # Verify initial allocation
    initial = await service.get_allocations(wp.work_package_id)
    assert len(initial) == 1
    assert initial[0].amount == Decimal("9000.00")

    # Replace with new allocations
    new_allocations = [
        QualityCostAllocation(
            cost_element_id=ce_id, amount=Decimal("4000.00")
        ),
        QualityCostAllocation(
            cost_element_id=ce_id, amount=Decimal("5000.00")
        ),
    ]
    result = await service.upsert_allocations(
        work_package_id=wp.work_package_id,
        allocations_data=new_allocations,
        actor_id=actor_id,
    )
    await db_session.flush()

    assert len(result) == 2

    # Verify old allocations are gone (get_allocations only returns current)
    after = await service.get_allocations(wp.work_package_id)
    assert len(after) == 2
    amounts = {alloc.amount for alloc in after}
    assert Decimal("4000.00") in amounts
    assert Decimal("5000.00") in amounts
    assert Decimal("9000.00") not in amounts


@pytest.mark.asyncio
async def test_compute_actual_cost(
    db_session: AsyncSession,
    test_entity_hierarchy,
    actor_id: tuple,
) -> None:
    """Create package with allocations, verify compute_actual_cost sums CRs."""
    service = WorkPackageService(db_session)
    hierarchy = test_entity_hierarchy
    project_id = hierarchy["project"].project_id
    ce_id = hierarchy["cost_element"].cost_element_id

    data = WorkPackageCreate(
        name="ACT-001",
        package_type="quality_impact",
        external_event_id="NCR-ACT-001",
        project_id=project_id,
        coq_category="internal_failure",
        cost_impact=Decimal("10000.00"),
        cost_allocations=[
            QualityCostAllocation(
                cost_element_id=ce_id, amount=Decimal("3000.00")
            ),
            QualityCostAllocation(
                cost_element_id=ce_id, amount=Decimal("2000.00")
            ),
        ],
    )

    wp = await service.create_work_package(data, actor_id=actor_id)
    await db_session.flush()

    actual_cost = await service.compute_actual_cost(wp.work_package_id)
    assert actual_cost == Decimal("5000.00")


# --- History Tests ---


@pytest.mark.asyncio
async def test_get_history(
    db_session: AsyncSession,
    test_project,
    actor_id: tuple,
) -> None:
    """Create and update a package, verify history returns multiple versions."""
    service = WorkPackageService(db_session)

    data = WorkPackageCreate(
        name="HIST-001",
        package_type="quality_impact",
        external_event_id="NCR-HIST-001",
        project_id=test_project.project_id,
        coq_category="internal_failure",
        cost_impact=Decimal("1000.00"),
    )
    wp = await service.create_work_package(data, actor_id=actor_id)
    await db_session.flush()

    root_id = wp.work_package_id

    # Update twice to create 3 versions total
    update1 = WorkPackageUpdate(cost_impact=Decimal("2000.00"))
    await service.update_work_package(root_id, update1, actor_id=actor_id)
    await db_session.flush()

    update2 = WorkPackageUpdate(cost_impact=Decimal("3000.00"))
    await service.update_work_package(root_id, update2, actor_id=actor_id)
    await db_session.flush()

    history = await service.get_history(root_id)

    assert len(history) == 3

    # History is ordered by transaction_time descending (newest first)
    assert history[0].cost_impact == Decimal("3000.00")
    assert history[1].cost_impact == Decimal("2000.00")
    assert history[2].cost_impact == Decimal("1000.00")

    # All versions share the same root ID
    for version in history:
        assert version.work_package_id == root_id


# --- COQ Metrics Tests ---


@pytest.mark.asyncio
async def test_get_coq_metrics(
    db_session: AsyncSession,
    test_entity_hierarchy,
    actor_id: tuple,
) -> None:
    """Create quality packages with allocations + regular CR, verify COQ metrics."""
    service = WorkPackageService(db_session)
    hierarchy = test_entity_hierarchy
    project_id = hierarchy["project"].project_id
    ce_id = hierarchy["cost_element"].cost_element_id

    # 1. Create an internal_failure quality package with 3000 allocation
    nc_data = WorkPackageCreate(
        name="COQ-NC-01",
        package_type="quality_impact",
        external_event_id="NCR-COQ-NC-01",
        project_id=project_id,
        coq_category="internal_failure",
        cost_impact=Decimal("5000.00"),
        cost_allocations=[
            QualityCostAllocation(
                cost_element_id=ce_id, amount=Decimal("3000.00")
            ),
        ],
    )
    await service.create_work_package(nc_data, actor_id=actor_id)
    await db_session.flush()

    # 2. Create a prevention quality package with 2000 allocation
    cf_data = WorkPackageCreate(
        name="COQ-CF-01",
        package_type="quality_impact",
        external_event_id="NCR-COQ-CF-01",
        project_id=project_id,
        coq_category="prevention",
        cost_impact=Decimal("3000.00"),
        cost_allocations=[
            QualityCostAllocation(
                cost_element_id=ce_id, amount=Decimal("2000.00")
            ),
        ],
    )
    await service.create_work_package(cf_data, actor_id=actor_id)
    await db_session.flush()

    # 3. Create a regular (non-quality) cost registration on the same CE
    regular_cr_id = uuid4()
    regular_cmd = CreateVersionCommand(
        entity_class=CostRegistration,  # type: ignore[type-var,unused-ignore]
        root_id=regular_cr_id,
        actor_id=actor_id,
        cost_registration_id=regular_cr_id,
        cost_element_id=ce_id,
        amount=Decimal("10000.00"),
        description="Regular cost, not quality-related",
    )
    await regular_cmd.execute(db_session)
    await db_session.flush()

    # 4. Get COQ metrics
    metrics = await service.get_coq_metrics(project_id)

    # Total COQ = internal_failure allocation (3000) + prevention allocation (2000)
    assert metrics.total_coq == Decimal("5000.00")

    # CPQ = internal_failure only = 3000
    assert metrics.cpq == Decimal("3000.00")

    # Total AC = quality CRs (3000+2000) + regular CR (10000) = 15000
    assert metrics.total_ac == Decimal("15000.00")

    # CPQ% = 3000 / 15000 * 100 = 20.00
    assert metrics.cpq_percentage == Decimal("20.00")

    # CPIq = 3000 / 15000 = 0.2000
    assert metrics.cpiq is not None
    assert metrics.cpiq == Decimal("0.2000")

    # QPI should be well below 0.85 at 20% CPQ, mapped to "Poor Performance"
    assert metrics.qpi is not None
    assert metrics.qpi < Decimal("0.85")
    assert metrics.qpi_rating == "Poor Performance"

    # COQ ratio = total_coq / project_budget * 100
    # Project budget from test_entity_hierarchy = 50000 (CE budget)
    assert metrics.coq_ratio is not None
    expected_ratio = (Decimal("5000.00") / Decimal("50000.00") * Decimal("100")).quantize(
        Decimal("0.01")
    )
    assert metrics.coq_ratio == expected_ratio


# --- NEW: Type Validation Tests ---


@pytest.mark.asyncio
async def test_create_work_package_invalid_type_raises(
    db_session: AsyncSession,
    test_project,
    actor_id: tuple,
) -> None:
    """Invalid package_type raises ValidationError from Pydantic schema."""
    with pytest.raises(ValidationError, match="package_type"):
        WorkPackageCreate(
            name="Invalid-Type",
            package_type="invalid_type",
            project_id=test_project.project_id,
            cost_impact=Decimal("1000.00"),
        )


@pytest.mark.asyncio
async def test_create_work_package_without_name_fails(
    db_session: AsyncSession,
    test_project,
    actor_id: tuple,
) -> None:
    """Creating a work package without a name raises ValidationError (T-003)."""
    with pytest.raises(ValidationError, match="name"):
        WorkPackageCreate(
            package_type="quality_impact",
            project_id=test_project.project_id,
            cost_impact=Decimal("1000.00"),
        )


@pytest.mark.asyncio
async def test_create_work_package_default_status_open(
    db_session: AsyncSession,
    test_project,
    actor_id: tuple,
) -> None:
    """New work package has status='open' without explicit setting."""
    service = WorkPackageService(db_session)

    data = WorkPackageCreate(
        name="Default-Status",
        package_type="site_visit",
        project_id=test_project.project_id,
        cost_impact=Decimal("1000.00"),
    )

    wp = await service.create_work_package(data, actor_id=actor_id)
    await db_session.flush()

    assert wp.status == "open"


@pytest.mark.asyncio
async def test_update_work_package_status_to_closed(
    db_session: AsyncSession,
    test_project,
    actor_id: tuple,
) -> None:
    """Status update to 'closed' succeeds; new version created."""
    service = WorkPackageService(db_session)

    create_data = WorkPackageCreate(
        name="Status-Test",
        package_type="quality_impact",
        external_event_id="NCR-STATUS-001",
        project_id=test_project.project_id,
        coq_category="internal_failure",
        cost_impact=Decimal("1000.00"),
    )
    wp = await service.create_work_package(create_data, actor_id=actor_id)
    await db_session.flush()

    root_id = wp.work_package_id

    update_data = WorkPackageUpdate(status="closed")
    updated = await service.update_work_package(root_id, update_data, actor_id=actor_id)
    await db_session.flush()

    assert updated.status == "closed"
    assert updated.work_package_id == root_id


@pytest.mark.asyncio
async def test_update_work_package_invalid_status_raises(
    db_session: AsyncSession,
    test_project,
    actor_id: tuple,
) -> None:
    """Invalid status raises ValidationError from Pydantic schema."""
    with pytest.raises(ValidationError, match="status"):
        WorkPackageUpdate(status="suspended")


# --- NEW: Type Filtering Tests ---


@pytest.mark.asyncio
async def test_get_work_packages_filter_by_type(
    db_session: AsyncSession,
    test_project,
    actor_id: tuple,
) -> None:
    """Create multiple types, verify filtering by package_type."""
    service = WorkPackageService(db_session)
    project_id = test_project.project_id

    # Create 2 quality_impact
    for i in range(2):
        data = WorkPackageCreate(
            name=f"QI-{i}",
            package_type="quality_impact",
            external_event_id=f"NCR-QI-{i}",
            project_id=project_id,
            coq_category="internal_failure",
            cost_impact=Decimal("3000.00"),
        )
        await service.create_work_package(data, actor_id=actor_id)

    # Create 3 site_visit
    for i in range(3):
        data = WorkPackageCreate(
            name=f"SV-{i}",
            package_type="site_visit",
            project_id=project_id,
            cost_impact=Decimal("1500.00"),
        )
        await service.create_work_package(data, actor_id=actor_id)
    await db_session.flush()

    # Filter by quality_impact
    qi_wps, qi_total = await service.get_work_packages(
        project_id, package_type="quality_impact"
    )
    assert qi_total == 2
    assert all(wp.package_type == "quality_impact" for wp in qi_wps)

    # Filter by site_visit
    sv_wps, sv_total = await service.get_work_packages(
        project_id, package_type="site_visit"
    )
    assert sv_total == 3
    assert all(wp.package_type == "site_visit" for wp in sv_wps)


# --- NEW: Non-quality Package CRUD Tests ---


@pytest.mark.asyncio
async def test_create_site_visit_no_quality_fields(
    db_session: AsyncSession,
    test_project,
    actor_id: tuple,
) -> None:
    """Create site_visit type without quality-specific fields succeeds."""
    service = WorkPackageService(db_session)

    data = WorkPackageCreate(
        name="Site Visit - Phase 1",
        package_type="site_visit",
        project_id=test_project.project_id,
        cost_impact=Decimal("2500.00"),
    )

    wp = await service.create_work_package(data, actor_id=actor_id)
    await db_session.flush()

    assert wp.work_package_id == data.work_package_id
    assert wp.name == "Site Visit - Phase 1"
    assert wp.package_type == "site_visit"
    assert wp.status == "open"
    assert wp.coq_category is None
    assert wp.schedule_impact_days is None
    assert wp.external_event_id is None


# --- NEW: COQ Filtering Tests ---


@pytest.mark.asyncio
async def test_coq_metrics_filters_by_quality_type_only(
    db_session: AsyncSession,
    test_entity_hierarchy,
    actor_id: tuple,
) -> None:
    """COQ metrics ignore non-quality packages."""
    service = WorkPackageService(db_session)
    hierarchy = test_entity_hierarchy
    project_id = hierarchy["project"].project_id
    ce_id = hierarchy["cost_element"].cost_element_id

    # Create a quality_impact package with allocation
    qi_data = WorkPackageCreate(
        name="COQ-ONLY-QI",
        package_type="quality_impact",
        external_event_id="NCR-COQ-ONLY",
        project_id=project_id,
        coq_category="internal_failure",
        cost_impact=Decimal("5000.00"),
        cost_allocations=[
            QualityCostAllocation(
                cost_element_id=ce_id, amount=Decimal("3000.00")
            ),
        ],
    )
    await service.create_work_package(qi_data, actor_id=actor_id)
    await db_session.flush()

    # Create a site_visit package (should be excluded from COQ)
    sv_data = WorkPackageCreate(
        name="COQ-SKIP-SV",
        package_type="site_visit",
        project_id=project_id,
        cost_impact=Decimal("9999.00"),
    )
    await service.create_work_package(sv_data, actor_id=actor_id)
    await db_session.flush()

    metrics = await service.get_coq_metrics(project_id)

    # Only quality_impact allocations counted
    assert metrics.total_coq == Decimal("3000.00")
    assert metrics.cpq == Decimal("3000.00")


@pytest.mark.asyncio
async def test_summary_excludes_non_quality_types(
    db_session: AsyncSession,
    test_project,
    actor_id: tuple,
) -> None:
    """Summary only includes quality_impact-typed packages."""
    service = WorkPackageService(db_session)
    project_id = test_project.project_id

    # Create a quality_impact package
    qi_data = WorkPackageCreate(
        name="SUM-QI",
        package_type="quality_impact",
        external_event_id="NCR-SUM-QI",
        project_id=project_id,
        coq_category="internal_failure",
        cost_impact=Decimal("5000.00"),
    )
    await service.create_work_package(qi_data, actor_id=actor_id)
    await db_session.flush()

    # Create a site_visit package
    sv_data = WorkPackageCreate(
        name="SUM-SV",
        package_type="site_visit",
        project_id=project_id,
        cost_impact=Decimal("9999.00"),
    )
    await service.create_work_package(sv_data, actor_id=actor_id)
    await db_session.flush()

    summary = await service.get_summary(project_id)

    # Only the quality_impact package counted
    assert summary.total_cost == Decimal("5000.00")
    assert summary.impact_count == 1


@pytest.mark.asyncio
async def test_cost_registration_links_via_work_package_id(
    db_session: AsyncSession,
    test_entity_hierarchy,
    actor_id: tuple,
) -> None:
    """CR.work_package_id references work package; allocations query works."""
    service = WorkPackageService(db_session)
    hierarchy = test_entity_hierarchy
    project_id = hierarchy["project"].project_id
    ce_id = hierarchy["cost_element"].cost_element_id

    data = WorkPackageCreate(
        name="FK-LINK-TEST",
        package_type="quality_impact",
        external_event_id="NCR-FK-001",
        project_id=project_id,
        coq_category="internal_failure",
        cost_impact=Decimal("4000.00"),
        cost_allocations=[
            QualityCostAllocation(
                cost_element_id=ce_id, amount=Decimal("2000.00")
            ),
        ],
    )

    wp = await service.create_work_package(data, actor_id=actor_id)
    await db_session.flush()

    # Verify CR links via work_package_id
    from sqlalchemy import select

    stmt = select(CostRegistration).where(
        CostRegistration.work_package_id == wp.work_package_id,
    )
    result = await db_session.execute(stmt)
    cr = result.scalar_one()
    assert cr.work_package_id == wp.work_package_id
    assert cr.amount == Decimal("2000.00")
