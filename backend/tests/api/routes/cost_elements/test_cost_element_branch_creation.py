"""Test for cost element branch creation bug (GitHub Issue #XXX).

This test reproduces the issue where cost elements were being created in the
'main' branch even when the user was viewing a different branch (e.g., CO branch).

The bug was caused by the CostElementCreate schema having a default value for
the 'branch' field set to 'main', which would override the frontend's branch value.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.cost_element import CostElement


@pytest.mark.asyncio
async def test_create_cost_element_in_non_main_branch_no_default(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Test that cost element is created in specified branch, not defaulting to main.

    Regression test for bug where cost elements created while viewing a CO branch
    were incorrectly saved to 'main' due to schema default value.

    The test verifies:
    1. Element is created in the specified branch ('BR-CO-2026-001')
    2. Element does NOT exist in 'main' branch
    3. branch field in request body is respected
    """
    # Setup dependencies
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
                "cost-element-create",
                "project-create",
                "wbe-create",
                "department-create",
                "cost-element-type-create",
            ]

    def mock_get_rbac_service() -> MockRBACService:
        return MockRBACService()

    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user
    app.dependency_overrides[get_rbac_service] = mock_get_rbac_service

    try:
        # 1. Create dependencies (Department, Type, Project, WBE)
        dept_res = await client.post(
            "/api/v1/departments",
            json={"code": f"D-{uuid4().hex[:4].upper()}", "name": "Test Dept"},
        )
        dept_id = dept_res.json()["department_id"]

        type_res = await client.post(
            "/api/v1/cost-element-types",
            json={
                "code": f"T-{uuid4().hex[:4].upper()}",
                "name": "Test Type",
                "department_id": dept_id,
            },
        )
        type_id = type_res.json()["cost_element_type_id"]

        proj_res = await client.post(
            "/api/v1/projects",
            json={
                "code": f"P-{uuid4().hex[:4].upper()}",
                "name": "Test Project",
                "budget": 100000,
            },
        )
        proj_id = proj_res.json()["project_id"]

        wbe_res = await client.post(
            "/api/v1/wbes",
            json={
                "code": f"W-{uuid4().hex[:4].upper()}",
                "name": "Test WBE",
                "project_id": proj_id,
            },
        )
        wbe_id = wbe_res.json()["wbe_id"]

        # 2. Create cost element in CO branch
        co_branch = "BR-CO-2026-001"
        element_data = {
            "code": f"CE-{uuid4().hex[:4].upper()}",
            "name": "CO Branch Element",
            "budget_amount": 5000.00,
            "wbe_id": wbe_id,
            "cost_element_type_id": type_id,
            "branch": co_branch,  # Explicitly set branch
        }

        create_res = await client.post("/api/v1/cost-elements", json=element_data)
        assert create_res.status_code == 201
        created_element = create_res.json()
        element_id = created_element["cost_element_id"]

        # 3. Verify element was created in CO branch (not main)
        assert created_element["branch"] == co_branch, (
            f"Expected element to be in '{co_branch}' branch, "
            f"but got '{created_element['branch']}'"
        )

        # 4. Query database directly to confirm branch assignment
        stmt = select(CostElement).where(
            CostElement.cost_element_id == element_id,
            CostElement.branch == co_branch,
        )
        result = await db_session.execute(stmt)
        co_element = result.scalar_one_or_none()

        assert co_element is not None, (
            f"Cost element should exist in '{co_branch}' branch in database"
        )
        assert co_element.branch == co_branch

        # 5. Verify element does NOT exist in main branch
        stmt_main = select(CostElement).where(
            CostElement.cost_element_id == element_id,
            CostElement.branch == "main",
        )
        result_main = await db_session.execute(stmt_main)
        main_element = result_main.scalar_one_or_none()

        assert main_element is None, (
            f"Cost element should NOT exist in 'main' branch when created in '{co_branch}'"
        )

    finally:
        app.dependency_overrides = {}
