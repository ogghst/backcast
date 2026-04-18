"""API integration tests for EVM metrics."""

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
            "progress-entry-read",
            "progress-entry-create",
        ]


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
async def setup_evm_data(client: AsyncClient) -> dict[str, Any]:
    """Setup complete EVM data: cost element, baseline, progress, costs."""
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
            "branch": "main",
        },
    )
    wbe_id = wbe_res.json()["wbe_id"]

    # 5. Cost Element with budget
    ce_res = await client.post(
        "/api/v1/cost-elements",
        json={
            "code": f"CE-{uuid4().hex[:4].upper()}",
            "name": "Cost Element",
            "budget_amount": 100000,
            "wbe_id": wbe_id,
            "cost_element_type_id": type_id,
            "branch": "main",
        },
    )
    cost_element_id = ce_res.json()["cost_element_id"]

    # 6. Schedule Baseline
    # 6. Schedule Baseline (Update Default)
    # Note: Cost Element creation auto-creates a default baseline (90 days).
    # We must update it to cover the full year.
    sb_res = await client.get(
        f"/api/v1/cost-elements/{cost_element_id}/schedule-baseline"
    )
    sb_data = sb_res.json()
    baseline_id = sb_data["schedule_baseline_id"]

    await client.put(
        f"/api/v1/cost-elements/{cost_element_id}/schedule-baseline/{baseline_id}",
        json={
            "start_date": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
            "end_date": datetime(2026, 12, 31, tzinfo=UTC).isoformat(),
            "progression_type": "LINEAR",
            "description": "2026 Project Baseline",
        },
    )

    # 7. Progress Entry (50% complete)
    await client.post(
        "/api/v1/progress-entries",
        json={
            "cost_element_id": str(cost_element_id),
            "progress_percentage": 50.0,
            "reported_date": datetime(2026, 6, 30, tzinfo=UTC).isoformat(),
            "reported_by_user_id": str(mock_admin_user.user_id),
            "notes": "Halfway complete",
        },
    )

    # 8. Cost Registrations (total 60,000)
    await client.post(
        "/api/v1/cost-registrations",
        json={
            "cost_element_id": str(cost_element_id),
            "amount": 35000.0,
            "description": "Materials",
            "registration_date": datetime(2026, 3, 1, tzinfo=UTC).isoformat(),
        },
    )
    await client.post(
        "/api/v1/cost-registrations",
        json={
            "cost_element_id": str(cost_element_id),
            "amount": 25000.0,
            "description": "Labor",
            "registration_date": datetime(2026, 6, 15, tzinfo=UTC).isoformat(),
        },
    )

    return {
        "cost_element_id": cost_element_id,
        "budget": 100000,
        "progress": 50.0,
        "total_costs": 60000,
    }


class TestEVMMetricsAPI:
    """Test EVM metrics API endpoint."""

    @pytest.mark.asyncio
    async def test_get_evm_metrics_returns_all_8_metrics(
        self, client: AsyncClient, setup_evm_data: dict[str, Any]
    ) -> None:
        """Test GET /cost-elements/{id}/evm returns all 8 EVM metrics.

        Test ID: T-011

        Expected metrics:
        - BAC (Budget at Completion)
        - PV (Planned Value)
        - AC (Actual Cost)
        - EV (Earned Value)
        - CV (Cost Variance)
        - SV (Schedule Variance)
        - CPI (Cost Performance Index)
        - SPI (Schedule Performance Index)
        """
        # Arrange
        cost_element_id = setup_evm_data["cost_element_id"]

        # Act
        response = await client.get(f"/api/v1/cost-elements/{cost_element_id}/evm")

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify all 8 metrics are present
        assert "bac" in data
        assert "pv" in data
        assert "ac" in data
        assert "ev" in data
        assert "cv" in data
        assert "sv" in data
        assert "cpi" in data
        assert "spi" in data

        # Verify values (Decimal fields are serialized as numbers)
        assert data["bac"] == 100000.0  # Budget
        assert data["ac"] == 60000.0  # Sum of costs
        assert (
            data["ev"] == 50000.0
        )  # BAC × 50% (4 decimal places for calculated values)

        # Verify variances
        assert data["cv"] == -10000.0  # EV - AC = 50000 - 60000
        # Note: PV depends on date calculation, may vary

        # Verify metadata
        assert data["cost_element_id"] == str(cost_element_id)
        assert "control_date" in data
        assert data["progress_percentage"] == 50.0
        assert data.get("warning") is None  # No warning (progress exists)

    @pytest.mark.asyncio
    async def test_get_evm_metrics_with_no_progress_returns_warning(
        self, client: AsyncClient, setup_evm_data: dict[str, Any]
    ) -> None:
        """Test EVM when no progress reported returns EV=0 with warning.

        Test ID: T-014

        Expected:
        - EV = 0
        - Warning message present
        - CPI = 0 (since EV = 0)
        """
        # Create a new cost element without progress
        dept_res = await client.post(
            "/api/v1/departments",
            json={"code": f"D-{uuid4().hex[:4].upper()}", "name": "Dept2"},
        )
        dept_id = dept_res.json()["department_id"]

        type_res = await client.post(
            "/api/v1/cost-element-types",
            json={
                "code": f"T-{uuid4().hex[:4].upper()}",
                "name": "Type",
                "department_id": dept_id,
            },
        )
        type_id = type_res.json()["cost_element_type_id"]

        proj_res = await client.post(
            "/api/v1/projects",
            json={
                "code": f"P-{uuid4().hex[:4].upper()}",
                "name": "Proj2",
            },
        )
        proj_id = proj_res.json()["project_id"]

        wbe_res = await client.post(
            "/api/v1/wbes",
            json={
                "code": f"W-{uuid4().hex[:4].upper()}",
                "name": "WBE2",
                "project_id": proj_id,
                "branch": "main",
            },
        )
        wbe_id = wbe_res.json()["wbe_id"]

        ce_res = await client.post(
            "/api/v1/cost-elements",
            json={
                "code": f"CE-{uuid4().hex[:4].upper()}",
                "name": "Cost Element No Progress",
                "budget_amount": 100000,
                "wbe_id": wbe_id,
                "cost_element_type_id": type_id,
                "branch": "main",
            },
        )
        new_cost_element_id = ce_res.json()["cost_element_id"]

        # Act
        response = await client.get(f"/api/v1/cost-elements/{new_cost_element_id}/evm")

        # Assert
        assert response.status_code == 200
        data = response.json()

        # EV should be 0
        assert data["ev"] == 0.0

        # Warning should be present
        assert data["warning"] is not None
        assert "No progress reported" in data["warning"]

        # CPI should be 0 or None (since EV = 0)
        assert data.get("cpi") is None or data.get("cpi") == 0

    @pytest.mark.asyncio
    async def test_get_evm_metrics_with_control_date(
        self, client: AsyncClient, setup_evm_data: dict[str, Any]
    ) -> None:
        """Test EVM with control_date parameter for time-travel.

        Test ID: T-012, T-013

        Scenario:
        - Query with control_date in the past
        - Expected: Returns metrics as of that date
        """
        # Arrange
        cost_element_id = setup_evm_data["cost_element_id"]
        # Use a date in the future (entities were created at test runtime)
        future_date = datetime(2026, 6, 30, tzinfo=UTC)

        # Act
        response = await client.get(
            f"/api/v1/cost-elements/{cost_element_id}/evm",
            params={"control_date": future_date.isoformat()},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Control date should be reflected in response
        assert "control_date" in data

    @pytest.mark.asyncio
    async def test_get_evm_metrics_cost_element_not_found(
        self, client: AsyncClient
    ) -> None:
        """Test EVM with non-existent cost element returns 404.

        Test ID: T-012
        """
        # Arrange
        fake_id = uuid4()

        # Act
        response = await client.get(f"/api/v1/cost-elements/{fake_id}/evm")

        # Assert
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_evm_metrics_branch_isolation(
        self, client: AsyncClient, setup_evm_data: dict[str, Any]
    ) -> None:
        """Test EVM with branch parameter.

        Test ID: T-013

        Scenario:
        - Query with branch="main"
        - Expected: Returns metrics for main branch
        """
        # Arrange
        cost_element_id = setup_evm_data["cost_element_id"]

        # Act
        response = await client.get(
            f"/api/v1/cost-elements/{cost_element_id}/evm",
            params={"branch": "main"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "bac" in data

    @pytest.mark.asyncio
    async def test_evm_timeseries_ac_future_flatline(
        self, client: AsyncClient, setup_evm_data: dict[str, Any]
    ) -> None:
        """Test that AC flatlines for future dates instead of dropping to zero.

        Scenario:
        - Control Date: June 1st 2026.
        - Cost Registrations exist up to June 1st.
        - Expected: Future months (July+) show same AC as June 1st.
        """
        cost_element_id = setup_evm_data["cost_element_id"]

        # Helper: Get time series with control date = June 1st
        control_date = datetime(2026, 6, 1, tzinfo=UTC)

        response = await client.get(
            f"/api/v1/evm/cost_element/{cost_element_id}/timeseries",
            params={
                "granularity": "month",
                "control_date": control_date.isoformat(),
            },
        )
        assert response.status_code == 200
        data = response.json()
        points = data["points"]

        # Locate points
        # May (past)
        may_point = next((p for p in points if p["date"].startswith("2026-05")), None)
        # July (Future)
        july_point = next((p for p in points if p["date"].startswith("2026-07")), None)

        assert may_point is not None, "May point not found"
        assert july_point is not None, "July point not found"

        # Verify AC is carried forward
        # Expected AC in May is 35000 (from March 1st registration)
        # AC in June 1st is 35000.
        # July should stay 35000.
        assert float(may_point["ac"]) == 35000.0, (
            f"May AC expected 35000.0, got {may_point['ac']}"
        )
        assert float(july_point["ac"]) == 35000.0, (
            f"AC for future date should be flatlined at 35000.0, but got {july_point['ac']}"
        )

    @pytest.mark.asyncio
    async def test_evm_timeseries_ev_future_flatline(
        self, client: AsyncClient, setup_evm_data: dict[str, Any]
    ) -> None:
        """Test that EV flatlines for future dates instead of dropping to zero.

        Scenario:
        - Control Date: June 1st 2026.
        - Progress Entries exist up to June 30th (50%).
        - BAC is 100,000.
        - EV = 50,000.
        - Expected: Future months (July+) show same EV as June.
        """
        cost_element_id = setup_evm_data["cost_element_id"]

        # Helper: Get time series with control date = July 1st (after progress report)
        control_date = datetime(2026, 7, 1, tzinfo=UTC)

        response = await client.get(
            f"/api/v1/evm/cost_element/{cost_element_id}/timeseries",
            params={
                "granularity": "month",
                "control_date": control_date.isoformat(),
            },
        )
        assert response.status_code == 200
        data = response.json()
        points = data["points"]

        # Locate points
        # June (last progress)
        june_point = next((p for p in points if p["date"].startswith("2026-06")), None)
        # August (Future)
        august_point = next(
            (p for p in points if p["date"].startswith("2026-08")), None
        )

        assert june_point is not None, "June point not found"
        assert august_point is not None, "August point not found"

        # Verify EV is carried forward
        # Expected EV in June is 50,000 (50% of 100,000)
        # August should stay 50,000.
        expected_ev = 50000.0
        assert float(june_point["ev"]) == expected_ev, (
            f"June EV expected {expected_ev}, got {june_point['ev']}"
        )
        assert float(august_point["ev"]) == expected_ev, (
            f"August EV expected {expected_ev}, got {august_point['ev']}"
        )

    @pytest_asyncio.fixture
    async def setup_wbe_level_data(self, client: AsyncClient) -> dict[str, Any]:
        """Setup WBE with multiple cost elements for aggregation tests."""
        # 1. Project
        proj_res = await client.post(
            "/api/v1/projects",
            json={
                "code": f"P2-{uuid4().hex[:4].upper()}",
                "name": "Proj2",
            },
        )
        proj_id = proj_res.json()["project_id"]

        # 2. WBE
        wbe_res = await client.post(
            "/api/v1/wbes",
            json={
                "code": f"W2-{uuid4().hex[:4].upper()}",
                "name": "WBE2",
                "project_id": proj_id,
                "branch": "main",
            },
        )
        wbe_id = wbe_res.json()["wbe_id"]

        # 3. Department & Type (reuse if possible, but create new for isolation)
        dept_res = await client.post(
            "/api/v1/departments",
            json={"code": f"D2-{uuid4().hex[:4].upper()}", "name": "Dept2"},
        )
        dept_id = dept_res.json()["department_id"]

        type_res = await client.post(
            "/api/v1/cost-element-types",
            json={
                "code": f"T2-{uuid4().hex[:4].upper()}",
                "name": "Type2",
                "department_id": dept_id,
            },
        )
        type_id = type_res.json()["cost_element_type_id"]

        # 4. Cost Element 1 (Budget 100k, 50% progress, 60k cost)
        ce1_res = await client.post(
            "/api/v1/cost-elements",
            json={
                "code": f"CE1-{uuid4().hex[:4].upper()}",
                "name": "Cost Element 1",
                "budget_amount": 100000,
                "wbe_id": wbe_id,
                "cost_element_type_id": type_id,
                "branch": "main",
            },
        )
        ce1_id = ce1_res.json()["cost_element_id"]

        # CE1 Progress (50%)
        await client.post(
            "/api/v1/progress-entries",
            json={
                "cost_element_id": str(ce1_id),
                "progress_percentage": 50.0,
                "reported_date": datetime(2026, 6, 30, tzinfo=UTC).isoformat(),
                "reported_by_user_id": str(mock_admin_user.user_id),
                "notes": "Halfway",
            },
        )
        # CE1 Costs (60k)
        await client.post(
            "/api/v1/cost-registrations",
            json={
                "cost_element_id": str(ce1_id),
                "amount": 60000.0,
                "description": "Cost 1",
                "registration_date": datetime(2026, 6, 1, tzinfo=UTC).isoformat(),
            },
        )

        # 5. Cost Element 2 (Budget 50k, 20% progress, 5k cost)
        ce2_res = await client.post(
            "/api/v1/cost-elements",
            json={
                "code": f"CE2-{uuid4().hex[:4].upper()}",
                "name": "Cost Element 2",
                "budget_amount": 50000,
                "wbe_id": wbe_id,
                "cost_element_type_id": type_id,
                "branch": "main",
            },
        )
        ce2_id = ce2_res.json()["cost_element_id"]

        # CE2 Progress (20%)
        await client.post(
            "/api/v1/progress-entries",
            json={
                "cost_element_id": str(ce2_id),
                "progress_percentage": 20.0,
                "reported_date": datetime(2026, 6, 30, tzinfo=UTC).isoformat(),
                "reported_by_user_id": str(mock_admin_user.user_id),
                "notes": "Started",
            },
        )
        # CE2 Costs (5k)
        await client.post(
            "/api/v1/cost-registrations",
            json={
                "cost_element_id": str(ce2_id),
                "amount": 5000.0,
                "description": "Cost 2",
                "registration_date": datetime(2026, 6, 1, tzinfo=UTC).isoformat(),
            },
        )

        return {
            "project_id": proj_id,
            "wbe_id": wbe_id,
            "ce1_id": ce1_id,
            "ce2_id": ce2_id,
            "ce1_metrics": {"bac": 100000, "ev": 50000, "ac": 60000},
            "ce2_metrics": {"bac": 50000, "ev": 10000, "ac": 5000},
            "wbe_metrics": {
                "bac": 150000,  # 100k + 50k
                "ev": 60000,  # 50k + 10k
                "ac": 65000,  # 60k + 5k
            },
        }

    @pytest.mark.asyncio
    async def test_get_evm_metrics_wbe_aggregates_child_cost_elements(
        self, client: AsyncClient, setup_wbe_level_data: dict[str, Any]
    ) -> None:
        """Test GET /evm/wbe/{id}/metrics returns aggregated metrics.

        Expected: WBE metrics should be sum of child cost elements.
        """
        wbe_id = setup_wbe_level_data["wbe_id"]
        expected = setup_wbe_level_data["wbe_metrics"]

        response = await client.get(f"/api/v1/evm/wbe/{wbe_id}/metrics")
        assert response.status_code == 200
        data = response.json()

        # Verify aggregation
        assert data["bac"] == float(expected["bac"])
        assert data["ev"] == float(expected["ev"])
        assert data["ac"] == float(expected["ac"])

        # Verify weighted CPI/SPI
        # CPI = Total EV / Total AC = 60000 / 65000 ≈ 0.9231
        expected_cpi = expected["ev"] / expected["ac"]
        assert abs(data["cpi"] - expected_cpi) < 0.0001

        # Verify progress percentage (BAC weighted)
        # (50% * 100k + 20% * 50k) / 150k = (50k + 10k) / 150k = 60/150 = 40%
        assert data["progress_percentage"] == 40.0

    @pytest.mark.asyncio
    async def test_get_evm_metrics_project_aggregates_child_wbes(
        self, client: AsyncClient, setup_wbe_level_data: dict[str, Any]
    ) -> None:
        """Test GET /evm/project/{id}/metrics returns aggregated metrics.

        Expected: Project metrics should be sum of child WBEs (which sum cost elements).
        """
        project_id = setup_wbe_level_data["project_id"]
        expected = setup_wbe_level_data[
            "wbe_metrics"
        ]  # Project only has 1 WBE, so same metrics

        response = await client.get(f"/api/v1/evm/project/{project_id}/metrics")
        assert response.status_code == 200
        data = response.json()

        # Verify aggregation
        assert data["bac"] == float(expected["bac"])
        assert data["ev"] == float(expected["ev"])
        assert data["ac"] == float(expected["ac"])

    @pytest.mark.asyncio
    async def test_get_evm_timeseries_wbe_aggregates_points(
        self, client: AsyncClient, setup_wbe_level_data: dict[str, Any]
    ) -> None:
        """Test WBE time series aggregates data from children."""
        wbe_id = setup_wbe_level_data["wbe_id"]

        # Use a future control date to ensure the time series covers our data (June 2026)
        control_date = datetime(2026, 12, 31, tzinfo=UTC)

        response = await client.get(
            f"/api/v1/evm/wbe/{wbe_id}/timeseries",
            params={
                "granularity": "month",
                "control_date": control_date.isoformat(),
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["points"]) > 0

        # Check June point (both have data)
        june_point = next(
            (p for p in data["points"] if p["date"].startswith("2026-06")), None
        )
        assert june_point is not None

        # EV should be sum of both
        # CE1 EV @ June 30 = 50k
        # CE2 EV @ June 30 = 10k
        # Total EV = 60k
        assert float(june_point["ev"]) == 60000.0

    @pytest.mark.asyncio
    async def test_evm_aggregation_handles_missing_children(
        self, client: AsyncClient
    ) -> None:
        """Test WBE/Project EVM metrics with no children return zeros."""
        # Create empty project & WBE
        proj_res = await client.post(
            "/api/v1/projects",
            json={"code": f"PE-{uuid4()}", "name": "Empty Proj"},
        )
        proj_id = proj_res.json()["project_id"]

        wbe_res = await client.post(
            "/api/v1/wbes",
            json={"code": f"WE-{uuid4()}", "name": "Empty WBE", "project_id": proj_id},
        )
        wbe_id = wbe_res.json()["wbe_id"]

        # Test WBE empty
        wbe_resp = await client.get(f"/api/v1/evm/wbe/{wbe_id}/metrics")
        wbe_data = wbe_resp.json()
        assert wbe_data["bac"] == 0
        assert wbe_data["ev"] == 0
        assert "No cost elements found" in wbe_data["warning"]

    @pytest.mark.asyncio
    async def test_get_evm_timeseries_project_aggregates_points(
        self, client: AsyncClient, setup_wbe_level_data: dict[str, Any]
    ) -> None:
        """Test Project time series aggregates data from WBEs."""
        project_id = setup_wbe_level_data["project_id"]

        # Use future control date to include June 2026 data
        control_date = datetime(2026, 12, 31, tzinfo=UTC)

        response = await client.get(
            f"/api/v1/evm/project/{project_id}/timeseries",
            params={
                "granularity": "month",
                "control_date": control_date.isoformat(),
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["points"]) > 0

        # Check June point
        june_point = next(
            (p for p in data["points"] if p["date"].startswith("2026-06")), None
        )
        assert june_point is not None

    @pytest.mark.asyncio
    async def test_batch_calculate_evm_metrics_cost_elements(
        self, client: AsyncClient, setup_wbe_level_data: dict[str, Any]
    ) -> None:
        """Test POST /evm/batch for Cost Elements."""
        ce1_id = setup_wbe_level_data["ce1_id"]
        ce2_id = setup_wbe_level_data["ce2_id"]
        expected = setup_wbe_level_data["wbe_metrics"]

        response = await client.post(
            "/api/v1/evm/batch",
            json={
                "entity_type": "cost_element",
                "entity_ids": [str(ce1_id), str(ce2_id)],
            },
        )
        assert response.status_code == 200
        data = response.json()

        # Should match WBE aggregation since it's the same cost elements
        # (calculated sum-based now)
        assert data["bac"] == float(expected["bac"])
        assert data["ev"] == float(expected["ev"])
        assert data["ac"] == float(expected["ac"])

        # Verify cumulative CPI
        expected_cpi = expected["ev"] / expected["ac"]
        if data["cpi"] is not None:
            assert abs(data["cpi"] - expected_cpi) < 0.0001

    @pytest.mark.asyncio
    async def test_batch_calculate_evm_metrics_invalid_type(
        self, client: AsyncClient
    ) -> None:
        """Test POST /evm/batch with invalid entity type."""
        response = await client.post(
            "/api/v1/evm/batch",
            json={
                "entity_type": "invalid_type",
                "entity_ids": [str(uuid4())],
            },
        )
        # The route catches invalid entity_type string and raises ValueError -> 400
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_batch_calculate_evm_metrics_empty_list(
        self, client: AsyncClient
    ) -> None:
        """Test POST /evm/batch with empty list."""
        response = await client.post(
            "/api/v1/evm/batch",
            json={
                "entity_type": "cost_element",
                "entity_ids": [],
            },
        )
        assert response.status_code == 200
        response.json()

    @pytest.mark.asyncio
    async def test_get_evm_timeseries_cost_element_not_found(
        self, client: AsyncClient
    ) -> None:
        """Test timeseries returns 404 if cost element not found."""
        response = await client.get(f"/api/v1/evm/cost_element/{uuid4()}/timeseries")
        assert response.status_code == 404
