"""Factory functions for creating test entities via service layer.

These factories use the BranchableService/TemporalService create methods
to produce properly versioned entities with correct TSTZRANGE values.
Use these in tests that need realistic EVCS entities.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.control_account import ControlAccount
from app.models.domain.cost_element import CostElement
from app.models.domain.cost_element_type import CostElementType
from app.models.domain.cost_event import CostEvent
from app.models.domain.cost_event_type import CostEventType
from app.models.domain.cost_registration import CostRegistration
from app.models.domain.organizational_unit import OrganizationalUnit
from app.models.domain.project import Project
from app.models.domain.wbs_element import WBSElement
from app.models.domain.work_package import WorkPackage


async def create_test_project(
    session: AsyncSession,
    actor_id: UUID,
    **kwargs: Any,
) -> Project:
    """Create a test project via direct DB insert."""
    from app.core.versioning.commands import CreateVersionCommand

    root_id = kwargs.pop("project_id", uuid4())
    defaults: dict[str, Any] = {
        "name": f"Project-{root_id.hex[:8]}",
        "code": f"P-{root_id.hex[:8].upper()}",
        "status": "active",
        "currency": "EUR",
        "contract_value": Decimal("1000000"),
    }
    defaults.update(kwargs)

    cmd = CreateVersionCommand(
        entity_class=Project,
        root_id=root_id,
        actor_id=actor_id,
        branch="main",
        **defaults,
    )
    return await cmd.execute(session)


async def create_test_wbs_element(
    session: AsyncSession,
    actor_id: UUID,
    project_id: UUID,
    **kwargs: Any,
) -> WBSElement:
    """Create a test WBS element under a project."""
    from app.core.versioning.commands import CreateVersionCommand

    root_id = kwargs.pop("wbs_element_id", uuid4())
    defaults: dict[str, Any] = {
        "project_id": project_id,
        "code": "1.0",
        "name": f"WBS-{root_id.hex[:8]}",
        "level": 1,
    }
    defaults.update(kwargs)

    cmd = CreateVersionCommand(
        entity_class=WBSElement,
        root_id=root_id,
        actor_id=actor_id,
        branch="main",
        **defaults,
    )
    return await cmd.execute(session)


async def create_test_org_unit(
    session: AsyncSession,
    actor_id: UUID,
    **kwargs: Any,
) -> OrganizationalUnit:
    """Create a test organizational unit."""
    from app.core.versioning.commands import CreateVersionCommand

    root_id = kwargs.pop("organizational_unit_id", uuid4())
    defaults: dict[str, Any] = {
        "code": f"OU-{root_id.hex[:8].upper()}",
        "name": f"OrgUnit-{root_id.hex[:8]}",
        "is_active": True,
    }
    defaults.update(kwargs)

    cmd = CreateVersionCommand(
        entity_class=OrganizationalUnit,
        root_id=root_id,
        actor_id=actor_id,
        branch="main",
        **defaults,
    )
    return await cmd.execute(session)


async def create_test_control_account(
    session: AsyncSession,
    actor_id: UUID,
    wbs_element_id: UUID,
    org_unit_id: UUID,
    **kwargs: Any,
) -> ControlAccount:
    """Create a test control account at WBS x OrgUnit intersection."""
    from app.core.versioning.commands import CreateVersionCommand

    root_id = kwargs.pop("control_account_id", uuid4())
    defaults: dict[str, Any] = {
        "wbs_element_id": wbs_element_id,
        "organizational_unit_id": org_unit_id,
        "name": f"CA-{root_id.hex[:8]}",
        "code": f"CA-{root_id.hex[:8].upper()}",
    }
    defaults.update(kwargs)

    cmd = CreateVersionCommand(
        entity_class=ControlAccount,
        root_id=root_id,
        actor_id=actor_id,
        branch="main",
        **defaults,
    )
    return await cmd.execute(session)


async def create_test_work_package(
    session: AsyncSession,
    actor_id: UUID,
    control_account_id: UUID,
    **kwargs: Any,
) -> WorkPackage:
    """Create a test work package under a control account."""
    from app.core.versioning.commands import CreateVersionCommand

    root_id = kwargs.pop("work_package_id", uuid4())
    defaults: dict[str, Any] = {
        "control_account_id": control_account_id,
        "name": f"WP-{root_id.hex[:8]}",
        "code": f"WP-{root_id.hex[:8].upper()}",
        "budget_amount": Decimal("50000"),
        "status": "open",
    }
    defaults.update(kwargs)

    cmd = CreateVersionCommand(
        entity_class=WorkPackage,
        root_id=root_id,
        actor_id=actor_id,
        branch="main",
        **defaults,
    )
    return await cmd.execute(session)


async def create_test_cost_element(
    session: AsyncSession,
    actor_id: UUID,
    work_package_id: UUID,
    cost_element_type_id: UUID,
    **kwargs: Any,
) -> CostElement:
    """Create a test cost element (EOC) under a work package."""
    from app.core.versioning.commands import CreateVersionCommand

    root_id = kwargs.pop("cost_element_id", uuid4())
    defaults: dict[str, Any] = {
        "work_package_id": work_package_id,
        "cost_element_type_id": cost_element_type_id,
        "amount": Decimal("25000"),
    }
    defaults.update(kwargs)

    cmd = CreateVersionCommand(
        entity_class=CostElement,
        root_id=root_id,
        actor_id=actor_id,
        **defaults,
    )
    return await cmd.execute(session)


async def create_test_cost_event_type(
    session: AsyncSession,
    actor_id: UUID,
    **kwargs: Any,
) -> CostEventType:
    """Create a test cost event type."""
    from app.core.versioning.commands import CreateVersionCommand

    root_id = kwargs.pop("cost_event_type_id", uuid4())
    defaults: dict[str, Any] = {
        "code": f"CET-{root_id.hex[:8].upper()}",
        "name": f"EventType-{root_id.hex[:8]}",
        "color": "blue",
        "is_quality": True,
    }
    defaults.update(kwargs)

    cmd = CreateVersionCommand(
        entity_class=CostEventType,
        root_id=root_id,
        actor_id=actor_id,
        **defaults,
    )
    return await cmd.execute(session)


async def create_test_cost_event(
    session: AsyncSession,
    actor_id: UUID,
    project_id: UUID,
    cost_event_type_id: UUID,
    **kwargs: Any,
) -> CostEvent:
    """Create a test cost event for a project."""
    from app.core.versioning.commands import CreateVersionCommand

    root_id = kwargs.pop("cost_event_id", uuid4())
    defaults: dict[str, Any] = {
        "project_id": project_id,
        "name": f"CostEvent-{root_id.hex[:8]}",
        "cost_event_type_id": cost_event_type_id,
        "status": "open",
        "coq_category": "internal_failure",
        "estimated_impact": Decimal("5000"),
    }
    defaults.update(kwargs)

    cmd = CreateVersionCommand(
        entity_class=CostEvent,
        root_id=root_id,
        actor_id=actor_id,
        **defaults,
    )
    return await cmd.execute(session)


async def create_test_cost_registration(
    session: AsyncSession,
    actor_id: UUID,
    cost_element_id: UUID,
    **kwargs: Any,
) -> CostRegistration:
    """Create a test cost registration against a cost element."""
    from app.core.versioning.commands import CreateVersionCommand

    root_id = kwargs.pop("cost_registration_id", uuid4())
    defaults: dict[str, Any] = {
        "cost_element_id": cost_element_id,
        "amount": Decimal("1000"),
        "registration_date": datetime.now(UTC),
    }
    defaults.update(kwargs)

    cmd = CreateVersionCommand(
        entity_class=CostRegistration,
        root_id=root_id,
        actor_id=actor_id,
        **defaults,
    )
    return await cmd.execute(session)


async def create_test_cost_element_type(
    session: AsyncSession,
    actor_id: UUID,
    org_unit_id: UUID,
    **kwargs: Any,
) -> CostElementType:
    """Create a test cost element type (EOC category)."""
    from app.core.versioning.commands import CreateVersionCommand

    root_id = kwargs.pop("cost_element_type_id", uuid4())
    defaults: dict[str, Any] = {
        "organizational_unit_id": org_unit_id,
        "code": f"EOC-{root_id.hex[:8].upper()}",
        "name": f"CostType-{root_id.hex[:8]}",
    }
    defaults.update(kwargs)

    cmd = CreateVersionCommand(
        entity_class=CostElementType,
        root_id=root_id,
        actor_id=actor_id,
        **defaults,
    )
    return await cmd.execute(session)


async def create_test_schedule_baseline(
    session: AsyncSession,
    actor_id: UUID,
    work_package_id: UUID,
    **kwargs: Any,
) -> Any:
    """Create a test schedule baseline for a work package."""
    from datetime import timedelta

    from app.core.versioning.commands import CreateVersionCommand
    from app.models.domain.schedule_baseline import ScheduleBaseline

    root_id = kwargs.pop("schedule_baseline_id", uuid4())
    now = datetime.now(UTC)
    defaults: dict[str, Any] = {
        "schedule_baseline_id": root_id,
        "name": f"Baseline-{root_id.hex[:8]}",
        "start_date": now - timedelta(days=30),
        "end_date": now + timedelta(days=60),
        "progression_type": "LINEAR",
        "branch": "main",
    }
    # Allow kwargs to override start_date and end_date explicitly
    if "start_date" in kwargs:
        defaults["start_date"] = kwargs.pop("start_date")
    if "end_date" in kwargs:
        defaults["end_date"] = kwargs.pop("end_date")
    if "progression_type" in kwargs:
        defaults["progression_type"] = kwargs.pop("progression_type")
    defaults.update(kwargs)

    cmd = CreateVersionCommand(
        entity_class=ScheduleBaseline,
        root_id=root_id,
        actor_id=actor_id,
        **defaults,
    )
    return await cmd.execute(session)


async def create_full_hierarchy(
    session: AsyncSession,
    actor_id: UUID,
    **kwargs: Any,
) -> dict[str, Any]:
    """Create the full ANSI-748 hierarchy and return all entities.

    Project -> WBSElement -> ControlAccount -> WorkPackage -> CostElement
                                                   ^
    OrganizationalUnit -----------------------------|

    Keyword Args:
        budget_amount: Override default WP budget (Decimal)
    """
    budget_amount = kwargs.pop("budget_amount", None)
    project = await create_test_project(session, actor_id)
    org_unit = await create_test_org_unit(session, actor_id)
    wbs = await create_test_wbs_element(session, actor_id, project.project_id)
    ca = await create_test_control_account(
        session, actor_id, wbs.wbs_element_id, org_unit.organizational_unit_id
    )
    wp_kwargs: dict[str, Any] = {}
    if budget_amount is not None:
        wp_kwargs["budget_amount"] = budget_amount
    wp = await create_test_work_package(
        session, actor_id, ca.control_account_id, **wp_kwargs
    )
    # CostEventType is used for CostEvents (quality tracking)
    cetype = await create_test_cost_event_type(session, actor_id)
    # CostElementType is needed for CostElements (EOC under WorkPackage)
    ce_type = await create_test_cost_element_type(
        session, actor_id, org_unit.organizational_unit_id
    )
    ce = await create_test_cost_element(
        session, actor_id, wp.work_package_id, ce_type.cost_element_type_id
    )
    return {
        "project": project,
        "org_unit": org_unit,
        "wbs": wbs,
        "ca": ca,
        "wp": wp,
        "cet": cetype,
        "ce_type": ce_type,
        "ce": ce,
    }


async def create_test_progress_entry(
    session: AsyncSession,
    actor_id: UUID,
    work_package_id: UUID,
    **kwargs: Any,
) -> Any:
    """Create a test progress entry for a work package."""
    from app.core.versioning.commands import CreateVersionCommand
    from app.models.domain.progress_entry import ProgressEntry

    root_id = kwargs.pop("progress_entry_id", uuid4())
    defaults: dict[str, Any] = {
        "work_package_id": work_package_id,
        "progress_percentage": Decimal("25.00"),
        "notes": "Test progress entry",
    }
    defaults.update(kwargs)

    cmd = CreateVersionCommand(
        entity_class=ProgressEntry,
        root_id=root_id,
        actor_id=actor_id,
        **defaults,
    )
    return await cmd.execute(session)
