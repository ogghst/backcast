"""API tests for Change Order archive endpoint.

Tests the POST /api/v1/change-orders/{id}/archive endpoint to verify:
- Successful archival for Implemented/Rejected change orders
- Appropriate status codes (200, 404, 400)
- Error handling for invalid/non-existent change orders or incorrect states
"""

from collections.abc import Generator
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user, get_current_user
from app.core.rbac import RBACServiceABC, get_rbac_service
from app.main import app
from app.models.domain.user import User
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
            "change-order-archive",  # assuming this maps to update or delete
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
async def test_archive_implemented_change_order(
    client: AsyncClient, override_auth: None, db_session: AsyncSession
) -> None:
    """Test archive endpoint returns 200 for successful archive.

    ARRANGE: Create an Implemented change order
    ACT: Call POST /api/v1/change-orders/{id}/archive
    ASSERT: Response is 200 and branch is logically deleted
    """
    # Arrange - Setup services and IDs
    actor_id = mock_admin_user.user_id
    project_id = uuid4()
    co_code = f"CO-{uuid4().hex[:6].upper()}"
    source_branch = f"BR-{co_code}"

    co_service = ChangeOrderService(db_session)

    from app.models.schemas.change_order import ChangeOrderCreate

    create_schema = ChangeOrderCreate(
        project_id=project_id,
        code=co_code,
        title="To Be Archived",
        description="Testing Archive",
        status="Draft",
    )

    created_co = await co_service.create_change_order(
        change_order_in=create_schema, actor_id=actor_id
    )
    co_id = created_co.change_order_id

    # Force status to Implemented
    co = await co_service.get_current(co_id)
    assert co is not None
    co.status = "Implemented"
    db_session.add(co)
    await db_session.commit()
    await db_session.refresh(co)

    # Act - Call archive endpoint
    response = await client.post(f"/api/v1/change-orders/{co_id}/archive")

    # Assert - Response is 200
    assert response.status_code == 200
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Branch archived successfully"

    # Assert - Branch is hidden
    from sqlalchemy.exc import NoResultFound

    from app.services.branch_service import BranchService

    branch_service = BranchService(db_session)
    with pytest.raises(NoResultFound):
        await branch_service.get_by_name_and_project(source_branch, project_id)


@pytest.mark.asyncio
async def test_archive_active_change_order_fails(
    client: AsyncClient, override_auth: None, db_session: AsyncSession
) -> None:
    """Test archive endpoint returns 400 for active change orders.

    ARRANGE: Create a Draft change order
    ACT: Call POST /api/v1/change-orders/{id}/archive
    ASSERT: Response is 400
    """
    logger_id = mock_admin_user.user_id
    project_id = uuid4()
    co_code = f"CO-{uuid4().hex[:6].upper()}"

    co_service = ChangeOrderService(db_session)

    from app.models.schemas.change_order import ChangeOrderCreate

    create_schema = ChangeOrderCreate(
        project_id=project_id,
        code=co_code,
        title="Active CO",
        description="Should not archive",
        status="Draft",
    )

    created_co = await co_service.create_change_order(
        change_order_in=create_schema, actor_id=logger_id
    )
    co_id = created_co.change_order_id

    # Act - Call archive endpoint
    response = await client.post(f"/api/v1/change-orders/{co_id}/archive")

    # Assert - Response is 400
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "Cannot archive active Change Order" in data["detail"]
