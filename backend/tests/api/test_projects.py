"""Integration tests for Project API endpoints."""

from collections.abc import Generator
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user, get_current_user
from app.core.rbac import RBACServiceABC, get_rbac_service
from app.main import app
from app.models.domain.user import User

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
            "project-read",
            "project-create",
            "project-update",
            "project-delete",
            "wbe-read",
            "wbe-create",
            "wbe-update",
            "wbe-delete",
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
async def test_create_project(
    client: AsyncClient, override_auth: None, db_session: AsyncSession
) -> None:
    """Test creating a new project."""
    unique_code = f"TEST-{uuid4().hex[:6].upper()}"
    project_data = {
        "name": "Test Project",
        "code": unique_code,
        "budget": 100000,
        "contract_value": 120000,
        "status": "planning",
        "description": "A test project",
    }

    response = await client.post("/api/v1/projects", json=project_data)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Project"
    assert data["code"] == unique_code
    assert float(data["budget"]) == 100000
    assert data["branch"] == "main"
    assert "id" in data
    assert "project_id" in data


@pytest.mark.asyncio
async def test_create_project_duplicate_code(
    client: AsyncClient, override_auth: None, db_session: AsyncSession
) -> None:
    """Test creating project with duplicate code fails."""
    unique_code = f"DUP-{uuid4().hex[:6].upper()}"
    project_data = {
        "name": "Test Project 1",
        "code": unique_code,
        "budget": 100000,
    }

    # Create first project
    response1 = await client.post("/api/v1/projects", json=project_data)
    assert response1.status_code == 201

    # Try to create duplicate
    project_data["name"] = "Test Project 2"
    response2 = await client.post("/api/v1/projects", json=project_data)
    assert response2.status_code == 400
    assert "already exists" in response2.json()["detail"]


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_get_projects(
    client: AsyncClient, override_auth: None, db_session: AsyncSession
) -> None:
    """Test retrieving list of projects."""
    # Create test projects
    for i in range(3):
        project_data = {
            "name": f"Project {i}",
            "code": f"PRJ-{i:03d}",
            "budget": 100000 * (i + 1),
        }
        await client.post("/api/v1/projects", json=project_data)

    # Get all projects
    response = await client.get("/api/v1/projects")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert any(p["code"] == "PRJ-000" for p in data)


@pytest.mark.asyncio
async def test_get_project_by_id(
    client: AsyncClient, override_auth: None, db_session: AsyncSession
) -> None:
    """Test retrieving a specific project."""
    # Create project
    project_data = {
        "name": "Specific Project",
        "code": "SPEC-001",
        "budget": 50000,
    }
    create_response = await client.post("/api/v1/projects", json=project_data)
    project_id = create_response.json()["project_id"]

    # Get specific project
    response = await client.get(f"/api/v1/projects/{project_id}")
    if response.status_code != 200:
        all_projects = (await client.get("/api/v1/projects")).json()
        print(f"DEBUG: 404 for {project_id}, found {len(all_projects)} projects.")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Specific Project"
    assert data["code"] == "SPEC-001"


@pytest.mark.asyncio
async def test_update_project(
    client: AsyncClient, override_auth: None, db_session: AsyncSession
) -> None:
    """Test updating a project creates new version."""
    # Create project
    project_data = {
        "name": "Original Name",
        "code": "UPD-001",
        "budget": 100000,
    }
    create_response = await client.post("/api/v1/projects", json=project_data)
    project_id = create_response.json()["project_id"]

    # Update project
    update_data = {
        "name": "Updated Name",
        "budget": 150000,
    }
    response = await client.put(f"/api/v1/projects/{project_id}", json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert float(data["budget"]) == 150000
    assert data["code"] == "UPD-001"  # Code should remain unchanged


@pytest.mark.asyncio
async def test_delete_project(
    client: AsyncClient, override_auth: None, db_session: AsyncSession
) -> None:
    """Test soft deleting a project."""
    # Create project
    project_data = {
        "name": "To Delete",
        "code": "DEL-001",
        "budget": 50000,
    }
    create_response = await client.post("/api/v1/projects", json=project_data)
    project_id = create_response.json()["project_id"]

    # Delete project
    response = await client.delete(f"/api/v1/projects/{project_id}")

    assert response.status_code == 204

    # Verify project is not in list
    list_response = await client.get("/api/v1/projects")
    projects = list_response.json()
    assert not any(p["code"] == "DEL-001" for p in projects)


@pytest.mark.asyncio
async def test_get_project_history(
    client: AsyncClient, override_auth: None, db_session: AsyncSession
) -> None:
    # Insert mock admin user into DB so the join works
    from app.models.domain.user import User

    stmt = select(User).where(User.user_id == mock_admin_user.user_id)
    existing_user = (await db_session.execute(stmt)).scalar_one_or_none()
    if not existing_user:
        db_session.add(mock_admin_user)
        # We need to manually flush/commit because we are in a transaction-managed session
        await db_session.flush()

    # Create project
    project_data = {
        "name": "History Project",
        "code": "HIST-001",
        "budget": 100000,
    }
    create_response = await client.post("/api/v1/projects", json=project_data)
    project_id = create_response.json()["project_id"]

    # Update project to create second version
    await client.put(
        f"/api/v1/projects/{project_id}",
        json={"name": "Updated History Project"},
    )

    # Get history
    response = await client.get(f"/api/v1/projects/{project_id}/history")

    assert response.status_code == 200
    history = response.json()
    assert len(history) >= 2  # At least 2 versions
    assert any(h["name"] == "Updated History Project" for h in history)
    assert any(h["name"] == "History Project" for h in history)

    # Check that created_by_name is populated
    for entry in history:
        assert entry["created_by_name"] == "Admin User"


@pytest.mark.asyncio
async def test_get_projects_with_pagination(
    client: AsyncClient, override_auth: None, db_session: AsyncSession
) -> None:
    """Test pagination works correctly."""
    # Create 5 projects
    for i in range(5):
        await client.post(
            "/api/v1/projects",
            json={"name": f"Project {i}", "code": f"PAG-{i:03d}", "budget": 10000},
        )

    # Get first page
    response = await client.get("/api/v1/projects?skip=0&limit=2")
    assert response.status_code == 200
    page1 = response.json()
    assert len(page1) == 2

    # Get second page
    response = await client.get("/api/v1/projects?skip=2&limit=2")
    assert response.status_code == 200
    page2 = response.json()
    assert len(page2) == 2

    # Verify different projects
    codes1 = {p["code"] for p in page1}
    codes2 = {p["code"] for p in page2}
    assert codes1.isdisjoint(codes2)
