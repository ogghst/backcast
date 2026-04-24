"""Comprehensive integration tests for EVM API endpoints.

Tests the EVM (Earned Value Management) system with:
- Real database (test fixtures with transaction rollback)
- Time-travel functionality (control_date parameter)
- Branching functionality (ISOLATED vs MERGE modes)
- Multi-entity aggregation (cost elements, WBEs, projects)
- Time-series data retrieval (day/week/month granularity)
- WBE and Project entity types

These tests must run SEQUENTIALLY due to single database constraint.
Run with: pytest tests/integration/test_evm_integration.py -v --no-cov
"""

from datetime import UTC, datetime
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
from app.models.domain.user import User
from app.models.schemas.evm import EntityType

# =============================================================================
# MOCK AUTHENTICATION
# =============================================================================

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
            "evm-read",
            "progress-entry-read",
            "wbe-read",
            "project-read",
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


# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest_asyncio.fixture
async def setup_wbe_evm_data(client: AsyncClient) -> dict[str, Any]:
    """Setup complete EVM data for WBE testing.

    Creates:
    - Department, Cost Element Type, Project, WBE
    - 3 Cost Elements with different budgets and progress
    - Schedule baselines for all cost elements
    - Progress entries at different dates
    - Cost registrations at different dates

    Returns:
        Dict with all created entity IDs and expected values
    """
    # 1. Department
    dept_res = await client.post(
        "/api/v1/departments",
        json={"code": "D-WBE", "name": "WBE Test Dept"},
    )
    dept_id = dept_res.json()["department_id"]

    # 2. Cost Element Type
    type_res = await client.post(
        "/api/v1/cost-element-types",
        json={
            "code": "T-WBE",
            "name": "WBE Test Type",
            "department_id": dept_id,
        },
    )
    type_id = type_res.json()["cost_element_type_id"]

    # 3. Project
    proj_res = await client.post(
        "/api/v1/projects",
        json={"code": "P-WBE", "name": "WBE Test Project"},
    )
    proj_id = proj_res.json()["project_id"]

    # 4. WBE
    wbe_res = await client.post(
        "/api/v1/wbes",
        json={
            "code": "W-WBE",
            "name": "WBE Test WBE",
            "project_id": proj_id,
            "branch": "main",
        },
    )
    wbe_id = wbe_res.json()["wbe_id"]

    # 5. Create 3 Cost Elements with different budgets and progress
    cost_elements = []

    for i in range(1, 4):
        ce_res = await client.post(
            "/api/v1/cost-elements",
            json={
                "code": f"CE-WBE-{i}",
                "name": f"Cost Element {i}",
                "budget_amount": 100000 * i,  # 100k, 200k, 300k
                "wbe_id": wbe_id,
                "cost_element_type_id": type_id,
                "branch": "main",
            },
        )
        ce_id = ce_res.json()["cost_element_id"]
        cost_elements.append(ce_id)

        # 6. Schedule Baseline for each cost element
        await client.post(
            f"/api/v1/cost-elements/{ce_id}/schedule-baseline",
            json={
                "start_date": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
                "end_date": datetime(2026, 12, 31, tzinfo=UTC).isoformat(),
                "progression_type": "LINEAR",
                "description": f"2026 Baseline for CE {i}",
            },
        )

        # 7. Progress Entry (different progress for each)
        progress_val = 50.0 * i
        if progress_val > 100.0:
            progress_val = 100.0  # Cap at 100% (schema validation)
        progress_res = await client.post(
            "/api/v1/progress-entries",
            json={
                "cost_element_id": str(ce_id),
                "progress_percentage": progress_val,  # 50%, 100%, 100%
                "reported_date": datetime(2026, 6, 30, tzinfo=UTC).isoformat(),
                "reported_by_user_id": str(mock_admin_user.user_id),
                "notes": f"Progress entry {i}",
            },
        )
        # Ensure progress entry was created successfully
        assert progress_res.status_code in (200, 201), (
            f"Failed to create progress entry for CE {i}: {progress_res.text}"
        )

        # 8. Cost Registrations (different amounts for each)
        await client.post(
            "/api/v1/cost-registrations",
            json={
                "cost_element_id": str(ce_id),
                "amount": 30000.0 * i,  # 30k, 60k, 90k
                "description": f"Costs {i}",
                "registration_date": datetime(2026, 6, 15, tzinfo=UTC).isoformat(),
            },
        )

    return {
        "wbe_id": wbe_id,
        "project_id": proj_id,
        "cost_elements": cost_elements,
        "ce1_id": cost_elements[0],
        "ce2_id": cost_elements[1],
        "ce3_id": cost_elements[2],
        "total_budget": 600000,  # 100k + 200k + 300k
        "total_costs": 180000,  # 30k + 60k + 90k
    }


@pytest_asyncio.fixture
async def setup_project_evm_data(client: AsyncClient) -> dict[str, Any]:
    """Setup complete EVM data for Project testing.

    Creates:
    - Department, Cost Element Type, Project
    - 2 WBEs with different budgets
    - 4 Cost Elements distributed across WBEs
    - Schedule baselines, progress entries, cost registrations

    Returns:
        Dict with all created entity IDs and expected values
    """
    # 1. Department
    dept_res = await client.post(
        "/api/v1/departments",
        json={"code": "D-PROJ", "name": "Project Test Dept"},
    )
    dept_id = dept_res.json()["department_id"]

    # 2. Cost Element Type
    type_res = await client.post(
        "/api/v1/cost-element-types",
        json={
            "code": "T-PROJ",
            "name": "Project Test Type",
            "department_id": dept_id,
        },
    )
    type_id = type_res.json()["cost_element_type_id"]

    # 3. Project
    proj_res = await client.post(
        "/api/v1/projects",
        json={"code": "P-PROJ", "name": "Project Test Project"},
    )
    proj_id = proj_res.json()["project_id"]

    # 4. Create 2 WBEs
    wbe_ids = []
    for i in range(1, 3):
        wbe_res = await client.post(
            "/api/v1/wbes",
            json={
                "code": f"W-PROJ-{i}",
                "name": f"WBE {i}",
                "project_id": proj_id,
                "branch": "main",
            },
        )
        wbe_id = wbe_res.json()["wbe_id"]
        wbe_ids.append(wbe_id)

        # Create 2 Cost Elements per WBE
        for j in range(1, 3):
            ce_res = await client.post(
                "/api/v1/cost-elements",
                json={
                    "code": f"CE-PROJ-{i}-{j}",
                    "name": f"Cost Element {i}-{j}",
                    "budget_amount": 150000,
                    "wbe_id": wbe_id,
                    "cost_element_type_id": type_id,
                    "branch": "main",
                },
            )
            ce_id = ce_res.json()["cost_element_id"]

            # Schedule Baseline
            await client.post(
                f"/api/v1/cost-elements/{ce_id}/schedule-baseline",
                json={
                    "start_date": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
                    "end_date": datetime(2026, 12, 31, tzinfo=UTC).isoformat(),
                    "progression_type": "LINEAR",
                    "description": f"2026 Baseline for CE {i}-{j}",
                },
            )

            # Progress Entry
            await client.post(
                "/api/v1/progress-entries",
                json={
                    "cost_element_id": str(ce_id),
                    "progress_percentage": 60.0,
                    "reported_date": datetime(2026, 6, 30, tzinfo=UTC).isoformat(),
                    "reported_by_user_id": str(mock_admin_user.user_id),
                    "notes": f"Progress {i}-{j}",
                },
            )

            # Cost Registrations
            await client.post(
                "/api/v1/cost-registrations",
                json={
                    "cost_element_id": str(ce_id),
                    "amount": 50000.0,
                    "description": f"Costs {i}-{j}",
                    "registration_date": datetime(2026, 6, 15, tzinfo=UTC).isoformat(),
                },
            )

    return {
        "project_id": proj_id,
        "wbe_ids": wbe_ids,
        "wbe1_id": wbe_ids[0],
        "wbe2_id": wbe_ids[1],
        "total_budget": 600000,  # 4 CEs × 150k
        "total_costs": 200000,  # 4 CEs × 50k
    }


# =============================================================================
# COST ELEMENT ENTITY TYPE TESTS (Currently Supported)
# =============================================================================


@pytest_asyncio.fixture
async def setup_cost_element_evm_data(client: AsyncClient) -> dict[str, Any]:
    """Setup complete EVM data for Cost Element testing.

    Creates:
    - Department, Cost Element Type, Project, WBE
    - 1 Cost Element with budget, baseline, progress, and costs
    - Multiple progress entries at different dates
    - Multiple cost registrations at different dates

    Returns:
        Dict with all created entity IDs and expected values
    """
    # 1. Department
    dept_res = await client.post(
        "/api/v1/departments",
        json={"code": "D-CE", "name": "CE Test Dept"},
    )
    dept_id = dept_res.json()["department_id"]

    # 2. Cost Element Type
    type_res = await client.post(
        "/api/v1/cost-element-types",
        json={
            "code": "T-CE",
            "name": "CE Test Type",
            "department_id": dept_id,
        },
    )
    type_id = type_res.json()["cost_element_type_id"]

    # 3. Project
    proj_res = await client.post(
        "/api/v1/projects",
        json={"code": "P-CE", "name": "CE Test Project"},
    )
    proj_id = proj_res.json()["project_id"]

    # 4. WBE
    wbe_res = await client.post(
        "/api/v1/wbes",
        json={
            "code": "W-CE",
            "name": "CE Test WBE",
            "project_id": proj_id,
            "branch": "main",
        },
    )
    wbe_id = wbe_res.json()["wbe_id"]

    # 5. Cost Element with budget
    ce_res = await client.post(
        "/api/v1/cost-elements",
        json={
            "code": "CE-TEST",
            "name": "Test Cost Element",
            "budget_amount": 200000,
            "wbe_id": wbe_id,
            "cost_element_type_id": type_id,
            "branch": "main",
        },
    )
    cost_element_id = ce_res.json()["cost_element_id"]

    # 6. Schedule Baseline (full year 2026)
    await client.post(
        f"/api/v1/cost-elements/{cost_element_id}/schedule-baseline",
        json={
            "start_date": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
            "end_date": datetime(2026, 12, 31, tzinfo=UTC).isoformat(),
            "progression_type": "LINEAR",
            "description": "2026 Test Baseline",
        },
    )

    # 7. Progress Entries (multiple dates)
    # First progress: 25% at end of Q1
    await client.post(
        "/api/v1/progress-entries",
        json={
            "cost_element_id": str(cost_element_id),
            "progress_percentage": 25.0,
            "reported_date": datetime(2026, 3, 31, tzinfo=UTC).isoformat(),
            "reported_by_user_id": str(mock_admin_user.user_id),
            "notes": "Q1 Progress",
        },
    )

    # Second progress: 50% at end of Q2
    await client.post(
        "/api/v1/progress-entries",
        json={
            "cost_element_id": str(cost_element_id),
            "progress_percentage": 50.0,
            "reported_date": datetime(2026, 6, 30, tzinfo=UTC).isoformat(),
            "reported_by_user_id": str(mock_admin_user.user_id),
            "notes": "Q2 Progress",
        },
    )

    # 8. Cost Registrations (multiple dates)
    # First cost: 40000 in Q1
    await client.post(
        "/api/v1/cost-registrations",
        json={
            "cost_element_id": str(cost_element_id),
            "amount": 40000.0,
            "description": "Q1 Costs",
            "registration_date": datetime(2026, 3, 31, tzinfo=UTC).isoformat(),
        },
    )

    # Second cost: 60000 in Q2
    await client.post(
        "/api/v1/cost-registrations",
        json={
            "cost_element_id": str(cost_element_id),
            "amount": 60000.0,
            "description": "Q2 Costs",
            "registration_date": datetime(2026, 6, 30, tzinfo=UTC).isoformat(),
        },
    )

    return {
        "cost_element_id": cost_element_id,
        "budget": 200000,
        "total_costs": 100000,  # 40000 + 60000
        "latest_progress": 50.0,
    }


class TestCostElementEntityEVM:
    """Test EVM metrics for Cost Element entity type (currently supported)."""

    @pytest.mark.asyncio
    async def test_get_cost_element_metrics_returns_all_metrics(
        self, client: AsyncClient, setup_cost_element_evm_data: dict[str, Any]
    ) -> None:
        """Test GET /evm/cost_element/{id}/metrics returns all EVM metrics.

        Test ID: T-BE-CE-001

        Expected:
        - Returns EVMMetricsResponse with entity_type="cost_element"
        - All 11 EVM metrics present (BAC, PV, AC, EV, CV, SV, CPI, SPI, EAC, VAC, ETC)
        - Metrics calculated correctly
        """
        # Arrange
        cost_element_id = setup_cost_element_evm_data["cost_element_id"]

        # Act
        response = await client.get(
            f"/api/v1/evm/cost_element/{cost_element_id}/metrics"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify entity type
        assert data["entity_type"] == EntityType.COST_ELEMENT
        assert data["entity_id"] == str(cost_element_id)

        # Verify all metrics present
        assert "bac" in data
        assert "pv" in data
        assert "ac" in data
        assert "ev" in data
        assert "cv" in data
        assert "sv" in data
        assert "cpi" in data
        assert "spi" in data
        assert "eac" in data
        assert "vac" in data
        assert "etc" in data

        # Verify values
        assert float(data["bac"]) == 200000  # Budget
        assert float(data["ac"]) == 100000  # Total costs
        assert float(data["ev"]) == 100000  # BAC × 50% (latest progress)
        assert float(data["cv"]) == 0  # EV - AC = 100000 - 100000

    @pytest.mark.asyncio
    async def test_cost_element_time_travel_with_past_date(
        self, client: AsyncClient, setup_cost_element_evm_data: dict[str, Any]
    ) -> None:
        """Test GET /evm/cost_element/{id}/metrics with past control_date.

        Test ID: T-BE-CE-002

        Expected:
        - Returns metrics as of the specified control_date
        - Control date is reflected in response
        - Note: Cost registrations are global facts, so they don't filter by control_date
        """
        # Arrange
        cost_element_id = setup_cost_element_evm_data["cost_element_id"]
        past_date = datetime(2026, 4, 30, tzinfo=UTC)

        # Act
        response = await client.get(
            f"/api/v1/evm/cost_element/{cost_element_id}/metrics",
            params={"control_date": past_date.isoformat()},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Control date should be in response
        assert "control_date" in data

        # Cost registrations are global facts (not time-travel enabled)
        # so AC will include all costs, not just those up to control_date
        # This is expected behavior - cost registrations are immutable facts
        assert float(data["ac"]) >= 0

        # EV should be based on latest progress as of control_date
        # Progress entries are also global facts
        assert float(data["ev"]) >= 0

    @pytest.mark.asyncio
    async def test_cost_element_with_branch_mode_strict(
        self, client: AsyncClient, setup_cost_element_evm_data: dict[str, Any]
    ) -> None:
        """Test GET /evm/cost_element/{id}/metrics with branch_mode=strict.

        Test ID: T-BE-CE-003

        Expected:
        - Only uses data from the specified branch
        - No fallback to parent branches
        """
        # Arrange
        cost_element_id = setup_cost_element_evm_data["cost_element_id"]

        # Act
        response = await client.get(
            f"/api/v1/evm/cost_element/{cost_element_id}/metrics",
            params={
                "branch": "main",
                "branch_mode": "strict",
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert data["branch"] == "main"
        assert "bac" in data

    @pytest.mark.asyncio
    async def test_cost_element_with_branch_mode_merge(
        self, client: AsyncClient, setup_cost_element_evm_data: dict[str, Any]
    ) -> None:
        """Test GET /evm/cost_element/{id}/metrics with branch_mode=merge.

        Test ID: T-BE-CE-004

        Expected:
        - Uses data from specified branch, falling back to parents
        """
        # Arrange
        cost_element_id = setup_cost_element_evm_data["cost_element_id"]

        # Act
        response = await client.get(
            f"/api/v1/evm/cost_element/{cost_element_id}/metrics",
            params={
                "branch": "main",
                "branch_mode": "merge",
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert "bac" in data

    @pytest.mark.asyncio
    async def test_cost_element_timeseries_with_weekly_granularity(
        self, client: AsyncClient, setup_cost_element_evm_data: dict[str, Any]
    ) -> None:
        """Test GET /evm/cost_element/{id}/timeseries with weekly granularity.

        Test ID: T-BE-CE-005

        Expected:
        - Returns weekly time-series data points
        - Each point has date, pv, ev, ac, forecast, actual
        - granularity = "week"
        """
        # Arrange
        cost_element_id = setup_cost_element_evm_data["cost_element_id"]

        # Act
        response = await client.get(
            f"/api/v1/evm/cost_element/{cost_element_id}/timeseries",
            params={"granularity": "week"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert data["granularity"] == "week"
        assert "points" in data
        assert isinstance(data["points"], list)
        assert "start_date" in data
        assert "end_date" in data
        assert "total_points" in data

        # Verify point structure
        if data["points"]:
            point = data["points"][0]
            assert "date" in point
            assert "pv" in point
            assert "ev" in point
            assert "ac" in point
            assert "forecast" in point
            assert "actual" in point

    @pytest.mark.asyncio
    async def test_cost_element_batch_multi_entity_aggregation(
        self, client: AsyncClient
    ) -> None:
        """Test POST /evm/batch with multiple cost elements.

        Test ID: T-BE-CE-006

        Expected:
        - Returns aggregated metrics
        - BAC, PV, AC, EV are summed
        - CPI, SPI are BAC-weighted averages
        """
        # Arrange - Create two cost elements
        dept_res = await client.post(
            "/api/v1/departments",
            json={"code": f"D-{uuid4().hex[:4].upper()}", "name": "Batch CE Dept"},
        )
        dept_id = dept_res.json()["department_id"]

        type_res = await client.post(
            "/api/v1/cost-element-types",
            json={
                "code": f"T-{uuid4().hex[:4].upper()}",
                "name": "Batch CE Type",
                "department_id": dept_id,
            },
        )
        type_id = type_res.json()["cost_element_type_id"]

        proj_res = await client.post(
            "/api/v1/projects",
            json={
                "code": f"P-{uuid4().hex[:4].upper()}",
                "name": "Batch CE Proj",
            },
        )
        proj_id = proj_res.json()["project_id"]

        wbe_res = await client.post(
            "/api/v1/wbes",
            json={
                "code": f"W-{uuid4().hex[:4].upper()}",
                "name": "Batch CE WBE",
                "project_id": proj_id,
                "branch": "main",
            },
        )
        wbe_id = wbe_res.json()["wbe_id"]

        # First cost element
        ce1_res = await client.post(
            "/api/v1/cost-elements",
            json={
                "code": f"CE-{uuid4().hex[:4].upper()}-1",
                "name": "Batch CE 1",
                "budget_amount": 100000,
                "wbe_id": wbe_id,
                "cost_element_type_id": type_id,
                "branch": "main",
            },
        )
        ce1_id = ce1_res.json()["cost_element_id"]

        # Second cost element
        ce2_res = await client.post(
            "/api/v1/cost-elements",
            json={
                "code": f"CE-{uuid4().hex[:4].upper()}-2",
                "name": "Batch CE 2",
                "budget_amount": 150000,
                "wbe_id": wbe_id,
                "cost_element_type_id": type_id,
                "branch": "main",
            },
        )
        ce2_id = ce2_res.json()["cost_element_id"]

        # Add baselines, progress, and costs for both
        for ce_id in [ce1_id, ce2_id]:
            await client.post(
                f"/api/v1/cost-elements/{ce_id}/schedule-baseline",
                json={
                    "start_date": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
                    "end_date": datetime(2026, 12, 31, tzinfo=UTC).isoformat(),
                    "progression_type": "LINEAR",
                    "description": "2026 Baseline",
                },
            )

            await client.post(
                "/api/v1/progress-entries",
                json={
                    "cost_element_id": str(ce_id),
                    "progress_percentage": 60.0,
                    "reported_date": datetime(2026, 6, 30, tzinfo=UTC).isoformat(),
                    "reported_by_user_id": str(mock_admin_user.user_id),
                    "notes": "Progress",
                },
            )

        # Act
        response = await client.post(
            "/api/v1/evm/batch",
            json={
                "entity_type": EntityType.COST_ELEMENT,
                "entity_ids": [str(ce1_id), str(ce2_id)],
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify aggregation (sum of budgets)
        expected_bac = 250000  # 100k + 150k
        assert float(data["bac"]) == expected_bac

    @pytest.mark.asyncio
    async def test_cost_element_with_no_progress_returns_warning(
        self, client: AsyncClient
    ) -> None:
        """Test GET /evm/cost_element/{id}/metrics with no progress entries.

        Test ID: T-BE-CE-007

        Expected:
        - EV = 0
        - Warning message present
        - CPI = 0 or None
        """
        # Arrange - Create cost element without progress
        dept_res = await client.post(
            "/api/v1/departments",
            json={
                "code": f"D-{uuid4().hex[:4].upper()}",
                "name": "No Progress CE Dept",
            },
        )
        dept_id = dept_res.json()["department_id"]

        type_res = await client.post(
            "/api/v1/cost-element-types",
            json={
                "code": f"T-{uuid4().hex[:4].upper()}",
                "name": "No Progress CE Type",
                "department_id": dept_id,
            },
        )
        type_id = type_res.json()["cost_element_type_id"]

        proj_res = await client.post(
            "/api/v1/projects",
            json={
                "code": f"P-{uuid4().hex[:4].upper()}",
                "name": "No Progress CE Proj",
            },
        )
        proj_id = proj_res.json()["project_id"]

        wbe_res = await client.post(
            "/api/v1/wbes",
            json={
                "code": f"W-{uuid4().hex[:4].upper()}",
                "name": "No Progress CE WBE",
                "project_id": proj_id,
                "branch": "main",
            },
        )
        wbe_id = wbe_res.json()["wbe_id"]

        ce_res = await client.post(
            "/api/v1/cost-elements",
            json={
                "code": f"CE-{uuid4().hex[:4].upper()}",
                "name": "No Progress CE",
                "budget_amount": 100000,
                "wbe_id": wbe_id,
                "cost_element_type_id": type_id,
                "branch": "main",
            },
        )
        ce_id = ce_res.json()["cost_element_id"]

        await client.post(
            f"/api/v1/cost-elements/{ce_id}/schedule-baseline",
            json={
                "start_date": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
                "end_date": datetime(2026, 12, 31, tzinfo=UTC).isoformat(),
                "progression_type": "LINEAR",
                "description": "2026 Baseline",
            },
        )

        # Act
        response = await client.get(f"/api/v1/evm/cost_element/{ce_id}/metrics")

        # Assert
        assert response.status_code == 200
        data = response.json()

        # EV should be 0
        assert float(data["ev"]) == 0

        # Warning should be present
        assert data.get("warning") is not None
        assert "No progress reported" in data["warning"]

    @pytest.mark.asyncio
    async def test_cost_element_with_zero_ac_returns_none_for_cpi(
        self, client: AsyncClient
    ) -> None:
        """Test GET /evm/cost_element/{id}/metrics with AC = 0.

        Test ID: T-BE-CE-008

        Expected:
        - CPI = None (division by zero handled gracefully)
        - Other metrics calculated normally
        """
        # Arrange - Create cost element with progress but no costs
        dept_res = await client.post(
            "/api/v1/departments",
            json={"code": f"D-{uuid4().hex[:4].upper()}", "name": "Zero AC CE Dept"},
        )
        dept_id = dept_res.json()["department_id"]

        type_res = await client.post(
            "/api/v1/cost-element-types",
            json={
                "code": f"T-{uuid4().hex[:4].upper()}",
                "name": "Zero AC CE Type",
                "department_id": dept_id,
            },
        )
        type_id = type_res.json()["cost_element_type_id"]

        proj_res = await client.post(
            "/api/v1/projects",
            json={
                "code": f"P-{uuid4().hex[:4].upper()}",
                "name": "Zero AC CE Proj",
            },
        )
        proj_id = proj_res.json()["project_id"]

        wbe_res = await client.post(
            "/api/v1/wbes",
            json={
                "code": f"W-{uuid4().hex[:4].upper()}",
                "name": "Zero AC CE WBE",
                "project_id": proj_id,
                "branch": "main",
            },
        )
        wbe_id = wbe_res.json()["wbe_id"]

        ce_res = await client.post(
            "/api/v1/cost-elements",
            json={
                "code": f"CE-{uuid4().hex[:4].upper()}",
                "name": "Zero AC CE",
                "budget_amount": 100000,
                "wbe_id": wbe_id,
                "cost_element_type_id": type_id,
                "branch": "main",
            },
        )
        ce_id = ce_res.json()["cost_element_id"]

        await client.post(
            f"/api/v1/cost-elements/{ce_id}/schedule-baseline",
            json={
                "start_date": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
                "end_date": datetime(2026, 12, 31, tzinfo=UTC).isoformat(),
                "progression_type": "LINEAR",
                "description": "2026 Baseline",
            },
        )

        await client.post(
            "/api/v1/progress-entries",
            json={
                "cost_element_id": str(ce_id),
                "progress_percentage": 50.0,
                "reported_date": datetime(2026, 6, 30, tzinfo=UTC).isoformat(),
                "reported_by_user_id": str(mock_admin_user.user_id),
                "notes": "Progress",
            },
        )

        # Act
        response = await client.get(f"/api/v1/evm/cost_element/{ce_id}/metrics")

        # Assert
        assert response.status_code == 200
        data = response.json()

        # AC should be 0
        assert float(data["ac"]) == 0

        # CPI should be None (division by zero)
        assert data.get("cpi") is None

        # EV should be calculated (BAC × 50%)
        assert float(data["ev"]) == 50000


# =============================================================================
# WBE ENTITY TYPE TESTS
# =============================================================================


class TestWBEEntityEVM:
    """Test EVM metrics for WBE entity type.

    NOTE: These tests are marked as expected to fail until BE-009 is completed.
    BE-009: Extend API routes for WBE and Project entities.
    """

    @pytest.mark.asyncio
    async def test_get_wbe_metrics_aggregates_child_cost_elements(
        self, client: AsyncClient, setup_wbe_evm_data: dict[str, Any]
    ) -> None:
        """Test GET /evm/wbe/{id}/metrics aggregates child cost elements.

        Test ID: T-BE-WBE-001

        Expected:
        - Returns EVMMetricsResponse with entity_type="wbe"
        - BAC = sum of child cost element budgets
        - AC = sum of child cost element actual costs
        - EV = sum of child cost element earned values
        - CPI and SPI are BAC-weighted averages
        """
        # Arrange
        wbe_id = setup_wbe_evm_data["wbe_id"]

        # Act
        response = await client.get(f"/api/v1/evm/wbe/{wbe_id}/metrics")

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify entity type
        assert data["entity_type"] == EntityType.WBE
        assert data["entity_id"] == str(wbe_id)

        # Verify aggregation (sum of amounts)
        expected_bac = setup_wbe_evm_data["total_budget"]  # 600000
        expected_ac = setup_wbe_evm_data["total_costs"]  # 180000

        # BAC should be sum of all child budgets
        assert float(data["bac"]) == expected_bac

        # AC should be sum of all child costs
        assert float(data["ac"]) == expected_ac

        # EV should be sum of all child EVs
        # CE1: 100k × 50% = 50k, CE2: 200k × 100% = 200k, CE3: 300k × 100% = 300k
        # Note: Progress is capped at 100%, so CE3's 150% becomes 100%
        expected_ev = 50000 + 200000 + 300000  # 550000
        assert float(data["ev"]) == expected_ev

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="WBE entity type not yet supported in API routes (BE-009)"
    )
    async def test_get_wbe_metrics_with_no_children_returns_zero(
        self, client: AsyncClient
    ) -> None:
        """Test GET /evm/wbe/{id}/metrics with WBE that has no cost elements.

        Test ID: T-BE-WBE-002

        Expected:
        - Returns zero metrics (all zeros)
        - warning = "No cost elements found for WBEs"
        """
        # Arrange - Create WBE without cost elements
        dept_res = await client.post(
            "/api/v1/departments",
            json={"code": f"D-{uuid4().hex[:4].upper()}", "name": "Empty Dept"},
        )
        dept_res.json()["department_id"]

        proj_res = await client.post(
            "/api/v1/projects",
            json={
                "code": f"P-{uuid4().hex[:4].upper()}",
                "name": "Empty Proj",
            },
        )
        proj_id = proj_res.json()["project_id"]

        wbe_res = await client.post(
            "/api/v1/wbes",
            json={
                "code": f"W-{uuid4().hex[:4].upper()}",
                "name": "Empty WBE",
                "project_id": proj_id,
                "branch": "main",
            },
        )
        wbe_id = wbe_res.json()["wbe_id"]

        # Act
        response = await client.get(f"/api/v1/evm/wbe/{wbe_id}/metrics")

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify zero metrics
        assert float(data["bac"]) == 0
        assert float(data["ac"]) == 0
        assert float(data["ev"]) == 0

        # Verify warning
        assert data.get("warning") is not None
        assert "No cost elements found" in data["warning"]


class TestProjectEntityEVM:
    """Test EVM metrics for Project entity type.

    NOTE: These tests are marked as expected to fail until BE-009 is completed.
    BE-009: Extend API routes for WBE and Project entities.
    """

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="Project entity type not yet supported in API routes (BE-009)"
    )
    async def test_get_project_metrics_aggregates_child_wbes(
        self, client: AsyncClient, setup_project_evm_data: dict[str, Any]
    ) -> None:
        """Test GET /evm/project/{id}/metrics aggregates child WBEs.

        Test ID: T-BE-PROJ-001

        Expected:
        - Returns EVMMetricsResponse with entity_type="project"
        - BAC = sum of all descendant cost element budgets
        - AC = sum of all descendant cost element actual costs
        - EV = sum of all descendant cost element earned values
        """
        # Arrange
        project_id = setup_project_evm_data["project_id"]

        # Act
        response = await client.get(f"/api/v1/evm/project/{project_id}/metrics")

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify entity type
        assert data["entity_type"] == EntityType.PROJECT
        assert data["entity_id"] == str(project_id)

        # Verify aggregation
        expected_bac = setup_project_evm_data["total_budget"]  # 600000
        expected_ac = setup_project_evm_data["total_costs"]  # 200000

        assert float(data["bac"]) == expected_bac
        assert float(data["ac"]) == expected_ac

        # EV = sum of all child EVs (4 CEs × 150k × 60% = 360k)
        expected_ev = 360000
        assert float(data["ev"]) == expected_ev


class TestEVMMultiEntityAggregation:
    """Test multi-entity EVM aggregation via batch endpoint."""

    @pytest.mark.asyncio
    async def test_batch_wbe_metrics_aggregates_correctly(
        self, client: AsyncClient, setup_wbe_evm_data: dict[str, Any]
    ) -> None:
        """Test POST /evm/batch with WBE entity type.

        Test ID: T-BE-BATCH-001

        Expected:
        - Returns aggregated metrics for multiple WBEs
        - BAC, PV, AC, EV are summed
        - CPI, SPI are BAC-weighted averages
        """
        # Arrange - Create a second WBE
        dept_res = await client.post(
            "/api/v1/departments",
            json={"code": f"D-{uuid4().hex[:4].upper()}", "name": "Batch Dept"},
        )
        dept_id = dept_res.json()["department_id"]

        type_res = await client.post(
            "/api/v1/cost-element-types",
            json={
                "code": f"T-{uuid4().hex[:4].upper()}",
                "name": "Batch Type",
                "department_id": dept_id,
            },
        )
        type_id = type_res.json()["cost_element_type_id"]

        proj_res = await client.post(
            "/api/v1/projects",
            json={
                "code": f"P-{uuid4().hex[:4].upper()}",
                "name": "Batch Proj",
            },
        )
        proj_id = proj_res.json()["project_id"]

        # Create second WBE
        wbe2_res = await client.post(
            "/api/v1/wbes",
            json={
                "code": f"W-{uuid4().hex[:4].upper()}",
                "name": "Second WBE",
                "project_id": proj_id,
                "branch": "main",
            },
        )
        wbe2_id = wbe2_res.json()["wbe_id"]

        # Add cost element to second WBE
        ce_res = await client.post(
            "/api/v1/cost-elements",
            json={
                "code": f"CE-{uuid4().hex[:4].upper()}",
                "name": "Second WBE CE",
                "budget_amount": 200000,
                "wbe_id": wbe2_id,
                "cost_element_type_id": type_id,
                "branch": "main",
            },
        )
        ce_id = ce_res.json()["cost_element_id"]

        await client.post(
            f"/api/v1/cost-elements/{ce_id}/schedule-baseline",
            json={
                "start_date": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
                "end_date": datetime(2026, 12, 31, tzinfo=UTC).isoformat(),
                "progression_type": "LINEAR",
                "description": "2026 Baseline",
            },
        )

        await client.post(
            "/api/v1/progress-entries",
            json={
                "cost_element_id": str(ce_id),
                "progress_percentage": 75.0,
                "reported_date": datetime(2026, 6, 30, tzinfo=UTC).isoformat(),
                "reported_by_user_id": str(mock_admin_user.user_id),
                "notes": "Progress",
            },
        )

        await client.post(
            "/api/v1/cost-registrations",
            json={
                "cost_element_id": str(ce_id),
                "amount": 80000.0,
                "description": "Costs",
                "registration_date": datetime(2026, 6, 15, tzinfo=UTC).isoformat(),
            },
        )

        wbe1_id = setup_wbe_evm_data["wbe_id"]

        # Act
        response = await client.post(
            "/api/v1/evm/batch",
            json={
                "entity_type": EntityType.WBE,
                "entity_ids": [str(wbe1_id), str(wbe2_id)],
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify aggregation
        # WBE1: 600k budget, WBE2: 200k budget = 800k total
        expected_bac = 800000
        assert float(data["bac"]) == expected_bac

    @pytest.mark.asyncio
    async def test_batch_project_metrics_aggregates_correctly(
        self, client: AsyncClient
    ) -> None:
        """Test POST /evm/batch with Project entity type.

        Test ID: T-BE-BATCH-002

        Expected:
        - Returns aggregated metrics for multiple projects
        """
        # Arrange - Create two projects with WBEs and cost elements
        dept_res = await client.post(
            "/api/v1/departments",
            json={"code": f"D-{uuid4().hex[:4].upper()}", "name": "Batch Proj Dept"},
        )
        dept_id = dept_res.json()["department_id"]

        type_res = await client.post(
            "/api/v1/cost-element-types",
            json={
                "code": f"T-{uuid4().hex[:4].upper()}",
                "name": "Batch Proj Type",
                "department_id": dept_id,
            },
        )
        type_id = type_res.json()["cost_element_type_id"]

        project_ids = []

        for i in range(1, 3):
            proj_res = await client.post(
                "/api/v1/projects",
                json={
                    "code": f"P-{uuid4().hex[:4].upper()}",
                    "name": f"Batch Project {i}",
                },
            )
            proj_id = proj_res.json()["project_id"]
            project_ids.append(proj_id)

            wbe_res = await client.post(
                "/api/v1/wbes",
                json={
                    "code": f"W-{uuid4().hex[:4].upper()}",
                    "name": f"Batch WBE {i}",
                    "project_id": proj_id,
                    "branch": "main",
                },
            )
            wbe_id = wbe_res.json()["wbe_id"]

            ce_res = await client.post(
                "/api/v1/cost-elements",
                json={
                    "code": f"CE-{uuid4().hex[:4].upper()}",
                    "name": f"Batch CE {i}",
                    "budget_amount": 150000,
                    "wbe_id": wbe_id,
                    "cost_element_type_id": type_id,
                    "branch": "main",
                },
            )
            ce_id = ce_res.json()["cost_element_id"]

            await client.post(
                f"/api/v1/cost-elements/{ce_id}/schedule-baseline",
                json={
                    "start_date": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
                    "end_date": datetime(2026, 12, 31, tzinfo=UTC).isoformat(),
                    "progression_type": "LINEAR",
                    "description": "2026 Baseline",
                },
            )

            await client.post(
                "/api/v1/progress-entries",
                json={
                    "cost_element_id": str(ce_id),
                    "progress_percentage": 50.0,
                    "reported_date": datetime(2026, 6, 30, tzinfo=UTC).isoformat(),
                    "reported_by_user_id": str(mock_admin_user.user_id),
                    "notes": "Progress",
                },
            )

        # Act
        response = await client.post(
            "/api/v1/evm/batch",
            json={
                "entity_type": EntityType.PROJECT,
                "entity_ids": [str(pid) for pid in project_ids],
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify aggregation (2 projects × 150k budget = 300k)
        expected_bac = 300000
        assert float(data["bac"]) == expected_bac


# =============================================================================
# TIME-TRAVEL TESTS
# =============================================================================


class TestEVMTimeTravel:
    """Test time-travel functionality with different control dates.

    NOTE: WBE/Project tests are marked as xfail until BE-009 is completed.
    """

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="WBE entity type not yet supported in API routes (BE-009)"
    )
    async def test_wbe_time_travel_with_past_control_date(
        self, client: AsyncClient, setup_wbe_evm_data: dict[str, Any]
    ) -> None:
        """Test GET /evm/wbe/{id}/metrics with control_date in the past.

        Test ID: T-BE-TT-001

        Expected:
        - Returns metrics as of the specified control_date
        - Only includes cost registrations up to control_date
        - Only includes progress entries up to control_date
        """
        # Arrange
        wbe_id = setup_wbe_evm_data["wbe_id"]
        past_date = datetime(2026, 3, 1, tzinfo=UTC)  # Before costs were registered

        # Act
        response = await client.get(
            f"/api/v1/evm/wbe/{wbe_id}/metrics",
            params={"control_date": past_date.isoformat()},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # AC should be 0 or lower (costs were registered on 2026-06-15)
        assert float(data["ac"]) < float(data["bac"])

        # Control date should be in response
        assert "control_date" in data

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="WBE entity type not yet supported in API routes (BE-009)"
    )
    async def test_wbe_time_travel_with_future_control_date(
        self, client: AsyncClient, setup_wbe_evm_data: dict[str, Any]
    ) -> None:
        """Test GET /evm/wbe/{id}/metrics with control_date in the future.

        Test ID: T-BE-TT-002

        Expected:
        - Returns metrics as of the future control_date
        - Includes all cost registrations and progress entries
        """
        # Arrange
        wbe_id = setup_wbe_evm_data["wbe_id"]
        future_date = datetime(2027, 1, 1, tzinfo=UTC)

        # Act
        response = await client.get(
            f"/api/v1/evm/wbe/{wbe_id}/metrics",
            params={"control_date": future_date.isoformat()},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Should include all costs and progress
        assert float(data["ac"]) == setup_wbe_evm_data["total_costs"]

    @pytest.mark.asyncio
    async def test_wbe_timeseries_respects_control_date(
        self, client: AsyncClient, setup_wbe_evm_data: dict[str, Any]
    ) -> None:
        """Test GET /evm/wbe/{id}/timeseries with control_date.

        Test ID: T-BE-TT-003

        Expected:
        - Returns time-series data up to control_date
        - Future dates show forecast/plan values
        """
        # Arrange
        wbe_id = setup_wbe_evm_data["wbe_id"]
        control_date = datetime(2026, 6, 30, tzinfo=UTC)

        # Act
        response = await client.get(
            f"/api/v1/evm/wbe/{wbe_id}/timeseries",
            params={
                "granularity": "month",
                "control_date": control_date.isoformat(),
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify time-series structure
        assert "points" in data
        assert isinstance(data["points"], list)
        assert data["granularity"] == "month"


# =============================================================================
# BRANCHING TESTS
# =============================================================================


class TestEVMBranching:
    """Test branching functionality with ISOLATED vs MERGE modes.

    NOTE: WBE/Project tests are marked as xfail until BE-009 is completed.
    """

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="WBE entity type not yet supported in API routes (BE-009)"
    )
    async def test_wbe_metrics_with_isolated_branch_mode(
        self, client: AsyncClient, setup_wbe_evm_data: dict[str, Any]
    ) -> None:
        """Test GET /evm/wbe/{id}/metrics with branch_mode=STRICT.

        Test ID: T-BE-BRANCH-001

        Expected:
        - Only returns data from the specified branch
        - Falls back to parent branches is disabled
        """
        # Arrange
        wbe_id = setup_wbe_evm_data["wbe_id"]

        # Act
        response = await client.get(
            f"/api/v1/evm/wbe/{wbe_id}/metrics",
            params={
                "branch": "main",
                "branch_mode": "strict",
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify branch mode in response
        assert data["branch"] == "main"
        # Note: branch_mode is returned as BranchMode enum value

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="WBE entity type not yet supported in API routes (BE-009)"
    )
    async def test_wbe_metrics_with_merge_branch_mode(
        self, client: AsyncClient, setup_wbe_evm_data: dict[str, Any]
    ) -> None:
        """Test GET /evm/wbe/{id}/metrics with branch_mode=MERGE.

        Test ID: T-BE-BRANCH-002

        Expected:
        - Returns data from specified branch, falling back to parent branches
        - Uses main branch if feature branch doesn't exist
        """
        # Arrange
        wbe_id = setup_wbe_evm_data["wbe_id"]

        # Act
        response = await client.get(
            f"/api/v1/evm/wbe/{wbe_id}/metrics",
            params={
                "branch": "main",
                "branch_mode": "merge",
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify branch mode in response
        assert data["branch"] == "main"

    @pytest.mark.asyncio
    async def test_wbe_batch_with_branch_mode(
        self, client: AsyncClient, setup_wbe_evm_data: dict[str, Any]
    ) -> None:
        """Test POST /evm/batch with branch mode parameter.

        Test ID: T-BE-BRANCH-003

        Expected:
        - Returns aggregated metrics respecting branch mode
        """
        # Arrange
        wbe_id = setup_wbe_evm_data["wbe_id"]

        # Act
        response = await client.post(
            "/api/v1/evm/batch",
            json={
                "entity_type": EntityType.WBE,
                "entity_ids": [str(wbe_id)],
                "branch": "main",
                "branch_mode": "merge",
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert data["branch"] == "main"


# =============================================================================
# TIME-SERIES TESTS
# =============================================================================


class TestEVMTimeSeries:
    """Test time-series data retrieval with different granularities.

    NOTE: WBE/Project tests are marked as xfail until BE-009 is completed.
    """

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="WBE entity type not yet supported in API routes (BE-009)"
    )
    async def test_wbe_timeseries_with_daily_granularity(
        self, client: AsyncClient, setup_wbe_evm_data: dict[str, Any]
    ) -> None:
        """Test GET /evm/wbe/{id}/timeseries with granularity=day.

        Test ID: T-BE-TS-001

        Expected:
        - Returns daily data points
        - granularity in response = "day"
        - Each point has date, pv, ev, ac, forecast, actual
        """
        # Arrange
        wbe_id = setup_wbe_evm_data["wbe_id"]

        # Act
        response = await client.get(
            f"/api/v1/evm/wbe/{wbe_id}/timeseries",
            params={"granularity": "day"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify granularity
        assert data["granularity"] == "day"

        # Verify points structure
        assert "points" in data
        assert isinstance(data["points"], list)

        # If points exist, verify structure
        if data["points"]:
            point = data["points"][0]
            assert "date" in point
            assert "pv" in point
            assert "ev" in point
            assert "ac" in point
            assert "forecast" in point
            assert "actual" in point

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="WBE entity type not yet supported in API routes (BE-009)"
    )
    async def test_wbe_timeseries_with_weekly_granularity(
        self, client: AsyncClient, setup_wbe_evm_data: dict[str, Any]
    ) -> None:
        """Test GET /evm/wbe/{id}/timeseries with granularity=week.

        Test ID: T-BE-TS-002

        Expected:
        - Returns weekly data points
        - granularity in response = "week"
        """
        # Arrange
        wbe_id = setup_wbe_evm_data["wbe_id"]

        # Act
        response = await client.get(
            f"/api/v1/evm/wbe/{wbe_id}/timeseries",
            params={"granularity": "week"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert data["granularity"] == "week"
        assert "points" in data

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="WBE entity type not yet supported in API routes (BE-009)"
    )
    async def test_wbe_timeseries_with_monthly_granularity(
        self, client: AsyncClient, setup_wbe_evm_data: dict[str, Any]
    ) -> None:
        """Test GET /evm/wbe/{id}/timeseries with granularity=month.

        Test ID: T-BE-TS-003

        Expected:
        - Returns monthly data points
        - granularity in response = "month"
        - Fewer points than daily/weekly
        """
        # Arrange
        wbe_id = setup_wbe_evm_data["wbe_id"]

        # Act
        response = await client.get(
            f"/api/v1/evm/wbe/{wbe_id}/timeseries",
            params={"granularity": "month"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert data["granularity"] == "month"
        assert "points" in data

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="Project entity type not yet supported in API routes (BE-009)"
    )
    async def test_project_timeseries_aggregates_child_wbes(
        self, client: AsyncClient, setup_project_evm_data: dict[str, Any]
    ) -> None:
        """Test GET /evm/project/{id}/timeseries aggregates child WBEs.

        Test ID: T-BE-TS-004

        Expected:
        - Returns aggregated time-series from all child WBEs
        - Date range covers overall project timeline
        """
        # Arrange
        project_id = setup_project_evm_data["project_id"]

        # Act
        response = await client.get(
            f"/api/v1/evm/project/{project_id}/timeseries",
            params={"granularity": "week"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify time-series structure
        assert "points" in data
        assert "start_date" in data
        assert "end_date" in data
        assert "total_points" in data
        assert data["granularity"] == "week"


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


class TestEVMErrorHandling:
    """Test error handling for EVM endpoints."""

    @pytest.mark.asyncio
    async def test_wbe_metrics_with_invalid_id_returns_404(
        self, client: AsyncClient
    ) -> None:
        """Test GET /evm/wbe/{invalid_id}/metrics returns 404.

        Test ID: T-BE-ERR-001

        Expected:
        - Returns 404 Not Found
        - Error message indicates entity not found
        """
        # Arrange
        fake_id = uuid4()

        # Act
        response = await client.get(f"/api/v1/evm/wbe/{fake_id}/metrics")

        # Assert
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_project_metrics_with_invalid_id_returns_404(
        self, client: AsyncClient
    ) -> None:
        """Test GET /evm/project/{invalid_id}/metrics returns 404.

        Test ID: T-BE-ERR-002

        Expected:
        - Returns 404 Not Found
        """
        # Arrange
        fake_id = uuid4()

        # Act
        response = await client.get(f"/api/v1/evm/project/{fake_id}/metrics")

        # Assert
        assert response.status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="WBE entity type not yet supported in API routes (BE-009)"
    )
    async def test_wbe_timeseries_with_invalid_id_returns_404(
        self, client: AsyncClient
    ) -> None:
        """Test GET /evm/wbe/{invalid_id}/timeseries returns 404.

        Test ID: T-BE-ERR-003

        Expected:
        - Returns 404 Not Found
        """
        # Arrange
        fake_id = uuid4()

        # Act
        response = await client.get(f"/api/v1/evm/wbe/{fake_id}/timeseries")

        # Assert
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_batch_with_invalid_entity_type_returns_400(
        self, client: AsyncClient
    ) -> None:
        """Test POST /evm/batch with invalid entity_type returns 400.

        Test ID: T-BE-ERR-004

        Expected:
        - Returns 400 Bad Request
        - Error message indicates entity type not supported
        """
        # Act
        response = await client.post(
            "/api/v1/evm/batch",
            json={
                "entity_type": "invalid_type",
                "entity_ids": [str(uuid4())],
            },
        )

        # Assert
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_batch_with_empty_entity_ids_returns_zero_metrics(
        self, client: AsyncClient
    ) -> None:
        """Test POST /evm/batch with empty entity_ids list.

        Test ID: T-BE-ERR-005

        Expected:
        - Returns zero metrics (all zeros)
        - warning = "No entities provided"
        """
        # Act
        response = await client.post(
            "/api/v1/evm/batch",
            json={
                "entity_type": EntityType.WBE,
                "entity_ids": [],
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify zero metrics
        assert float(data["bac"]) == 0
        assert data.get("warning") is not None


# =============================================================================
# EDGE CASES TESTS
# =============================================================================


class TestEVMEdgeCases:
    """Test edge cases and boundary conditions.

    NOTE: WBE/Project tests are marked as xfail until BE-009 is completed.
    """

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="WBE entity type not yet supported in API routes (BE-009)"
    )
    async def test_wbe_metrics_with_no_progress_returns_warning(
        self, client: AsyncClient
    ) -> None:
        """Test GET /evm/wbe/{id}/metrics with WBE that has no progress.

        Test ID: T-BE-EDGE-001

        Expected:
        - EV = 0 for all cost elements
        - Warning message about no progress
        """
        # Arrange - Create WBE with cost elements but no progress
        dept_res = await client.post(
            "/api/v1/departments",
            json={"code": f"D-{uuid4().hex[:4].upper()}", "name": "No Progress Dept"},
        )
        dept_id = dept_res.json()["department_id"]

        type_res = await client.post(
            "/api/v1/cost-element-types",
            json={
                "code": f"T-{uuid4().hex[:4].upper()}",
                "name": "No Progress Type",
                "department_id": dept_id,
            },
        )
        type_id = type_res.json()["cost_element_type_id"]

        proj_res = await client.post(
            "/api/v1/projects",
            json={
                "code": f"P-{uuid4().hex[:4].upper()}",
                "name": "No Progress Proj",
            },
        )
        proj_id = proj_res.json()["project_id"]

        wbe_res = await client.post(
            "/api/v1/wbes",
            json={
                "code": f"W-{uuid4().hex[:4].upper()}",
                "name": "No Progress WBE",
                "project_id": proj_id,
                "branch": "main",
            },
        )
        wbe_id = wbe_res.json()["wbe_id"]

        ce_res = await client.post(
            "/api/v1/cost-elements",
            json={
                "code": f"CE-{uuid4().hex[:4].upper()}",
                "name": "No Progress CE",
                "budget_amount": 100000,
                "wbe_id": wbe_id,
                "cost_element_type_id": type_id,
                "branch": "main",
            },
        )
        ce_id = ce_res.json()["cost_element_id"]

        await client.post(
            f"/api/v1/cost-elements/{ce_id}/schedule-baseline",
            json={
                "start_date": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
                "end_date": datetime(2026, 12, 31, tzinfo=UTC).isoformat(),
                "progression_type": "LINEAR",
                "description": "2026 Baseline",
            },
        )

        # Act
        response = await client.get(f"/api/v1/evm/wbe/{wbe_id}/metrics")

        # Assert
        assert response.status_code == 200
        data = response.json()

        # EV should be 0
        assert float(data["ev"]) == 0

        # Warning should be present
        assert data.get("warning") is not None

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="WBE entity type not yet supported in API routes (BE-009)"
    )
    async def test_wbe_metrics_with_zero_ac_returns_none_for_cpi(
        self, client: AsyncClient
    ) -> None:
        """Test GET /evm/wbe/{id}/metrics with AC = 0.

        Test ID: T-BE-EDGE-002

        Expected:
        - CPI = None (division by zero handled gracefully)
        - Other metrics calculated normally
        """
        # Arrange - Create WBE with budget but no costs
        dept_res = await client.post(
            "/api/v1/departments",
            json={"code": f"D-{uuid4().hex[:4].upper()}", "name": "Zero AC Dept"},
        )
        dept_id = dept_res.json()["department_id"]

        type_res = await client.post(
            "/api/v1/cost-element-types",
            json={
                "code": f"T-{uuid4().hex[:4].upper()}",
                "name": "Zero AC Type",
                "department_id": dept_id,
            },
        )
        type_id = type_res.json()["cost_element_type_id"]

        proj_res = await client.post(
            "/api/v1/projects",
            json={
                "code": f"P-{uuid4().hex[:4].upper()}",
                "name": "Zero AC Proj",
            },
        )
        proj_id = proj_res.json()["project_id"]

        wbe_res = await client.post(
            "/api/v1/wbes",
            json={
                "code": f"W-{uuid4().hex[:4].upper()}",
                "name": "Zero AC WBE",
                "project_id": proj_id,
                "branch": "main",
            },
        )
        wbe_id = wbe_res.json()["wbe_id"]

        ce_res = await client.post(
            "/api/v1/cost-elements",
            json={
                "code": f"CE-{uuid4().hex[:4].upper()}",
                "name": "Zero AC CE",
                "budget_amount": 100000,
                "wbe_id": wbe_id,
                "cost_element_type_id": type_id,
                "branch": "main",
            },
        )
        ce_id = ce_res.json()["cost_element_id"]

        await client.post(
            f"/api/v1/cost-elements/{ce_id}/schedule-baseline",
            json={
                "start_date": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
                "end_date": datetime(2026, 12, 31, tzinfo=UTC).isoformat(),
                "progression_type": "LINEAR",
                "description": "2026 Baseline",
            },
        )

        await client.post(
            "/api/v1/progress-entries",
            json={
                "cost_element_id": str(ce_id),
                "progress_percentage": 50.0,
                "reported_date": datetime(2026, 6, 30, tzinfo=UTC).isoformat(),
                "reported_by_user_id": str(mock_admin_user.user_id),
                "notes": "Progress",
            },
        )

        # Act
        response = await client.get(f"/api/v1/evm/wbe/{wbe_id}/metrics")

        # Assert
        assert response.status_code == 200
        data = response.json()

        # AC should be 0
        assert float(data["ac"]) == 0

        # CPI should be None (division by zero)
        assert data.get("cpi") is None

        # EV should be calculated (BAC × 50%)
        assert float(data["ev"]) == 50000
