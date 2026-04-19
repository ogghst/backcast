"""Tests for the global search API route (GET /api/v1/search).

Uses the project's standard auth override pattern with mocked
GlobalSearchService to isolate route-level validation and response
formatting from the service implementation.
"""

from collections.abc import Generator
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.api.dependencies.auth import get_current_active_user, get_current_user
from app.api.routes.search import get_global_search_service
from app.core.rbac import RBACServiceABC, get_rbac_service
from app.main import app
from app.models.domain.user import User
from app.models.schemas.search import GlobalSearchResponse, SearchResultItem

# ---------------------------------------------------------------------------
# Mock user and RBAC for auth override
# ---------------------------------------------------------------------------

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


def _mock_get_current_user() -> User:
    return mock_admin_user


def _mock_get_current_active_user() -> User:
    return mock_admin_user


class _MockRBACService(RBACServiceABC):
    def has_role(self, user_role: str, required_roles: list[str]) -> bool:
        return True

    def has_permission(self, user_role: str, required_permission: str) -> bool:
        return True

    def get_user_permissions(self, user_role: str) -> list[str]:
        return ["project-read", "project-create", "project-update", "project-delete"]

    async def has_project_access(
        self,
        user_id: UUID,
        user_role: str,
        project_id: UUID,
        required_permission: str,
    ) -> bool:
        return True

    async def get_user_projects(
        self, user_id: UUID, user_role: str
    ) -> list[UUID]:
        return []

    async def get_project_role(
        self, user_id: UUID, project_id: UUID
    ) -> str | None:
        return None


def _mock_get_rbac_service() -> RBACServiceABC:
    return _MockRBACService()


@pytest.fixture(autouse=True)
def override_auth() -> Generator[None, None, None]:
    """Override authentication and RBAC for all search route tests."""
    app.dependency_overrides[get_current_user] = _mock_get_current_user
    app.dependency_overrides[get_current_active_user] = _mock_get_current_active_user
    app.dependency_overrides[get_rbac_service] = _mock_get_rbac_service
    yield
    app.dependency_overrides = {}


# ---------------------------------------------------------------------------
# Helper to build a mock service that returns a fixed response
# ---------------------------------------------------------------------------


def _make_mock_service_response(query: str = "test") -> GlobalSearchResponse:
    """Build a standard mock search response."""
    return GlobalSearchResponse(
        results=[
            SearchResultItem(
                entity_type="project",
                id=uuid4(),
                root_id=uuid4(),
                code="TEST-001",
                name="Test Project",
                description=None,
                status="Active",
                relevance_score=1.0,
                project_id=uuid4(),
            ),
        ],
        total=1,
        query=query,
    )


# ---------------------------------------------------------------------------
# Route tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_endpoint_returns_200(
    client: AsyncClient,
) -> None:
    """Happy path: valid query returns 200 with expected response shape."""
    mock_response = _make_mock_service_response("test")

    mock_service = AsyncMock()
    mock_service.search.return_value = mock_response

    app.dependency_overrides[get_global_search_service] = lambda: mock_service

    try:
        response = await client.get("/api/v1/search", params={"q": "test"})
    finally:
        app.dependency_overrides.pop(get_global_search_service, None)

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "test"
    assert data["total"] == 1
    assert len(data["results"]) == 1
    assert data["results"][0]["entity_type"] == "project"
    assert data["results"][0]["relevance_score"] == 1.0


@pytest.mark.asyncio
async def test_search_endpoint_requires_auth(
    client: AsyncClient,
) -> None:
    """Endpoint returns 401 when no authentication token is provided."""
    # Clear auth overrides to simulate unauthenticated request
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_current_active_user, None)
    app.dependency_overrides.pop(get_rbac_service, None)

    response = await client.get("/api/v1/search", params={"q": "test"})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_search_endpoint_requires_query_param(
    client: AsyncClient,
) -> None:
    """Endpoint returns 422 when the required 'q' parameter is missing."""
    response = await client.get("/api/v1/search")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_endpoint_rejects_empty_query(
    client: AsyncClient,
) -> None:
    """Endpoint returns 422 when 'q' is empty (min_length=1)."""
    response = await client.get("/api/v1/search", params={"q": ""})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_endpoint_rejects_query_too_long(
    client: AsyncClient,
) -> None:
    """Endpoint returns 422 when 'q' exceeds max_length=200."""
    response = await client.get(
        "/api/v1/search", params={"q": "a" * 201}
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_endpoint_validates_limit_bounds(
    client: AsyncClient,
) -> None:
    """Endpoint returns 422 when limit is outside 1-200 range."""
    # limit=0 is below minimum
    resp_zero = await client.get(
        "/api/v1/search", params={"q": "test", "limit": 0}
    )
    assert resp_zero.status_code == 422

    # limit=201 exceeds maximum
    resp_over = await client.get(
        "/api/v1/search", params={"q": "test", "limit": 201}
    )
    assert resp_over.status_code == 422


@pytest.mark.asyncio
async def test_search_endpoint_validates_mode_pattern(
    client: AsyncClient,
) -> None:
    """Endpoint returns 422 when mode does not match 'merged' or 'isolated'."""
    response = await client.get(
        "/api/v1/search", params={"q": "test", "mode": "invalid"}
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_endpoint_accepts_valid_params(
    client: AsyncClient,
) -> None:
    """Endpoint returns 200 with all valid query parameters."""
    mock_response = _make_mock_service_response("alpha")
    mock_service = AsyncMock()
    mock_service.search.return_value = mock_response

    app.dependency_overrides[get_global_search_service] = lambda: mock_service

    try:
        response = await client.get(
            "/api/v1/search",
            params={
                "q": "alpha",
                "branch": "main",
                "mode": "merged",
                "limit": 10,
            },
        )
    finally:
        app.dependency_overrides.pop(get_global_search_service, None)

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_search_endpoint_passes_service_kwargs(
    client: AsyncClient,
) -> None:
    """Route passes all query parameters to the service search method."""
    mock_response = _make_mock_service_response("beta")
    mock_service = AsyncMock()
    mock_service.search.return_value = mock_response

    app.dependency_overrides[get_global_search_service] = lambda: mock_service

    project_id = uuid4()
    wbe_id = uuid4()

    try:
        response = await client.get(
            "/api/v1/search",
            params={
                "q": "beta",
                "project_id": str(project_id),
                "wbe_id": str(wbe_id),
                "branch": "feature-branch",
                "mode": "isolated",
                "limit": 25,
            },
        )
    finally:
        app.dependency_overrides.pop(get_global_search_service, None)

    assert response.status_code == 200
    mock_service.search.assert_called_once()

    call_kwargs = mock_service.search.call_args
    # First positional arg is the query
    assert call_kwargs[0][0] == "beta"
    # Keyword args
    assert call_kwargs[1]["project_id"] == project_id
    assert call_kwargs[1]["wbe_id"] == wbe_id
    assert call_kwargs[1]["branch"] == "feature-branch"
    assert call_kwargs[1]["limit"] == 25


@pytest.mark.asyncio
async def test_search_endpoint_invalid_project_id_format(
    client: AsyncClient,
) -> None:
    """Endpoint returns 422 when project_id is not a valid UUID."""
    response = await client.get(
        "/api/v1/search",
        params={"q": "test", "project_id": "not-a-uuid"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_endpoint_invalid_as_of_format(
    client: AsyncClient,
) -> None:
    """Endpoint returns 422 when as_of is not a valid ISO 8601 datetime."""
    response = await client.get(
        "/api/v1/search",
        params={"q": "test", "as_of": "not-a-datetime"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_endpoint_default_params(
    client: AsyncClient,
) -> None:
    """Endpoint uses correct defaults when optional params are omitted."""
    mock_response = _make_mock_service_response("query")
    mock_service = AsyncMock()
    mock_service.search.return_value = mock_response

    app.dependency_overrides[get_global_search_service] = lambda: mock_service

    try:
        response = await client.get(
            "/api/v1/search",
            params={"q": "query"},
        )
    finally:
        app.dependency_overrides.pop(get_global_search_service, None)

    assert response.status_code == 200
    call_kwargs = mock_service.search.call_args[1]
    assert call_kwargs["branch"] == "main"
    assert call_kwargs["limit"] == 50
    assert call_kwargs["as_of"] is None
    assert call_kwargs["project_id"] is None
    assert call_kwargs["wbe_id"] is None
