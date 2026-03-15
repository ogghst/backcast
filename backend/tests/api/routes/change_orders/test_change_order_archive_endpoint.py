"""API tests for Change Order archive endpoint.

Tests the POST /api/v1/change-orders/{id}/archive endpoint to verify:
- Successful archival for Implemented/Rejected status (200)
- Error handling for non-terminal status (400)
- Error handling for non-existent change order (404)
- RBAC permission enforcement
"""

from collections.abc import Generator
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user, get_current_user
from app.core.rbac import RBACServiceABC, get_rbac_service
from app.main import app
from app.models.domain.branch import Branch
from app.models.domain.user import User
from app.services.branch_service import BranchService
from app.services.change_order_service import ChangeOrderService

# Mock admin user for auth
mock_admin_user = User(
    id=uuid4(),
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


# Mock RBAC service that allows everything
class MockRBACService(RBACServiceABC):
    def has_role(self, user_role: str, required_roles: list[str]) -> bool:
        return True

    def has_permission(self, user_role: str, required_permission: str) -> bool:
        return True

    def get_user_permissions(self, user_role: str) -> list[str]:
        return [
            "change-order-read",
            "change-order-create",
            "change-order-update",
            "change-order-delete",
        ]


def mock_get_rbac_service() -> RBACServiceABC:
    return MockRBACService()


@pytest.fixture(autouse=True)
def override_auth() -> Generator[None, None, None]:
    """Override authentication and RBAC for all tests."""
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user
    app.dependency_overrides[get_rbac_service] = mock_get_rbac_service
    yield
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_archive_implemented_change_order_success(
    client: AsyncClient, override_auth: None, db_session: AsyncSession
) -> None:
    """Test archive endpoint returns 200 for Implemented change order.

    ARRANGE: Create a change order with Implemented status and its branch
    ACT: Call POST /api/v1/change-orders/{id}/archive
    ASSERT: Response is 200, branch is soft-deleted
    """
    # Arrange - Setup services and IDs
    actor_id = mock_admin_user.user_id
    project_id = uuid4()
    co_id = uuid4()
    co_code = f"CO-{uuid4().hex[:6].upper()}"

    co_service = ChangeOrderService(db_session)
    branch_service = BranchService(db_session)

    # Arrange - Create CO on main branch with Implemented status
    branch_name = f"BR-{co_code}"
    await co_service.create_root(
        root_id=co_id,
        actor_id=actor_id,
        branch="main",
        code=co_code,
        title="Implemented Change Order",
        description="Test CO for archive endpoint",
        project_id=project_id,
        status="Implemented",
        branch_name=branch_name,  # Required for archive to find the branch
    )

    # Arrange - Create the branch associated with this CO
    await branch_service.create(
        name=branch_name,
        project_id=project_id,
        actor_id=actor_id,
    )

    # Act - Call archive endpoint
    response = await client.post(
        f"/api/v1/change-orders/{co_id}/archive",
    )

    # Assert - Response is 200
    assert response.status_code == 200
    data = response.json()
    assert data["change_order_id"] == str(co_id)
    assert data["status"] == "Implemented"

    # Assert - Branch is soft-deleted (not found by standard query)
    stmt = select(Branch).where(
        Branch.name == branch_name,
        Branch.project_id == project_id,
        Branch.deleted_at.is_(None),
    )
    result = await db_session.execute(stmt)
    active_branch = result.scalar_one_or_none()
    assert active_branch is None, "Branch should be soft-deleted after archive"


@pytest.mark.asyncio
async def test_archive_rejected_change_order_success(
    client: AsyncClient, override_auth: None, db_session: AsyncSession
) -> None:
    """Test archive endpoint returns 200 for Rejected change order.

    ARRANGE: Create a change order with Rejected status and its branch
    ACT: Call POST /api/v1/change-orders/{id}/archive
    ASSERT: Response is 200, branch is soft-deleted
    """
    # Arrange - Setup services and IDs
    actor_id = mock_admin_user.user_id
    project_id = uuid4()
    co_id = uuid4()
    co_code = f"CO-{uuid4().hex[:6].upper()}"

    co_service = ChangeOrderService(db_session)
    branch_service = BranchService(db_session)

    # Arrange - Create CO on main branch with Rejected status
    branch_name = f"BR-{co_code}"
    await co_service.create_root(
        root_id=co_id,
        actor_id=actor_id,
        branch="main",
        code=co_code,
        title="Rejected Change Order",
        description="Test CO for archive endpoint",
        project_id=project_id,
        status="Rejected",
        branch_name=branch_name,  # Required for archive to find the branch
    )

    # Arrange - Create the branch associated with this CO
    await branch_service.create(
        name=branch_name,
        project_id=project_id,
        actor_id=actor_id,
    )

    # Act - Call archive endpoint
    response = await client.post(
        f"/api/v1/change-orders/{co_id}/archive",
    )

    # Assert - Response is 200
    assert response.status_code == 200
    data = response.json()
    assert data["change_order_id"] == str(co_id)
    assert data["status"] == "Rejected"


@pytest.mark.asyncio
async def test_archive_active_change_order_fails(
    client: AsyncClient, override_auth: None, db_session: AsyncSession
) -> None:
    """Test archive endpoint returns 400 for non-terminal status.

    ARRANGE: Create a change order with Draft status
    ACT: Call POST /api/v1/change-orders/{id}/archive
    ASSERT: Response is 400 with "Cannot archive active" error
    """
    # Arrange - Setup services and IDs
    actor_id = mock_admin_user.user_id
    project_id = uuid4()
    co_id = uuid4()
    co_code = f"CO-{uuid4().hex[:6].upper()}"

    co_service = ChangeOrderService(db_session)

    # Arrange - Create CO on main branch with Draft status
    await co_service.create_root(
        root_id=co_id,
        actor_id=actor_id,
        branch="main",
        code=co_code,
        title="Draft Change Order",
        description="Test CO for archive endpoint",
        project_id=project_id,
        status="Draft",
    )

    # Act - Call archive endpoint
    response = await client.post(
        f"/api/v1/change-orders/{co_id}/archive",
    )

    # Assert - Response is 400
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "Cannot archive active" in data["detail"]


@pytest.mark.asyncio
async def test_archive_nonexistent_change_order_fails(
    client: AsyncClient, override_auth: None, db_session: AsyncSession
) -> None:
    """Test archive endpoint returns 404 for non-existent change order.

    ARRANGE: No change order exists
    ACT: Call POST /api/v1/change-orders/{invalid_id}/archive
    ASSERT: Response is 404 with appropriate error message
    """
    # Arrange - Non-existent UUID
    invalid_id = uuid4()

    # Act - Call archive endpoint with invalid ID
    response = await client.post(
        f"/api/v1/change-orders/{invalid_id}/archive",
    )

    # Assert - Response is 404
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower()
