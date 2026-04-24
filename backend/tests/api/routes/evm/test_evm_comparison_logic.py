from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
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


@pytest.mark.asyncio
class TestEVMCostComparisonLogic:
    async def test_cost_comparison_actual_maps_to_ac(self, client: AsyncClient) -> None:
        """Test that the 'actual' field in time series maps to Actual Cost (AC), not Earned Value (EV).

        And verifies valid_time (as_of) filtering.
        """
        # 1. Setup Data
        # Project
        proj_res = await client.post(
            "/api/v1/projects",
            json={
                "code": f"P-{uuid4().hex[:4].upper()}",
                "name": "Test Project",
            },
        )
        assert proj_res.status_code == 201
        project_id = proj_res.json()["project_id"]

        # WBE
        wbe_res = await client.post(
            "/api/v1/wbes",
            json={
                "code": f"W-{uuid4().hex[:4].upper()}",
                "name": "Test WBE",
                "project_id": project_id,
                "branch": "main",
            },
        )
        wbe_id = wbe_res.json()["wbe_id"]

        # Department
        dept_res = await client.post(
            "/api/v1/departments",
            json={"code": f"D-{uuid4().hex[:4].upper()}", "name": "Test Dept"},
        )
        dept_id = dept_res.json()["department_id"]

        # Type
        type_res = await client.post(
            "/api/v1/cost-element-types",
            json={
                "code": f"T-{uuid4().hex[:4].upper()}",
                "name": "Test Type",
                "department_id": dept_id,
            },
        )
        type_id = type_res.json()["cost_element_type_id"]

        # Cost Element
        ce_res = await client.post(
            "/api/v1/cost-elements",
            json={
                "code": f"CE-{uuid4().hex[:4].upper()}",
                "name": "Test CE",
                "budget_amount": 10000,
                "wbe_id": wbe_id,
                "cost_element_type_id": type_id,
                "branch": "main",
            },
        )
        cost_element_id = ce_res.json()["cost_element_id"]

        # 2. Add Cost Registrations at different times
        # We simulate adding costs at T2 and T2+10days
        # But we create them NOW, so valid_time is NOW.
        # Wait, if we want to test 'control_date' (as_of), we need entities to have valid_time.
        # The CostRegistration 'create' endpoint usually uses current server time for valid_time.
        # However, for testing, we can just create them sequentially.

        # Scenario:
        # Create Reg1 (Amount 1000)
        # Query at T1 (after Reg1). Should allow us to see Reg1.
        # Create Reg2 (Amount 2000).
        # Query at T2 (after Reg2). Should see Reg1 + Reg2.
        # Query at T1 AGAIN. Should only see Reg1. (Time Travel)

        # T1 Timestamp
        datetime.now(UTC)

        # Reg 1
        await client.post(
            "/api/v1/cost-registrations",
            json={
                "cost_element_id": cost_element_id,
                "amount": 1000,
                "description": "Cost T1",
                "registration_date": "2025-06-01T12:00:00Z",
            },
        )

        # Wait a bit to ensure distinct timestamps if needed, or rely on execution order.
        # But valid_time is set at transaction commit.

        # Capture timestamp after Reg1
        # We need to sleep briefly or use returned valid_time if available.
        # Or just take current time.
        import asyncio

        await asyncio.sleep(0.1)  # minimal delay
        t_after_reg1 = datetime.now(UTC)

        # Reg 2
        await client.post(
            "/api/v1/cost-registrations",
            json={
                "cost_element_id": cost_element_id,
                "amount": 2000,
                "description": "Cost T2",
                "registration_date": "2025-07-01T12:00:00Z",
            },
        )

        t_after_reg2 = datetime.now(UTC)

        # 3. Time Series Queries

        # Query AS OF t_after_reg1
        # Should see only Reg1 (1000)
        res_t1 = await client.get(
            f"/api/v1/evm/cost_element/{cost_element_id}/timeseries",
            params={"control_date": t_after_reg1.isoformat(), "granularity": "month"},
        )
        assert res_t1.status_code == 200
        data_t1 = res_t1.json()

        # Find June point (Reg1 date)
        points_t1 = data_t1["points"]
        # The AC should be 1000 for June and future months (flatline)

        # Find July point (future relative to control_date 2026-06-XX if we query June?)
        # Actually our t_after_reg1 is likely today/now.
        # But for the system, Reg1 is valid from now.
        # Wait, Time Travel works on Valid Time.
        # If I query as_of t_after_reg1, Reg2 (created later) should NOT exist.

        # Let's verify that AC is 1000 in the last point
        last_ac_t1 = points_t1[-1]["ac"]
        last_actual_t1 = points_t1[-1]["actual"]

        print(
            f"\nDEBUG: T1 Query (After Reg1): AC={last_ac_t1}, Actual={last_actual_t1}"
        )

        assert float(last_ac_t1) == 1000.0, f"Expected AC 1000 at T1, got {last_ac_t1}"
        assert float(last_actual_t1) == 1000.0, (
            f"Expected Actual 1000 at T1, got {last_actual_t1}"
        )

        # Query AS OF t_after_reg2
        res_t2 = await client.get(
            f"/api/v1/evm/cost_element/{cost_element_id}/timeseries",
            params={"control_date": t_after_reg2.isoformat(), "granularity": "month"},
        )
        data_t2 = res_t2.json()
        points_t2 = data_t2["points"]

        last_ac_t2 = points_t2[-1]["ac"]
        last_actual_t2 = points_t2[-1]["actual"]

        print(f"DEBUG: T2 Query (After Reg2): AC={last_ac_t2}, Actual={last_actual_t2}")

        assert float(last_ac_t2) == 3000.0, f"Expected AC 3000 at T2, got {last_ac_t2}"
        assert float(last_actual_t2) == 3000.0, (
            f"Expected Actual 3000 at T2, got {last_actual_t2}"
        )

        # 4. Check 'actual' mapping
        # If 'actual' maps to Actual Cost, it should match 'ac'.
        # If it maps to EV, it will be 0 (no progress).

        assert float(last_actual_t1) == float(last_ac_t1), (
            f"Actual field ({last_actual_t1}) should match AC ({last_ac_t1})"
        )
