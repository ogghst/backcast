
from collections.abc import Generator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.api.dependencies.auth import get_current_active_user, get_current_user
from app.core.rbac import RBACServiceABC, get_rbac_service
from app.main import app
from app.models.domain.project import Project
from app.models.domain.user import User

UTC = UTC

# Mock admin user for auth
mock_admin_user = User(
    id=uuid4(),
    user_id=uuid4(),
    email="admin@example.com",
    is_active=True,
    role="admin",
    full_name="Admin User",
    hashed_password="hash",
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
        return ["project-read", "project-create", "project-update", "project-delete"]

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
async def test_create_project_with_control_date_header(client, db_session):
    """API should accept X-Control-Date header and use it."""
    control_date = datetime(2026, 5, 5, 0, 0, 0, tzinfo=UTC)

    response = await client.post(
        "/api/v1/projects",
        json={
            "name": "Header Test",
            "code": "HDR-001",
            "budget": 50000,
            "start_date": datetime.now().isoformat(),
            "end_date": datetime.now().isoformat()
        },
        headers={"X-Control-Date": control_date.isoformat()}
    )

    assert response.status_code == 201
    data = response.json()
    project_id = data["project_id"]

    # Verify in DB
    # We need to wait for async write or ensure session is synced?
    # The client uses the same db_session via override in conftest.

    stmt = select(Project).where(Project.project_id == project_id)
    result = await db_session.execute(stmt)
    project = result.scalar_one()

    # Check valid_time matches control_date
    assert project.valid_time.lower == control_date

    # Transaction time should be NOW (2026-01-10)
    assert project.transaction_time.lower < control_date

@pytest.mark.asyncio
async def test_update_project_with_control_date_header(client, db_session):
    """Update via API with header should respect control date."""
    # Create project first (default date)
    create_resp = await client.post(
        "/api/v1/projects",
        json={
            "name": "Update Test",
            "code": "UPD-HDR-001",
            "budget": 50000
        }
    )
    assert create_resp.status_code == 201
    project_id = create_resp.json()["project_id"]

    # Update with control date
    control_date = datetime(2026, 6, 1, tzinfo=UTC)

    response = await client.put(
        f"/api/v1/projects/{project_id}",
        json={"name": "Updated Name API"},
        headers={"X-Control-Date": control_date.isoformat()}
    )

    assert response.status_code == 200

    # Verify DB
    # Should get the current version (HEAD)
    stmt = select(Project).where(
        Project.project_id == project_id,
        Project.name == "Updated Name API"
    )
    result = await db_session.execute(stmt)
    new_version = result.scalar_one()

    assert new_version.valid_time.lower == control_date

@pytest.mark.asyncio
async def test_delete_project_with_control_date_header(client, db_session):
    """Delete via API with header should respect control date."""
    create_resp = await client.post(
        "/api/v1/projects",
        json={
            "name": "Delete Test",
            "code": "DEL-HDR-001",
            "budget": 50000
        }
    )
    project_id = create_resp.json()["project_id"]

    control_date = datetime(2026, 7, 1, tzinfo=UTC)

    response = await client.delete(
        f"/api/v1/projects/{project_id}",
        headers={"X-Control-Date": control_date.isoformat()}
    )

    assert response.status_code == 204

    # Verify DB
    stmt = select(Project).where(Project.project_id == project_id).order_by(Project.valid_time.desc()).limit(1)
    result = await db_session.execute(stmt)
    project = result.scalar_one()

    assert project.deleted_at == control_date
