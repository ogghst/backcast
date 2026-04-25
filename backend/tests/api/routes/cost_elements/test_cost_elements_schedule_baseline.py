"""API tests for Cost Element Schedule Baseline nested endpoints.

Tests the new 1:1 relationship where schedule baselines are nested under cost elements.
"""

from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.api.dependencies.auth import (
    get_current_active_user,
    get_current_user,
)
from app.core.rbac import RBACServiceABC, get_rbac_service
from app.main import app
from app.models.domain.cost_element import CostElement
from app.models.domain.user import User

# Mock user for authentication
mock_admin_user = User(
    user_id=uuid4(),
    email="admin@example.com",
    is_active=True,
    role="admin",
    full_name="Admin User",
    hashed_password="hash",
    created_by=uuid4(),
)


def mock_get_current_user() -> User:
    return mock_admin_user


def mock_get_current_active_user() -> User:
    return mock_admin_user


class MockRBACService(RBACServiceABC):
    def has_role(self, user_role: str, required_roles: list[str]) -> bool:
        return True

    def has_permission(self, user_role: str, required_permission: str) -> bool:
        return True

    def get_user_permissions(self, user_role: str) -> list[str]:
        return [
            "cost-element-read",
            "cost-element-create",
            "cost-element-update",
            "cost-element-delete",
            "schedule-baseline-read",
            "schedule-baseline-create",
            "schedule-baseline-update",
            "schedule-baseline-delete",
        ]

    async def has_project_access(
        self,
        user_id,
        user_role: str,
        project_id,
        required_permission: str,
    ) -> bool:
        return True

    async def get_user_projects(self, user_id, user_role: str):
        return []

    async def get_project_role(self, user_id, project_id):
        return "admin"


def mock_get_rbac_service() -> MockRBACService:
    return MockRBACService()


@pytest.fixture(autouse=True)
def override_auth() -> Any:
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user
    app.dependency_overrides[get_rbac_service] = mock_get_rbac_service
    yield
    app.dependency_overrides = {}


@pytest_asyncio.fixture
async def setup_dependencies(client: AsyncClient) -> dict[str, Any]:
    """Setup dependencies: Project, WBE, Department, CostElementType."""
    # 1. Department
    dept_res = await client.post(
        "/api/v1/departments",
        json={"code": f"D-{uuid4().hex[:4].upper()}", "name": "Dept"},
    )
    dept_id = dept_res.json()["department_id"]

    # 2. Cost Element Type
    type_res = await client.post(
        "/api/v1/cost-element-types",
        json={
            "code": f"T-{uuid4().hex[:4].upper()}",
            "name": "Type",
            "department_id": dept_id,
        },
    )
    type_id = type_res.json()["cost_element_type_id"]

    # 3. Project
    proj_res = await client.post(
        "/api/v1/projects",
        json={"code": f"P-{uuid4().hex[:4].upper()}", "name": "Proj"},
    )
    proj_id = proj_res.json()["project_id"]

    # 4. WBE
    wbe_res = await client.post(
        "/api/v1/wbes",
        json={
            "code": f"W-{uuid4().hex[:4].upper()}",
            "name": "WBE",
            "project_id": proj_id,
        },
    )
    wbe_id = wbe_res.json()["wbe_id"]

    return {
        "department_id": dept_id,
        "cost_element_type_id": type_id,
        "project_id": proj_id,
        "wbe_id": wbe_id,
    }


@pytest_asyncio.fixture
async def test_cost_element_with_baseline(
    db_session, setup_dependencies
) -> CostElement:
    """Create a cost element with a schedule baseline for testing.

    Note: The baseline is auto-created by the cost element service,
    so we don't need to create it manually.
    """

    from app.services.cost_element_service import CostElementService
    from app.services.schedule_baseline_service import ScheduleBaselineService

    cost_element_service: CostElementService = CostElementService(
        db_session  # type: ignore[arg-type]
    )
    baseline_service: ScheduleBaselineService = ScheduleBaselineService(
        db_session  # type: ignore[arg-type]
    )

    # Get the dependency IDs
    deps = setup_dependencies
    wbe_id = deps["wbe_id"]
    cost_element_type_id = deps["cost_element_type_id"]

    # Create cost element (this auto-creates a baseline)
    from app.models.schemas.cost_element import CostElementCreate

    create_schema = CostElementCreate(
        cost_element_id=None,  # Auto-generated
        wbe_id=wbe_id,
        cost_element_type_id=cost_element_type_id,
        code="TEST-001",
        name="Test Cost Element",
        budget_amount=100000.00,
        branch="main",
        control_date=None,
    )

    cost_element = await cost_element_service.create_cost_element(
        element_in=create_schema,
        actor_id=mock_admin_user.user_id,
        branch="main",
    )

    # Get the auto-created baseline
    baseline = await baseline_service.get_for_cost_element(
        cost_element_id=cost_element.cost_element_id,
        branch="main",
    )

    await db_session.commit()
    await db_session.refresh(cost_element)

    # Attach baseline to cost element for test access
    cost_element.baseline = baseline  # type: ignore[attr-defined]

    return cost_element  # type: ignore[return-value]


class TestGetScheduleBaseline:
    """Tests for GET /api/v1/cost-elements/{id}/schedule-baseline."""

    @pytest.mark.asyncio
    async def test_get_schedule_baseline_returns_baseline(
        self,
        client: AsyncClient,
        test_cost_element_with_baseline: CostElement,
    ) -> None:
        """Test getting schedule baseline for a cost element."""
        cost_element_id = test_cost_element_with_baseline.cost_element_id

        response = await client.get(
            f"/api/v1/cost-elements/{cost_element_id}/schedule-baseline"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["schedule_baseline_id"] == str(
            test_cost_element_with_baseline.baseline.schedule_baseline_id  # type: ignore[attr-defined]
        )
        assert data["name"] == "Default Schedule"  # Auto-created baseline
        assert data["cost_element_id"] == str(cost_element_id)

    @pytest.mark.asyncio
    async def test_get_schedule_baseline_returns_404_when_missing(
        self,
        client: AsyncClient,
        db_session,
        setup_dependencies,
    ) -> None:
        """Test getting schedule baseline for cost element without one."""

        from app.services.cost_element_service import CostElementService
        from app.services.schedule_baseline_service import ScheduleBaselineService

        cost_element_service: CostElementService = CostElementService(
            db_session  # type: ignore[arg-type]
        )
        baseline_service: ScheduleBaselineService = ScheduleBaselineService(
            db_session  # type: ignore[arg-type]
        )

        # Create cost element (will auto-create baseline)
        deps = setup_dependencies
        from app.models.schemas.cost_element import CostElementCreate

        create_schema = CostElementCreate(
            cost_element_id=None,
            wbe_id=deps["wbe_id"],
            cost_element_type_id=deps["cost_element_type_id"],
            code="TEST-NO-BL",
            name="Test No Baseline",
            budget_amount=50000.00,
            branch="main",
            control_date=None,
        )

        cost_element = await cost_element_service.create_cost_element(
            element_in=create_schema,
            actor_id=mock_admin_user.user_id,
            branch="main",
        )
        await db_session.commit()

        # Delete the auto-created baseline
        baseline = await baseline_service.get_for_cost_element(
            cost_element_id=cost_element.cost_element_id,
            branch="main",
        )
        if baseline:
            await baseline_service.soft_delete(
                root_id=baseline.schedule_baseline_id,
                actor_id=mock_admin_user.user_id,
                branch="main",
            )
            await db_session.commit()

        response = await client.get(
            f"/api/v1/cost-elements/{cost_element.cost_element_id}/schedule-baseline"
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestCreateScheduleBaseline:
    """Tests for POST /api/v1/cost-elements/{id}/schedule-baseline."""

    @pytest.mark.asyncio
    async def test_create_schedule_baseline_success(
        self,
        client: AsyncClient,
        db_session,
        setup_dependencies,
    ) -> None:
        """Test creating schedule baseline for a cost element."""

        from app.services.cost_element_service import CostElementService
        from app.services.schedule_baseline_service import ScheduleBaselineService

        cost_element_service: CostElementService = CostElementService(
            db_session  # type: ignore[arg-type]
        )
        baseline_service: ScheduleBaselineService = ScheduleBaselineService(
            db_session  # type: ignore[arg-type]
        )

        # Create cost element (will auto-create baseline)
        deps = setup_dependencies
        from app.models.schemas.cost_element import CostElementCreate

        create_schema = CostElementCreate(
            cost_element_id=None,
            wbe_id=deps["wbe_id"],
            cost_element_type_id=deps["cost_element_type_id"],
            code="TEST-CREATE",
            name="Test Create Baseline",
            budget_amount=75000.00,
            branch="main",
            control_date=None,
        )

        cost_element = await cost_element_service.create_cost_element(
            element_in=create_schema,
            actor_id=mock_admin_user.user_id,
            branch="main",
        )
        await db_session.commit()

        # Delete the auto-created baseline so we can test creating a new one
        baseline = await baseline_service.get_for_cost_element(
            cost_element_id=cost_element.cost_element_id,
            branch="main",
        )
        if baseline:
            await baseline_service.soft_delete(
                root_id=baseline.schedule_baseline_id,
                actor_id=mock_admin_user.user_id,
                branch="main",
            )
            await db_session.commit()

        # Create baseline via API
        now = datetime.utcnow()
        baseline_data = {
            "name": "New Baseline",
            "start_date": now.isoformat(),
            "end_date": (now + timedelta(days=60)).isoformat(),
            "progression_type": "LINEAR",
            "description": "Test creation",
        }

        response = await client.post(
            f"/api/v1/cost-elements/{cost_element.cost_element_id}/schedule-baseline",
            json=baseline_data,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Baseline"
        assert data["cost_element_id"] == str(cost_element.cost_element_id)
        assert "schedule_baseline_id" in data

    @pytest.mark.asyncio
    async def test_create_duplicate_baseline_returns_400(
        self,
        client: AsyncClient,
        test_cost_element_with_baseline: CostElement,
    ) -> None:
        """Test creating duplicate baseline returns 400 error."""
        cost_element_id = test_cost_element_with_baseline.cost_element_id

        now = datetime.utcnow()
        baseline_data = {
            "name": "Duplicate Baseline",
            "start_date": now.isoformat(),
            "end_date": (now + timedelta(days=60)).isoformat(),
            "progression_type": "LINEAR",
        }

        response = await client.post(
            f"/api/v1/cost-elements/{cost_element_id}/schedule-baseline",
            json=baseline_data,
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()


class TestUpdateScheduleBaseline:
    """Tests for PUT /api/v1/cost-elements/{id}/schedule-baseline."""

    @pytest.mark.asyncio
    async def test_update_schedule_baseline_success(
        self,
        client: AsyncClient,
        test_cost_element_with_baseline: CostElement,
    ) -> None:
        """Test updating schedule baseline for a cost element."""
        cost_element_id = test_cost_element_with_baseline.cost_element_id
        baseline_id = test_cost_element_with_baseline.baseline.schedule_baseline_id  # type: ignore[attr-defined]

        now = datetime.utcnow()
        update_data = {
            "name": "Updated Baseline",
            "start_date": now.isoformat(),
            "end_date": (now + timedelta(days=120)).isoformat(),
            "progression_type": "GAUSSIAN",
            "description": "Updated description",
        }

        response = await client.put(
            f"/api/v1/cost-elements/{cost_element_id}/schedule-baseline/{baseline_id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Baseline"
        assert data["progression_type"] == "GAUSSIAN"
        assert data["description"] == "Updated description"

    @pytest.mark.asyncio
    async def test_update_baseline_partial_update(
        self,
        client: AsyncClient,
        test_cost_element_with_baseline: CostElement,
    ) -> None:
        """Test partial update of schedule baseline."""
        cost_element_id = test_cost_element_with_baseline.cost_element_id
        baseline_id = test_cost_element_with_baseline.baseline.schedule_baseline_id  # type: ignore[attr-defined]

        # Only update the name field
        update_data = {"name": "Partially Updated"}

        response = await client.put(
            f"/api/v1/cost-elements/{cost_element_id}/schedule-baseline/{baseline_id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Partially Updated"
        # Other fields should remain unchanged
        assert data["progression_type"] == "LINEAR"


class TestDeleteScheduleBaseline:
    """Tests for DELETE /api/v1/cost-elements/{id}/schedule-baseline."""

    @pytest.mark.asyncio
    async def test_delete_schedule_baseline_success(
        self,
        client: AsyncClient,
        test_cost_element_with_baseline: CostElement,
    ) -> None:
        """Test soft deleting schedule baseline."""
        cost_element_id = test_cost_element_with_baseline.cost_element_id
        baseline_id = test_cost_element_with_baseline.baseline.schedule_baseline_id  # type: ignore[attr-defined]

        response = await client.delete(
            f"/api/v1/cost-elements/{cost_element_id}/schedule-baseline/{baseline_id}"
        )

        assert response.status_code == 204

        # Verify baseline is deleted
        get_response = await client.get(
            f"/api/v1/cost-elements/{cost_element_id}/schedule-baseline"
        )
        assert get_response.status_code == 404


class TestBranchIsolation:
    """Tests for branch isolation in schedule baseline endpoints."""

    @pytest.mark.asyncio
    async def test_branch_isolation_get_baseline(
        self,
        client: AsyncClient,
        test_cost_element_with_baseline: CostElement,
        db_session,
    ) -> None:
        """Test that baseline queries are branch-isolated.

        This test verifies that:
        1. Each branch can have its own schedule baseline for a cost element
        2. Baselines are properly isolated by branch
        3. The API correctly uses the 1:1 relationship (cost_element.schedule_baseline_id)

        NOTE: This test creates a cost element in a different branch with a different baseline,
        demonstrating that baselines are branch-isolated.
        """
        from app.models.schemas.cost_element import CostElementCreate
        from app.services.cost_element_service import CostElementService
        from app.services.schedule_baseline_service import ScheduleBaselineService

        cost_element_service: CostElementService = CostElementService(
            db_session  # type: ignore[arg-type]
        )
        baseline_service: ScheduleBaselineService = ScheduleBaselineService(
            db_session  # type: ignore[arg-type]
        )

        # Get the original cost element's dependencies
        cost_element_id = test_cost_element_with_baseline.cost_element_id
        original_ce = await cost_element_service.get_by_id(
            cost_element_id, branch="main"
        )

        # Get baseline in main branch (auto-created)
        main_response = await client.get(
            f"/api/v1/cost-elements/{cost_element_id}/schedule-baseline?branch=main"
        )
        assert main_response.status_code == 200
        assert main_response.json()["name"] == "Default Schedule"  # Auto-created

        # Create a NEW cost element in the change-order branch
        # This simulates a change order scenario where we create a new version
        # We use the same code but a different root_id (as if it were a new cost element)
        # In a real scenario, this would be done via a change order workflow
        from uuid import uuid4

        new_ce_id = uuid4()
        create_schema = CostElementCreate(
            cost_element_id=new_ce_id,
            wbe_id=original_ce.wbe_id,
            cost_element_type_id=original_ce.cost_element_type_id,
            code=f"{original_ce.code}-CO1",  # Different code to avoid conflicts
            name=f"{original_ce.name} (Change Order 1)",
            budget_amount=original_ce.budget_amount,
            branch="change-order-1",
            control_date=None,
        )

        _ = await cost_element_service.create_cost_element(
            element_in=create_schema,
            actor_id=mock_admin_user.user_id,
            branch="change-order-1",
        )
        await db_session.commit()

        # Get the auto-created baseline (it will be auto-created when the cost element is created)
        baseline_co = await baseline_service.get_for_cost_element(
            cost_element_id=new_ce_id, branch="change-order-1"
        )
        assert baseline_co is not None
        assert baseline_co.name == "Default Schedule"

        # Update the baseline to have a custom name
        from app.models.schemas.schedule_baseline import ScheduleBaselineUpdate

        now = datetime.utcnow()
        _ = await baseline_service.update_schedule_baseline(
            root_id=baseline_co.schedule_baseline_id,
            baseline_in=ScheduleBaselineUpdate(
                name="Branch Baseline",
                start_date=now,
                end_date=now + timedelta(days=90),
                branch="change-order-1",
            ),
            actor_id=mock_admin_user.user_id,
        )
        await db_session.commit()

        # Get baseline in change-order branch
        branch_response = await client.get(
            f"/api/v1/cost-elements/{new_ce_id}/schedule-baseline?branch=change-order-1"
        )
        assert branch_response.status_code == 200
        assert branch_response.json()["name"] == "Branch Baseline"

        # Verify main branch still has original baseline
        main_response2 = await client.get(
            f"/api/v1/cost-elements/{cost_element_id}/schedule-baseline?branch=main"
        )
        assert main_response2.status_code == 200
        assert main_response2.json()["name"] == "Default Schedule"  # Unchanged
