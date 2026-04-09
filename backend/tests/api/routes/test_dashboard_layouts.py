"""Tests for dashboard layout API endpoints.

Covers all 7 routes under /api/v1/dashboard-layouts:
- GET  /                list layouts for user (query: project_id?)
- GET  /templates       list all templates
- GET  /{layout_id}     get single layout
- POST /                create layout
- PUT  /{layout_id}     update layout
- DELETE /{layout_id}   delete layout
- POST /{layout_id}/clone  clone template
"""

from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user, get_current_user
from app.core.rbac import RBACServiceABC, get_rbac_service
from app.db.session import get_db
from app.main import app
from app.models.domain.user import User
from app.services.dashboard_layout_service import DashboardLayoutService

BASE_URL = "/api/v1/dashboard-layouts"


# ---------------------------------------------------------------------------
# Mock RBAC that grants all permissions
# ---------------------------------------------------------------------------


class _MockRBAC(RBACServiceABC):
    """RBAC service that grants all permissions for testing."""

    def has_role(self, user_role: str, required_roles: list[str]) -> bool:
        return True

    def has_permission(self, user_role: str, required_permission: str) -> bool:
        return True

    def get_user_permissions(self, user_role: str) -> list[str]:
        return []

    async def has_project_access(
        self,
        user_id: UUID,
        user_role: str,
        project_id: UUID,
        required_permission: str,
    ) -> bool:
        return True

    async def get_user_projects(self, user_id: UUID, user_role: str) -> list[UUID]:
        return []

    async def get_project_role(
        self, user_id: UUID, project_id: UUID
    ) -> str | None:
        return None


# ---------------------------------------------------------------------------
# Fixtures: authenticated clients for owner and other user
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def owner_user(db_session: AsyncSession) -> User:
    """Create the owner user in the database.

    Returns:
        User instance representing the layout owner.
    """
    user = User(
        id=uuid4(),
        user_id=uuid4(),
        email="owner@test.com",
        full_name="Owner User",
        role="admin",
        is_active=True,
        hashed_password="hash",
        created_by=uuid4(),
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def other_user(db_session: AsyncSession) -> User:
    """Create a second user for authorization tests.

    Returns:
        User instance representing a non-owner.
    """
    user = User(
        id=uuid4(),
        user_id=uuid4(),
        email="other@test.com",
        full_name="Other User",
        role="viewer",
        is_active=True,
        hashed_password="hash",
        created_by=uuid4(),
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_client(
    db_session: AsyncSession,
    owner_user: User,
) -> AsyncClient:
    """Create an authenticated client acting as the owner user.

    Returns:
        AsyncClient with auth and DB dependencies overridden.
    """
    app.dependency_overrides[get_current_active_user] = lambda: owner_user
    app.dependency_overrides[get_current_user] = lambda: owner_user
    app.dependency_overrides[get_rbac_service] = lambda: _MockRBAC()
    app.dependency_overrides[get_db] = lambda: db_session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides = {}


@pytest_asyncio.fixture
async def other_client(
    db_session: AsyncSession,
    other_user: User,
) -> AsyncClient:
    """Create an authenticated client acting as a different user.

    Returns:
        AsyncClient with auth overridden to the non-owner user.
    """
    app.dependency_overrides[get_current_active_user] = lambda: other_user
    app.dependency_overrides[get_current_user] = lambda: other_user
    app.dependency_overrides[get_rbac_service] = lambda: _MockRBAC()
    app.dependency_overrides[get_db] = lambda: db_session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides = {}


# ---------------------------------------------------------------------------
# Helper: create layout via service for test setup
# ---------------------------------------------------------------------------


async def _create_layout(
    db_session: AsyncSession,
    user_id: UUID,
    name: str = "Test Layout",
    project_id: UUID | None = None,
    is_template: bool = False,
    is_default: bool = False,
    widgets: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    """Create a layout via service and commit for test setup.

    Args:
        db_session: Database session.
        user_id: Owner user ID.
        name: Layout name.
        project_id: Optional project scope.
        is_template: Whether this is a template.
        is_default: Whether this is the default layout.
        widgets: Widget configuration list.

    Returns:
        Dictionary of the created layout's key fields.
    """
    svc = DashboardLayoutService(db_session)
    layout = await svc.create(
        user_id=user_id,
        name=name,
        description="A test layout",
        project_id=project_id,
        is_template=is_template,
        is_default=is_default,
        widgets=widgets or [],
    )
    await db_session.commit()
    return {
        "id": str(layout.id),
        "name": layout.name,
        "user_id": str(layout.user_id),
        "project_id": str(layout.project_id) if layout.project_id else None,
        "is_template": layout.is_template,
        "is_default": layout.is_default,
        "widgets": layout.widgets,
    }


# ===========================================================================
# 1. GET /api/v1/dashboard-layouts -- list layouts for user
# ===========================================================================


@pytest.mark.asyncio
async def test_list_layouts_empty(auth_client: AsyncClient) -> None:
    """Listing layouts returns empty list when none exist."""
    response = await auth_client.get(BASE_URL)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_layouts_returns_only_user_layouts(
    auth_client: AsyncClient,
    owner_user: User,
    other_user: User,
    db_session: AsyncSession,
) -> None:
    """Listing returns layouts owned by the authenticated user only."""
    await _create_layout(
        db_session, user_id=owner_user.user_id, name="Owner Layout"
    )
    await _create_layout(
        db_session, user_id=other_user.user_id, name="Other Layout"
    )

    response = await auth_client.get(BASE_URL)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Owner Layout"


@pytest.mark.asyncio
async def test_list_layouts_excludes_templates(
    auth_client: AsyncClient,
    owner_user: User,
    db_session: AsyncSession,
) -> None:
    """Listing user layouts does not include templates."""
    await _create_layout(
        db_session,
        user_id=owner_user.user_id,
        name="My Layout",
        is_template=False,
    )
    await _create_layout(
        db_session,
        user_id=owner_user.user_id,
        name="Template",
        is_template=True,
    )

    response = await auth_client.get(BASE_URL)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "My Layout"


@pytest.mark.asyncio
async def test_list_layouts_filter_by_project(
    auth_client: AsyncClient,
    owner_user: User,
    db_session: AsyncSession,
) -> None:
    """Filtering by project_id returns matching and global layouts."""
    project_id = uuid4()

    await _create_layout(
        db_session,
        user_id=owner_user.user_id,
        name="Global Layout",
        project_id=None,
    )
    await _create_layout(
        db_session,
        user_id=owner_user.user_id,
        name="Project Layout",
        project_id=project_id,
    )
    await _create_layout(
        db_session,
        user_id=owner_user.user_id,
        name="Other Project",
        project_id=uuid4(),
    )

    response = await auth_client.get(
        BASE_URL,
        params={"project_id": str(project_id)},
    )
    assert response.status_code == 200
    data = response.json()
    names = {item["name"] for item in data}
    assert names == {"Global Layout", "Project Layout"}


# ===========================================================================
# 2. GET /api/v1/dashboard-layouts/templates -- list templates
# ===========================================================================


@pytest.mark.asyncio
async def test_list_templates_empty(auth_client: AsyncClient) -> None:
    """Listing templates returns empty list when none exist."""
    response = await auth_client.get(f"{BASE_URL}/templates")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_templates_returns_only_templates(
    auth_client: AsyncClient,
    owner_user: User,
    db_session: AsyncSession,
) -> None:
    """Listing templates returns only is_template=True layouts."""
    await _create_layout(
        db_session,
        user_id=owner_user.user_id,
        name="Regular",
        is_template=False,
    )
    await _create_layout(
        db_session,
        user_id=owner_user.user_id,
        name="My Template",
        is_template=True,
    )

    response = await auth_client.get(f"{BASE_URL}/templates")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "My Template"
    assert data[0]["is_template"] is True


@pytest.mark.asyncio
async def test_list_templates_returns_all_users_templates(
    auth_client: AsyncClient,
    owner_user: User,
    other_user: User,
    db_session: AsyncSession,
) -> None:
    """Templates from all users are returned regardless of caller."""
    await _create_layout(
        db_session,
        user_id=owner_user.user_id,
        name="Owner Template",
        is_template=True,
    )
    await _create_layout(
        db_session,
        user_id=other_user.user_id,
        name="Other Template",
        is_template=True,
    )

    response = await auth_client.get(f"{BASE_URL}/templates")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    names = {item["name"] for item in data}
    assert names == {"Owner Template", "Other Template"}


# ===========================================================================
# 3. GET /api/v1/dashboard-layouts/{layout_id} -- get single layout
# ===========================================================================


@pytest.mark.asyncio
async def test_get_layout_owner(
    auth_client: AsyncClient,
    owner_user: User,
    db_session: AsyncSession,
) -> None:
    """Owner can retrieve their own layout."""
    created = await _create_layout(
        db_session, user_id=owner_user.user_id, name="My Layout"
    )

    response = await auth_client.get(f"{BASE_URL}/{created['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == "My Layout"


@pytest.mark.asyncio
async def test_get_layout_not_found(auth_client: AsyncClient) -> None:
    """GET with a non-existent ID returns 404."""
    fake_id = uuid4()
    response = await auth_client.get(f"{BASE_URL}/{fake_id}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_layout_other_user_non_template_returns_404(
    auth_client: AsyncClient,
    owner_user: User,
    other_user: User,
    db_session: AsyncSession,
) -> None:
    """Requesting another user's non-template layout returns 404."""
    created = await _create_layout(
        db_session, user_id=other_user.user_id, name="Private Layout"
    )

    response = await auth_client.get(f"{BASE_URL}/{created['id']}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_layout_template_from_other_user_allowed(
    auth_client: AsyncClient,
    other_user: User,
    db_session: AsyncSession,
) -> None:
    """Any authenticated user can retrieve a template layout."""
    created = await _create_layout(
        db_session,
        user_id=other_user.user_id,
        name="Shared Template",
        is_template=True,
    )

    response = await auth_client.get(f"{BASE_URL}/{created['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == "Shared Template"


# ===========================================================================
# 4. POST /api/v1/dashboard-layouts -- create layout
# ===========================================================================


@pytest.mark.asyncio
async def test_create_layout(
    auth_client: AsyncClient,
    owner_user: User,
) -> None:
    """Creating a layout returns 201 with correct fields."""
    payload = {
        "name": "New Layout",
        "description": "A fresh layout",
        "project_id": None,
        "is_template": False,
        "is_default": False,
        "widgets": [{"typeId": "test-widget", "config": {}}],
    }

    response = await auth_client.post(BASE_URL, json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == "New Layout"
    assert data["description"] == "A fresh layout"
    assert data["user_id"] == str(owner_user.user_id)
    assert data["is_template"] is False
    assert data["is_default"] is False
    assert len(data["widgets"]) == 1
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_create_layout_minimal(
    auth_client: AsyncClient,
    owner_user: User,
) -> None:
    """Creating with only required fields defaults widgets to empty list."""
    payload = {"name": "Minimal Layout"}

    response = await auth_client.post(BASE_URL, json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["widgets"] == []
    assert data["is_template"] is False
    assert data["is_default"] is False
    assert data["project_id"] is None


@pytest.mark.asyncio
async def test_create_layout_with_project(
    auth_client: AsyncClient,
    owner_user: User,
) -> None:
    """Creating with a project_id scopes the layout correctly."""
    project_id = uuid4()
    payload = {
        "name": "Scoped Layout",
        "project_id": str(project_id),
    }

    response = await auth_client.post(BASE_URL, json=payload)
    assert response.status_code == 201
    assert response.json()["project_id"] == str(project_id)


@pytest.mark.asyncio
async def test_create_default_layout_clears_previous_default(
    auth_client: AsyncClient,
    owner_user: User,
    db_session: AsyncSession,
) -> None:
    """Creating a default layout clears the existing default for same scope."""
    project_id = uuid4()

    # Create first default via service
    await _create_layout(
        db_session,
        user_id=owner_user.user_id,
        name="First Default",
        project_id=project_id,
        is_default=True,
    )

    # Create second default via API
    payload = {
        "name": "Second Default",
        "project_id": str(project_id),
        "is_default": True,
    }
    response = await auth_client.post(BASE_URL, json=payload)
    assert response.status_code == 201
    assert response.json()["is_default"] is True

    # Verify only the new one is default via service query
    svc = DashboardLayoutService(db_session)
    layouts = await svc.get_for_user_project(owner_user.user_id, project_id)
    defaults = [ly for ly in layouts if ly.is_default]
    assert len(defaults) == 1
    assert defaults[0].name == "Second Default"


# ===========================================================================
# 5. PUT /api/v1/dashboard-layouts/{layout_id} -- update layout
# ===========================================================================


@pytest.mark.asyncio
async def test_update_layout(
    auth_client: AsyncClient,
    owner_user: User,
    db_session: AsyncSession,
) -> None:
    """Owner can update their layout and changes are persisted."""
    created = await _create_layout(
        db_session, user_id=owner_user.user_id, name="Original"
    )

    payload = {"name": "Updated", "description": "Changed desc"}
    response = await auth_client.put(
        f"{BASE_URL}/{created['id']}", json=payload
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated"
    assert data["description"] == "Changed desc"


@pytest.mark.asyncio
async def test_update_layout_widgets(
    auth_client: AsyncClient,
    owner_user: User,
    db_session: AsyncSession,
) -> None:
    """Updating widgets replaces the entire widget array."""
    created = await _create_layout(
        db_session, user_id=owner_user.user_id, name="Widget Layout"
    )

    new_widgets = [{"typeId": "chart", "config": {"color": "blue"}}]
    payload = {"widgets": new_widgets}
    response = await auth_client.put(
        f"{BASE_URL}/{created['id']}", json=payload
    )
    assert response.status_code == 200
    assert response.json()["widgets"] == new_widgets


@pytest.mark.asyncio
async def test_update_layout_not_found(auth_client: AsyncClient) -> None:
    """Updating a non-existent layout returns 404."""
    fake_id = uuid4()
    response = await auth_client.put(
        f"{BASE_URL}/{fake_id}",
        json={"name": "Nope"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_layout_other_user_forbidden(
    auth_client: AsyncClient,
    other_user: User,
    db_session: AsyncSession,
) -> None:
    """Updating another user's layout returns 403."""
    created = await _create_layout(
        db_session, user_id=other_user.user_id, name="Not Yours"
    )

    response = await auth_client.put(
        f"{BASE_URL}/{created['id']}",
        json={"name": "Hacked"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_layout_set_default_clears_previous(
    auth_client: AsyncClient,
    owner_user: User,
    db_session: AsyncSession,
) -> None:
    """Setting is_default=True clears the existing default in same scope."""
    project_id = uuid4()

    await _create_layout(
        db_session,
        user_id=owner_user.user_id,
        name="Old Default",
        project_id=project_id,
        is_default=True,
    )
    non_default = await _create_layout(
        db_session,
        user_id=owner_user.user_id,
        name="New Default",
        project_id=project_id,
        is_default=False,
    )

    response = await auth_client.put(
        f"{BASE_URL}/{non_default['id']}",
        json={"is_default": True},
    )
    assert response.status_code == 200
    assert response.json()["is_default"] is True

    # Verify only one default exists
    svc = DashboardLayoutService(db_session)
    layouts = await svc.get_for_user_project(owner_user.user_id, project_id)
    defaults = [ly for ly in layouts if ly.is_default]
    assert len(defaults) == 1
    assert defaults[0].name == "New Default"


@pytest.mark.asyncio
async def test_update_template_layout_returns_403(
    auth_client: AsyncClient,
    owner_user: User,
    db_session: AsyncSession,
) -> None:
    """Updating a template layout via the regular PUT endpoint returns 403."""
    created = await _create_layout(
        db_session,
        user_id=owner_user.user_id,
        name="Template",
        is_template=True,
    )

    response = await auth_client.put(
        f"{BASE_URL}/{created['id']}",
        json={"name": "Hacked"},
    )
    assert response.status_code == 403
    assert "template" in response.json()["detail"].lower()


# ===========================================================================
# 5b. PUT /api/v1/dashboard-layouts/templates/{layout_id} -- admin template update
# ===========================================================================


@pytest.mark.asyncio
async def test_admin_update_template(
    auth_client: AsyncClient,
    other_user: User,
    db_session: AsyncSession,
) -> None:
    """Admin user can update a template via the admin endpoint."""
    template = await _create_layout(
        db_session,
        user_id=other_user.user_id,
        name="Admin Template",
        is_template=True,
        widgets=[{"typeId": "header", "config": {}}],
    )

    response = await auth_client.put(
        f"{BASE_URL}/templates/{template['id']}",
        json={"name": "Updated by Admin"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated by Admin"


@pytest.mark.asyncio
async def test_admin_update_template_not_found(auth_client: AsyncClient) -> None:
    """Admin template update returns 404 for nonexistent ID."""
    fake_id = uuid4()
    response = await auth_client.put(
        f"{BASE_URL}/templates/{fake_id}",
        json={"name": "Nope"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_update_template_non_template_returns_404(
    auth_client: AsyncClient,
    owner_user: User,
    db_session: AsyncSession,
) -> None:
    """Admin template update returns 404 when layout is not a template."""
    created = await _create_layout(
        db_session,
        user_id=owner_user.user_id,
        name="Regular",
        is_template=False,
    )

    response = await auth_client.put(
        f"{BASE_URL}/templates/{created['id']}",
        json={"name": "Nope"},
    )
    assert response.status_code == 404


# ===========================================================================
# 6. DELETE /api/v1/dashboard-layouts/{layout_id} -- delete layout
# ===========================================================================


@pytest.mark.asyncio
async def test_delete_layout(
    auth_client: AsyncClient,
    owner_user: User,
    db_session: AsyncSession,
) -> None:
    """Owner can delete their layout and receives 204."""
    created = await _create_layout(
        db_session, user_id=owner_user.user_id, name="ToDelete"
    )

    response = await auth_client.delete(f"{BASE_URL}/{created['id']}")
    assert response.status_code == 204

    # Verify it is gone
    svc = DashboardLayoutService(db_session)
    result = await svc.get(UUID(created["id"]))
    assert result is None


@pytest.mark.asyncio
async def test_delete_layout_not_found(auth_client: AsyncClient) -> None:
    """Deleting a non-existent layout returns 404."""
    fake_id = uuid4()
    response = await auth_client.delete(f"{BASE_URL}/{fake_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_layout_other_user_forbidden(
    auth_client: AsyncClient,
    other_user: User,
    db_session: AsyncSession,
) -> None:
    """Deleting another user's layout returns 403."""
    created = await _create_layout(
        db_session, user_id=other_user.user_id, name="Protected"
    )

    response = await auth_client.delete(f"{BASE_URL}/{created['id']}")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_layout_twice_returns_404(
    auth_client: AsyncClient,
    owner_user: User,
    db_session: AsyncSession,
) -> None:
    """Deleting the same layout twice returns 404 on second attempt."""
    created = await _create_layout(
        db_session, user_id=owner_user.user_id, name="Delete Me"
    )

    response1 = await auth_client.delete(f"{BASE_URL}/{created['id']}")
    assert response1.status_code == 204

    response2 = await auth_client.delete(f"{BASE_URL}/{created['id']}")
    assert response2.status_code == 404


@pytest.mark.asyncio
async def test_delete_default_auto_promotes(
    auth_client: AsyncClient,
    owner_user: User,
    db_session: AsyncSession,
) -> None:
    """Deleting the default layout auto-promotes the next most recent."""
    project_id = uuid4()

    await _create_layout(
        db_session,
        user_id=owner_user.user_id,
        name="Promote Me",
        project_id=project_id,
        is_default=False,
    )
    default_layout = await _create_layout(
        db_session,
        user_id=owner_user.user_id,
        name="Default",
        project_id=project_id,
        is_default=True,
    )

    response = await auth_client.delete(f"{BASE_URL}/{default_layout['id']}")
    assert response.status_code == 204

    # Verify the remaining layout is now default
    svc = DashboardLayoutService(db_session)
    layouts = await svc.get_for_user_project(owner_user.user_id, project_id)
    assert len(layouts) == 1
    assert layouts[0].name == "Promote Me"
    assert layouts[0].is_default is True


# ===========================================================================
# 7. POST /api/v1/dashboard-layouts/{layout_id}/clone -- clone template
# ===========================================================================


@pytest.mark.asyncio
async def test_clone_template(
    auth_client: AsyncClient,
    owner_user: User,
    other_user: User,
    db_session: AsyncSession,
) -> None:
    """Cloning a template creates a non-template copy for the user."""
    template = await _create_layout(
        db_session,
        user_id=other_user.user_id,
        name="Project Overview",
        is_template=True,
        widgets=[{"typeId": "header", "config": {}}],
    )

    response = await auth_client.post(
        f"{BASE_URL}/{template['id']}/clone",
        json={},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Copy of Project Overview"
    assert data["is_template"] is False
    assert data["user_id"] == str(owner_user.user_id)
    assert data["widgets"] == [{"typeId": "header", "config": {}}]


@pytest.mark.asyncio
async def test_clone_template_with_project(
    auth_client: AsyncClient,
    owner_user: User,
    other_user: User,
    db_session: AsyncSession,
) -> None:
    """Cloning with a project_id scopes the clone to that project."""
    project_id = uuid4()
    template = await _create_layout(
        db_session,
        user_id=other_user.user_id,
        name="Template",
        is_template=True,
    )

    response = await auth_client.post(
        f"{BASE_URL}/{template['id']}/clone",
        json={"project_id": str(project_id)},
    )
    assert response.status_code == 201
    assert response.json()["project_id"] == str(project_id)


@pytest.mark.asyncio
async def test_clone_non_template_returns_400(
    auth_client: AsyncClient,
    owner_user: User,
    db_session: AsyncSession,
) -> None:
    """Cloning a non-template layout returns 400."""
    non_template = await _create_layout(
        db_session,
        user_id=owner_user.user_id,
        name="Not A Template",
        is_template=False,
    )

    response = await auth_client.post(
        f"{BASE_URL}/{non_template['id']}/clone",
        json={},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_clone_nonexistent_returns_400(auth_client: AsyncClient) -> None:
    """Cloning a non-existent layout returns 400."""
    fake_id = uuid4()
    response = await auth_client.post(
        f"{BASE_URL}/{fake_id}/clone",
        json={},
    )
    assert response.status_code == 400
