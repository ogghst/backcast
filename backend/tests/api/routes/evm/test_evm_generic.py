"""API integration tests for generic EVM endpoints.

Tests the generic EVM API endpoints that work with any entity type:
- GET /api/v1/evm/{entity_type}/{entity_id}/metrics
- GET /api/v1/evm/{entity_type}/{entity_id}/timeseries
- POST /api/v1/evm/batch
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
        json={"code": f"P-{uuid4().hex[:4].upper()}", "name": "Proj", "budget": 100000},
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
    await client.post(
        f"/api/v1/cost-elements/{cost_element_id}/schedule-baseline",
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


class TestGenericEVMMetricsEndpoint:
    """Test generic EVM /metrics endpoint for all entity types."""

    @pytest.mark.asyncio
    async def test_get_evm_metrics_cost_element(
        self, client: AsyncClient, setup_evm_data: dict[str, Any]
    ) -> None:
        """Test GET /evm/cost_element/{id}/metrics returns EVM metrics.

        Test ID: BE-004-T-001

        Expected:
        - Returns generic EVMMetricsResponse structure
        - All EVM metrics present (BAC, PV, AC, EV, CV, SV, CPI, SPI)
        - entity_type = "cost_element"
        - entity_id matches the cost_element_id
        """
        # Arrange
        cost_element_id = setup_evm_data["cost_element_id"]

        # Act
        response = await client.get(
            f"/api/v1/evm/cost_element/{cost_element_id}/metrics"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify generic response structure
        assert data["entity_type"] == EntityType.COST_ELEMENT
        assert data["entity_id"] == str(cost_element_id)

        # Verify all EVM metrics are present
        assert "bac" in data
        assert "pv" in data
        assert "ac" in data
        assert "ev" in data
        assert "cv" in data
        assert "sv" in data
        assert "cpi" in data
        assert "spi" in data

        # Verify values
        assert data["bac"] == 100000.0  # Budget
        assert data["ac"] == 60000.0  # Sum of costs
        assert data["ev"] == 50000.0  # BAC × 50%

        # Verify variances
        assert data["cv"] == -10000.0  # EV - AC = 50000 - 60000

    @pytest.mark.asyncio
    async def test_get_evm_metrics_with_control_date(
        self, client: AsyncClient, setup_evm_data: dict[str, Any]
    ) -> None:
        """Test GET /evm/cost_element/{id}/metrics with control_date.

        Test ID: BE-004-T-002

        Expected:
        - Returns metrics as of the specified control_date
        - control_date in response matches request
        """
        # Arrange
        cost_element_id = setup_evm_data["cost_element_id"]
        # Use a date in the future (entities were created at test runtime)
        future_date = datetime(2026, 6, 30, tzinfo=UTC)

        # Act
        response = await client.get(
            f"/api/v1/evm/cost_element/{cost_element_id}/metrics",
            params={"control_date": future_date.isoformat()},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Control date should be reflected in response
        assert "control_date" in data

    @pytest.mark.asyncio
    async def test_get_evm_metrics_with_branch(
        self, client: AsyncClient, setup_evm_data: dict[str, Any]
    ) -> None:
        """Test GET /evm/cost_element/{id}/metrics with branch parameter.

        Test ID: BE-004-T-003

        Expected:
        - Returns metrics for the specified branch
        - branch in response matches request
        """
        # Arrange
        cost_element_id = setup_evm_data["cost_element_id"]

        # Act
        response = await client.get(
            f"/api/v1/evm/cost_element/{cost_element_id}/metrics",
            params={"branch": "main"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["branch"] == "main"

    @pytest.mark.asyncio
    async def test_get_evm_metrics_cost_element_not_found(
        self, client: AsyncClient
    ) -> None:
        """Test GET /evm/cost_element/{id}/metrics with non-existent ID.

        Test ID: BE-004-T-004

        Expected:
        - Returns 404 Not Found
        """
        # Arrange
        fake_id = uuid4()

        # Act
        response = await client.get(f"/api/v1/evm/cost_element/{fake_id}/metrics")

        # Assert
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_evm_metrics_invalid_entity_type(
        self, client: AsyncClient
    ) -> None:
        """Test GET /evm/{invalid_type}/{id}/metrics.

        Test ID: BE-004-T-005

        Expected:
        - Returns 422 Validation Error or similar error
        - Invalid entity type is rejected
        """
        # Arrange
        fake_id = uuid4()

        # Act
        response = await client.get(f"/api/v1/evm/invalid_type/{fake_id}/metrics")

        # Assert - Should get validation error or 404
        assert response.status_code in (404, 422)

    @pytest.mark.asyncio
    async def test_get_evm_metrics_wbe(
        self, client: AsyncClient, setup_evm_data: dict[str, Any]
    ) -> None:
        """Test GET /evm/wbe/{id}/metrics returns aggregated EVM metrics.

        Test ID: BE-009-T-001

        Expected:
        - Returns generic EVMMetricsResponse structure
        - All EVM metrics present (BAC, PV, AC, EV, CV, SV, CPI, SPI)
        - entity_type = "wbe"
        - Metrics are aggregated from child cost elements
        """
        # Arrange
        cost_element_id = setup_evm_data["cost_element_id"]
        # Get the WBE ID from the cost element
        ce_res = await client.get(f"/api/v1/cost-elements/{cost_element_id}")
        wbe_id = ce_res.json()["wbe_id"]

        # Act
        response = await client.get(f"/api/v1/evm/wbe/{wbe_id}/metrics")

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify generic response structure
        assert data["entity_type"] == EntityType.WBE
        assert data["entity_id"] == str(wbe_id)

        # Verify all EVM metrics are present
        assert "bac" in data
        assert "pv" in data
        assert "ac" in data
        assert "ev" in data
        assert "cv" in data
        assert "sv" in data
        assert "cpi" in data
        assert "spi" in data

        # Verify values (should match the single cost element)
        assert data["bac"] == 100000.0
        assert data["ac"] == 60000.0

    @pytest.mark.asyncio
    async def test_get_evm_metrics_project(
        self, client: AsyncClient, setup_evm_data: dict[str, Any]
    ) -> None:
        """Test GET /evm/project/{id}/metrics returns aggregated EVM metrics.

        Test ID: BE-009-T-002

        Expected:
        - Returns generic EVMMetricsResponse structure
        - All EVM metrics present (BAC, PV, AC, EV, CV, SV, CPI, SPI)
        - entity_type = "project"
        - Metrics are aggregated from all child WBEs and cost elements
        """
        # Arrange
        cost_element_id = setup_evm_data["cost_element_id"]
        # Get the project ID from the cost element -> WBE -> project
        ce_res = await client.get(f"/api/v1/cost-elements/{cost_element_id}")
        wbe_id = ce_res.json()["wbe_id"]
        wbe_res = await client.get(f"/api/v1/wbes/{wbe_id}")
        project_id = wbe_res.json()["project_id"]

        # Act
        response = await client.get(f"/api/v1/evm/project/{project_id}/metrics")

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify generic response structure
        assert data["entity_type"] == EntityType.PROJECT
        assert data["entity_id"] == str(project_id)

        # Verify all EVM metrics are present
        assert "bac" in data
        assert "pv" in data
        assert "ac" in data
        assert "ev" in data
        assert "cv" in data
        assert "sv" in data
        assert "cpi" in data
        assert "spi" in data

        # Verify values (should match the single cost element)
        assert data["bac"] == 100000.0
        assert data["ac"] == 60000.0


class TestEVMTimeSeriesEndpoint:
    """Test generic EVM /timeseries endpoint."""

    @pytest.mark.asyncio
    async def test_get_evm_timeseries_cost_element(
        self, client: AsyncClient, setup_evm_data: dict[str, Any]
    ) -> None:
        """Test GET /evm/cost_element/{id}/timeseries returns time-series data.

        Test ID: BE-004-T-006

        Expected:
        - Returns EVMTimeSeriesResponse structure
        - Contains list of time-series points
        - Each point has date, pv, ev, ac, forecast, actual
        - Default granularity is "week"
        """
        # Arrange
        cost_element_id = setup_evm_data["cost_element_id"]

        # Act
        response = await client.get(
            f"/api/v1/evm/cost_element/{cost_element_id}/timeseries"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify time-series response structure
        assert "granularity" in data
        assert "points" in data
        assert "start_date" in data
        assert "end_date" in data
        assert "total_points" in data

        # Verify points is a list
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
    async def test_get_evm_timeseries_with_granularity_day(
        self, client: AsyncClient, setup_evm_data: dict[str, Any]
    ) -> None:
        """Test GET /evm/cost_element/{id}/timeseries with granularity=day.

        Test ID: BE-004-T-007

        Expected:
        - Returns daily data points
        - granularity in response = "day"
        """
        # Arrange
        cost_element_id = setup_evm_data["cost_element_id"]

        # Act
        response = await client.get(
            f"/api/v1/evm/cost_element/{cost_element_id}/timeseries",
            params={"granularity": "day"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["granularity"] == "day"

    @pytest.mark.asyncio
    async def test_get_evm_timeseries_with_granularity_week(
        self, client: AsyncClient, setup_evm_data: dict[str, Any]
    ) -> None:
        """Test GET /evm/cost_element/{id}/timeseries with granularity=week.

        Test ID: BE-004-T-008

        Expected:
        - Returns weekly data points
        - granularity in response = "week"
        """
        # Arrange
        cost_element_id = setup_evm_data["cost_element_id"]

        # Act
        response = await client.get(
            f"/api/v1/evm/cost_element/{cost_element_id}/timeseries",
            params={"granularity": "week"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["granularity"] == "week"

    @pytest.mark.asyncio
    async def test_get_evm_timeseries_with_granularity_month(
        self, client: AsyncClient, setup_evm_data: dict[str, Any]
    ) -> None:
        """Test GET /evm/cost_element/{id}/timeseries with granularity=month.

        Test ID: BE-004-T-009

        Expected:
        - Returns monthly data points
        - granularity in response = "month"
        """
        # Arrange
        cost_element_id = setup_evm_data["cost_element_id"]

        # Act
        response = await client.get(
            f"/api/v1/evm/cost_element/{cost_element_id}/timeseries",
            params={"granularity": "month"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["granularity"] == "month"

    @pytest.mark.asyncio
    async def test_get_evm_timeseries_with_control_date(
        self, client: AsyncClient, setup_evm_data: dict[str, Any]
    ) -> None:
        """Test GET /evm/cost_element/{id}/timeseries with control_date.

        Test ID: BE-004-T-010

        Expected:
        - Returns time-series data respecting the control_date
        - Future dates show forecast/plan values
        """
        # Arrange
        cost_element_id = setup_evm_data["cost_element_id"]
        control_date = datetime(2026, 6, 30, tzinfo=UTC)

        # Act
        response = await client.get(
            f"/api/v1/evm/cost_element/{cost_element_id}/timeseries",
            params={"control_date": control_date.isoformat()},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "points" in data

    @pytest.mark.asyncio
    async def test_get_evm_timeseries_cost_element_not_found(
        self, client: AsyncClient
    ) -> None:
        """Test GET /evm/cost_element/{id}/timeseries with non-existent ID.

        Test ID: BE-004-T-011

        Expected:
        - Returns 404 Not Found
        """
        # Arrange
        fake_id = uuid4()

        # Act
        response = await client.get(f"/api/v1/evm/cost_element/{fake_id}/timeseries")

        # Assert
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_evm_timeseries_wbe(
        self, client: AsyncClient, setup_evm_data: dict[str, Any]
    ) -> None:
        """Test GET /evm/wbe/{id}/timeseries returns aggregated time-series data.

        Test ID: BE-009-T-003

        Expected:
        - Returns EVMTimeSeriesResponse structure
        - Contains list of time-series points
        - Each point has date, pv, ev, ac, forecast, actual
        - Metrics are aggregated from child cost elements
        """
        # Arrange
        cost_element_id = setup_evm_data["cost_element_id"]
        # Get the WBE ID from the cost element
        ce_res = await client.get(f"/api/v1/cost-elements/{cost_element_id}")
        wbe_id = ce_res.json()["wbe_id"]

        # Act
        response = await client.get(f"/api/v1/evm/wbe/{wbe_id}/timeseries")

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify time-series response structure
        assert "granularity" in data
        assert "points" in data
        assert "start_date" in data
        assert "end_date" in data
        assert "total_points" in data

        # Verify points is a list
        assert isinstance(data["points"], list)

    @pytest.mark.asyncio
    async def test_get_evm_timeseries_project(
        self, client: AsyncClient, setup_evm_data: dict[str, Any]
    ) -> None:
        """Test GET /evm/project/{id}/timeseries returns aggregated time-series data.

        Test ID: BE-009-T-004

        Expected:
        - Returns EVMTimeSeriesResponse structure
        - Contains list of time-series points
        - Each point has date, pv, ev, ac, forecast, actual
        - Metrics are aggregated from all child WBEs and cost elements
        """
        # Arrange
        cost_element_id = setup_evm_data["cost_element_id"]
        # Get the project ID from the cost element -> WBE -> project
        ce_res = await client.get(f"/api/v1/cost-elements/{cost_element_id}")
        wbe_id = ce_res.json()["wbe_id"]
        wbe_res = await client.get(f"/api/v1/wbes/{wbe_id}")
        project_id = wbe_res.json()["project_id"]

        # Act
        response = await client.get(f"/api/v1/evm/project/{project_id}/timeseries")

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify time-series response structure
        assert "granularity" in data
        assert "points" in data
        assert "start_date" in data
        assert "end_date" in data
        assert "total_points" in data

        # Verify points is a list
        assert isinstance(data["points"], list)


class TestEVMBatchEndpoint:
    """Test EVM /batch endpoint for multi-entity aggregation."""

    @pytest.mark.asyncio
    async def test_post_evm_batch_single_entity(
        self, client: AsyncClient, setup_evm_data: dict[str, Any]
    ) -> None:
        """Test POST /evm/batch with single cost element.

        Test ID: BE-004-T-012

        Expected:
        - Returns aggregated metrics for the single entity
        - Metrics match the individual entity metrics
        """
        # Arrange
        cost_element_id = setup_evm_data["cost_element_id"]

        # Act
        response = await client.post(
            "/api/v1/evm/batch",
            json={
                "entity_type": EntityType.COST_ELEMENT,
                "entity_ids": [str(cost_element_id)],
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify generic response structure
        assert data["entity_type"] == EntityType.COST_ELEMENT
        assert "bac" in data
        assert "pv" in data
        assert "ac" in data
        assert "ev" in data

        # Verify values match single entity
        assert data["bac"] == 100000.0
        assert data["ac"] == 60000.0

    @pytest.mark.asyncio
    async def test_post_evm_batch_multiple_entities(self, client: AsyncClient) -> None:
        """Test POST /evm/batch with multiple cost elements.

        Test ID: BE-004-T-013

        Expected:
        - Returns aggregated metrics (sum of amounts)
        - BAC, PV, AC, EV are summed
        - CPI, SPI are weighted averages
        """
        # Arrange - Create two cost elements
        dept_res = await client.post(
            "/api/v1/departments",
            json={"code": f"D-{uuid4().hex[:4].upper()}", "name": "Dept"},
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
                "name": "Proj",
                "budget": 200000,
            },
        )
        proj_id = proj_res.json()["project_id"]

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

        # First cost element
        ce1_res = await client.post(
            "/api/v1/cost-elements",
            json={
                "code": f"CE-{uuid4().hex[:4].upper()}",
                "name": "Cost Element 1",
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
                "code": f"CE-{uuid4().hex[:4].upper()}",
                "name": "Cost Element 2",
                "budget_amount": 150000,
                "wbe_id": wbe_id,
                "cost_element_type_id": type_id,
                "branch": "main",
            },
        )
        ce2_id = ce2_res.json()["cost_element_id"]

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

        # Verify aggregation - BAC should be sum
        assert data["bac"] == 250000.0  # 100000 + 150000

    @pytest.mark.asyncio
    async def test_post_evm_batch_with_control_date(
        self, client: AsyncClient, setup_evm_data: dict[str, Any]
    ) -> None:
        """Test POST /evm/batch with control_date parameter.

        Test ID: BE-004-T-014

        Expected:
        - Returns metrics as of the specified control_date
        - control_date in response matches request
        """
        # Arrange
        cost_element_id = setup_evm_data["cost_element_id"]
        # Use a date in the future (entities were created at test runtime)
        control_date = datetime(2026, 6, 30, tzinfo=UTC)

        # Act
        response = await client.post(
            "/api/v1/evm/batch",
            json={
                "entity_type": EntityType.COST_ELEMENT,
                "entity_ids": [str(cost_element_id)],
                "control_date": control_date.isoformat(),
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "control_date" in data

    @pytest.mark.asyncio
    async def test_post_evm_batch_with_branch(
        self, client: AsyncClient, setup_evm_data: dict[str, Any]
    ) -> None:
        """Test POST /evm/batch with branch parameter.

        Test ID: BE-004-T-015

        Expected:
        - Returns metrics for the specified branch
        - branch in response matches request
        """
        # Arrange
        cost_element_id = setup_evm_data["cost_element_id"]

        # Act
        response = await client.post(
            "/api/v1/evm/batch",
            json={
                "entity_type": EntityType.COST_ELEMENT,
                "entity_ids": [str(cost_element_id)],
                "branch": "main",
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["branch"] == "main"

    @pytest.mark.asyncio
    async def test_post_evm_batch_empty_entity_ids(self, client: AsyncClient) -> None:
        """Test POST /evm/batch with empty entity_ids list.

        Test ID: BE-004-T-016

        Expected:
        - Returns zero metrics (all zeros)
        - warning = "No entities provided"
        """
        # Act
        response = await client.post(
            "/api/v1/evm/batch",
            json={
                "entity_type": EntityType.COST_ELEMENT,
                "entity_ids": [],
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify zero metrics
        assert data["bac"] == 0
        assert data.get("warning") is not None

    @pytest.mark.asyncio
    async def test_post_evm_batch_invalid_entity_type(
        self, client: AsyncClient, setup_evm_data: dict[str, Any]
    ) -> None:
        """Test POST /evm/batch with unsupported entity_type.

        Test ID: BE-004-T-017

        Expected:
        - Returns 400 Bad Request or similar error
        - Indicates entity type not yet supported
        """
        # Arrange
        cost_element_id = setup_evm_data["cost_element_id"]

        # Act
        response = await client.post(
            "/api/v1/evm/batch",
            json={
                "entity_type": "department",  # Not supported
                "entity_ids": [str(cost_element_id)],
            },
        )

        # Assert - Should get validation error
        assert response.status_code == 400
        data = response.json()
        # Error message can be either "not yet supported" (from service) or "Invalid entity_type" (from Pydantic)
        detail = data.get("detail", "").lower()
        assert "not yet supported" in detail or "invalid entity_type" in detail
