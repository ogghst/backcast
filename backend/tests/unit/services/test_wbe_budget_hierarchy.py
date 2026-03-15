"""Tests for WBE budget calculation with full hierarchy.

Tests verify that budget_allocation includes cost elements from:
1. Direct cost elements on the WBE
2. Cost elements on all descendant WBEs (recursive)
"""

from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.cost_element_service import CostElementService
from app.services.cost_element_type_service import CostElementTypeService
from app.services.department import DepartmentService
from app.services.project import ProjectService
from app.services.wbe import WBEService


@pytest_asyncio.fixture
async def test_user_id():
    """Provide a test user ID for entity creation."""
    return uuid4()


@pytest_asyncio.fixture
async def wbe_service(db_session: AsyncSession) -> WBEService:
    """Provide WBEService instance."""
    return WBEService(db_session)


@pytest_asyncio.fixture
async def cost_element_service(db_session: AsyncSession) -> CostElementService:
    """Provide CostElementService instance."""
    return CostElementService(db_session)


@pytest_asyncio.fixture
async def cost_element_type_service(db_session: AsyncSession) -> CostElementTypeService:
    """Provide CostElementTypeService instance."""
    return CostElementTypeService(db_session)


@pytest_asyncio.fixture
async def department_service(db_session: AsyncSession) -> DepartmentService:
    """Provide DepartmentService instance."""
    return DepartmentService(db_session)


@pytest_asyncio.fixture
async def project_service(db_session: AsyncSession) -> ProjectService:
    """Provide ProjectService instance."""
    return ProjectService(db_session)


@pytest_asyncio.fixture
async def project_with_hierarchy(
    project_service: ProjectService,
    wbe_service: WBEService,
    cost_element_service: CostElementService,
    cost_element_type_service: CostElementTypeService,
    department_service: DepartmentService,
    test_user_id,
):
    """Create a project with a multi-level WBE hierarchy for testing.

    Structure:
    Project
    ├── WBE 1 (root WBE)
    │   ├── CostElement A (budget: 10,000)
    │   └── WBE 1.1 (child WBE)
    │       ├── CostElement B (budget: 20,000)
    │       └── WBE 1.1.1 (grandchild WBE)
    │           └── CostElement C (budget: 5,000)
    └── WBE 2 (root WBE)
        └── CostElement D (budget: 15,000)
    """
    # Create department
    department = await department_service.create_department(
        name="Test Department",
        code="TEST-DEPT",
        actor_id=test_user_id,
    )

    # Create cost element type
    cost_element_type = await cost_element_type_service.create(
        code="TEST-TYPE",
        name="Test Cost Element Type",
        department_id=department.department_id,
        actor_id=test_user_id,
    )

    # Create project
    project = await project_service.create_root(
        root_id=uuid4(),
        actor_id=test_user_id,
        name="Test Project",
        code="TEST-001",
        contract_value=Decimal("100000"),
        branch="main",
    )

    # Create WBE 1 (root level)
    wbe_1 = await wbe_service.create_root(
        root_id=uuid4(),
        actor_id=test_user_id,
        project_id=project.project_id,
        code="1",
        name="WBE 1",
        level=1,
        branch="main",
    )

    # Create CostElement A on WBE 1
    ce_a = await cost_element_service.create_root(
        root_id=uuid4(),
        actor_id=test_user_id,
        wbe_id=wbe_1.wbe_id,
        cost_element_type_id=cost_element_type.cost_element_type_id,
        code="CE-A",
        name="CostElement A",
        budget_amount=Decimal("10000"),
        branch="main",
    )

    # Create WBE 1.1 (child of WBE 1)
    wbe_1_1 = await wbe_service.create_root(
        root_id=uuid4(),
        actor_id=test_user_id,
        project_id=project.project_id,
        code="1.1",
        name="WBE 1.1",
        level=2,
        parent_wbe_id=wbe_1.wbe_id,
        branch="main",
    )

    # Create CostElement B on WBE 1.1
    ce_b = await cost_element_service.create_root(
        root_id=uuid4(),
        actor_id=test_user_id,
        wbe_id=wbe_1_1.wbe_id,
        cost_element_type_id=cost_element_type.cost_element_type_id,
        code="CE-B",
        name="CostElement B",
        budget_amount=Decimal("20000"),
        branch="main",
    )

    # Create WBE 1.1.1 (grandchild of WBE 1)
    wbe_1_1_1 = await wbe_service.create_root(
        root_id=uuid4(),
        actor_id=test_user_id,
        project_id=project.project_id,
        code="1.1.1",
        name="WBE 1.1.1",
        level=3,
        parent_wbe_id=wbe_1_1.wbe_id,
        branch="main",
    )

    # Create CostElement C on WBE 1.1.1
    ce_c = await cost_element_service.create_root(
        root_id=uuid4(),
        actor_id=test_user_id,
        wbe_id=wbe_1_1_1.wbe_id,
        cost_element_type_id=cost_element_type.cost_element_type_id,
        code="CE-C",
        name="CostElement C",
        budget_amount=Decimal("5000"),
        branch="main",
    )

    # Create WBE 2 (separate root WBE)
    wbe_2 = await wbe_service.create_root(
        root_id=uuid4(),
        actor_id=test_user_id,
        project_id=project.project_id,
        code="2",
        name="WBE 2",
        level=1,
        branch="main",
    )

    # Create CostElement D on WBE 2
    ce_d = await cost_element_service.create_root(
        root_id=uuid4(),
        actor_id=test_user_id,
        wbe_id=wbe_2.wbe_id,
        cost_element_type_id=cost_element_type.cost_element_type_id,
        code="CE-D",
        name="CostElement D",
        budget_amount=Decimal("15000"),
        branch="main",
    )

    return {
        "project": project,
        "wbe_1": wbe_1,
        "wbe_1_1": wbe_1_1,
        "wbe_1_1_1": wbe_1_1_1,
        "wbe_2": wbe_2,
        "ce_a": ce_a,
        "ce_b": ce_b,
        "ce_c": ce_c,
        "ce_d": ce_d,
        "cost_element_type": cost_element_type,
    }


@pytest.mark.asyncio
async def test_simple_hierarchy_budget(wbe_service: WBEService, project_with_hierarchy):
    """Test budget calculation with direct and child cost elements.

    WBE 1.1 has:
    - Direct CostElement B (20,000)
    - Child WBE 1.1.1 with CostElement C (5,000)

    Expected: WBE 1.1 budget = 25,000
    """
    wbe_1_1 = project_with_hierarchy["wbe_1_1"]

    budget = await wbe_service._compute_wbe_budget(wbe_1_1.wbe_id, branch="main")

    assert budget == Decimal("25000"), (
        f"WBE 1.1 budget should include direct (20,000) + child (5,000) = 25,000, "
        f"got {budget}"
    )


@pytest.mark.asyncio
async def test_deep_hierarchy_budget(wbe_service: WBEService, project_with_hierarchy):
    """Test budget calculation through 3 levels of hierarchy.

    WBE 1 has:
    - Direct CostElement A (10,000)
    - Child WBE 1.1 with CostElement B (20,000)
    - Grandchild WBE 1.1.1 with CostElement C (5,000)

    Expected: WBE 1 budget = 35,000 (all levels aggregated)
    """
    wbe_1 = project_with_hierarchy["wbe_1"]

    budget = await wbe_service._compute_wbe_budget(wbe_1.wbe_id, branch="main")

    assert budget == Decimal("35000"), (
        f"WBE 1 budget should include all hierarchy levels: "
        f"10,000 + 20,000 + 5,000 = 35,000, got {budget}"
    )


@pytest.mark.asyncio
async def test_branch_isolation(
    wbe_service: WBEService,
    cost_element_service: CostElementService,
    project_with_hierarchy,
    test_user_id,
):
    """Test that budget calculation respects branch isolation.

    Main branch should not include cost elements from change branches.
    """
    wbe_1 = project_with_hierarchy["wbe_1"]

    # Create a cost element on a different branch
    change_branch = "change-order-123"
    await cost_element_service.create_root(
        root_id=uuid4(),
        actor_id=test_user_id,
        wbe_id=wbe_1.wbe_id,
        name="CostElement on Change Branch",
        budget_amount=Decimal("50000"),
        branch=change_branch,
    )

    # Main branch budget should NOT include the change branch cost element
    main_budget = await wbe_service._compute_wbe_budget(wbe_1.wbe_id, branch="main")

    assert main_budget == Decimal("35000"), (
        f"Main branch budget should not include change branch costs, "
        f"expected 35,000, got {main_budget}"
    )

    # Change branch budget should include only its own cost element
    change_budget = await wbe_service._compute_wbe_budget(
        wbe_1.wbe_id, branch=change_branch
    )

    assert change_budget == Decimal("50000"), (
        f"Change branch budget should only include its cost element, "
        f"expected 50,000, got {change_budget}"
    )


@pytest.mark.asyncio
async def test_soft_deleted_descendants_excluded(
    wbe_service: WBEService,
    cost_element_service: CostElementService,
    project_with_hierarchy,
    test_user_id,
):
    """Test that soft-deleted WBEs and cost elements are excluded from budget."""
    wbe_1 = project_with_hierarchy["wbe_1"]
    wbe_1_1 = project_with_hierarchy["wbe_1_1"]

    # Soft delete child WBE 1.1
    await wbe_service.soft_delete(
        root_id=wbe_1_1.wbe_id, actor_id=test_user_id, branch="main"
    )

    # WBE 1 budget should only include direct cost element (10,000)
    # Deleted WBE 1.1 (20,000) and WBE 1.1.1 (5,000) should be excluded
    budget = await wbe_service._compute_wbe_budget(wbe_1.wbe_id, branch="main")

    assert budget == Decimal("10000"), (
        f"WBE 1 budget should exclude deleted descendants, "
        f"expected 10,000, got {budget}"
    )


@pytest.mark.asyncio
async def test_empty_hierarchy_budget(
    wbe_service: WBEService, project_with_hierarchy, test_user_id
):
    """Test that WBE with no cost elements returns 0 budget."""
    # Create a new empty WBE
    from uuid import uuid4

    new_wbe = await wbe_service.create_root(
        root_id=uuid4(),
        actor_id=test_user_id,
        project_id=project_with_hierarchy["project"].project_id,
        code="3",
        name="Empty WBE",
        level=1,
        branch="main",
    )

    budget = await wbe_service._compute_wbe_budget(new_wbe.wbe_id, branch="main")

    assert budget == Decimal("0"), f"Empty WBE should have 0 budget, got {budget}"


@pytest.mark.asyncio
async def test_wbe_with_only_descendants(
    wbe_service: WBEService,
    cost_element_service: CostElementService,
    project_with_hierarchy,
    test_user_id,
):
    """Test WBE that has no direct cost elements, only descendant cost elements."""
    # Create a new parent WBE with no direct cost elements
    from uuid import uuid4

    parent_wbe = await wbe_service.create_root(
        root_id=uuid4(),
        actor_id=test_user_id,
        project_id=project_with_hierarchy["project"].project_id,
        code="4",
        name="Parent with only descendants",
        level=1,
        branch="main",
    )

    # Create child WBE with cost element
    child_wbe = await wbe_service.create_root(
        root_id=uuid4(),
        actor_id=test_user_id,
        project_id=project_with_hierarchy["project"].project_id,
        code="4.1",
        name="Child WBE",
        level=2,
        parent_wbe_id=parent_wbe.wbe_id,
        branch="main",
    )

    await cost_element_service.create_root(
        root_id=uuid4(),
        actor_id=test_user_id,
        wbe_id=child_wbe.wbe_id,
        name="Child Cost Element",
        budget_amount=Decimal("30000"),
        branch="main",
    )

    # Parent WBE budget should include child's cost element
    budget = await wbe_service._compute_wbe_budget(parent_wbe.wbe_id, branch="main")

    assert budget == Decimal("30000"), (
        f"Parent WBE should include descendant budgets even with no direct cost elements, "
        f"expected 30,000, got {budget}"
    )


@pytest.mark.asyncio
async def test_get_as_of_includes_hierarchical_budget(
    wbe_service: WBEService, project_with_hierarchy
):
    """Test that get_as_of populates budget_allocation with hierarchical budget."""
    wbe_1 = project_with_hierarchy["wbe_1"]

    wbe = await wbe_service.get_as_of(wbe_1.wbe_id, branch="main")

    assert wbe is not None, "WBE should be found"
    assert wbe.budget_allocation == Decimal("35000"), (
        f"get_as_of should populate budget_allocation with hierarchical budget, "
        f"expected 35,000, got {wbe.budget_allocation}"
    )


@pytest.mark.asyncio
async def test_populate_computed_budgets_hierarchical(
    wbe_service: WBEService, project_with_hierarchy
):
    """Test that _populate_computed_budgets populates hierarchical budgets."""
    wbe_1 = project_with_hierarchy["wbe_1"]
    wbe_1_1 = project_with_hierarchy["wbe_1_1"]
    wbe_2 = project_with_hierarchy["wbe_2"]

    wbes = [wbe_1, wbe_1_1, wbe_2]
    populated_wbes = await wbe_service._populate_computed_budgets(wbes, branch="main")

    # WBE 1: 10,000 + 20,000 + 5,000 = 35,000
    assert populated_wbes[0].budget_allocation == Decimal("35000")

    # WBE 1.1: 20,000 + 5,000 = 25,000
    assert populated_wbes[1].budget_allocation == Decimal("25000")

    # WBE 2: 15,000
    assert populated_wbes[2].budget_allocation == Decimal("15000")
