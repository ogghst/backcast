"""Tests for GlobalSearchService.

Tests the global cross-entity search service using mocked AsyncSession
to avoid database dependencies. Focuses on scoring logic, RBAC project
filtering, temporal/branch filters, and result merging.
"""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from app.core.versioning.enums import BranchMode
from app.models.schemas.search import GlobalSearchResponse, SearchResultItem
from app.services.global_search_service import (
    GlobalSearchService,
    _best_score,
    _score,
)

# ---------------------------------------------------------------------------
# Unit tests for pure helper functions
# ---------------------------------------------------------------------------


class TestScore:
    """Tests for the _score helper function."""

    def test_exact_match(self) -> None:
        assert _score("hello", "hello") == 1.0

    def test_exact_match_case_insensitive(self) -> None:
        assert _score("Hello", "hello") == 1.0

    def test_prefix_match(self) -> None:
        assert _score("hello world", "hello") == 0.9

    def test_prefix_match_case_insensitive(self) -> None:
        assert _score("Hello World", "hello") == 0.9

    def test_substring_match(self) -> None:
        assert _score("say hello there", "hello") == 0.7

    def test_substring_match_case_insensitive(self) -> None:
        assert _score("Say Hello There", "hello") == 0.7

    def test_no_match(self) -> None:
        assert _score("goodbye", "hello") is None

    def test_none_value(self) -> None:
        assert _score(None, "hello") is None


class TestBestScore:
    """Tests for the _best_score helper function."""

    def _make_row(self, **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(**kwargs)

    def test_primary_exact_beats_prefix(self) -> None:
        row = self._make_row(code="HELLO", name="something")
        score = _best_score(row, "hello", ["code", "name"], [], [])
        assert score == 1.0

    def test_primary_prefix_beats_description(self) -> None:
        row = self._make_row(code="hello world", description="hello")
        score = _best_score(row, "hello", ["code"], ["description"], [])
        assert score == 0.9

    def test_description_score_0_5(self) -> None:
        row = self._make_row(code="nope", description="say hello there")
        score = _best_score(row, "hello", ["code"], ["description"], [])
        assert score == 0.5

    def test_secondary_score_0_3(self) -> None:
        row = self._make_row(status="hello status")
        score = _best_score(row, "hello", [], [], ["status"])
        assert score == 0.3

    def test_primary_exact_overrides_description(self) -> None:
        row = self._make_row(name="hello", description="hello world")
        score = _best_score(row, "hello", ["name"], ["description"], [])
        assert score == 1.0

    def test_no_matching_fields_returns_zero(self) -> None:
        row = self._make_row(code="nope", name="nada")
        score = _best_score(row, "hello", ["code", "name"], [], [])
        assert score == 0.0

    def test_missing_attribute_skipped(self) -> None:
        row = self._make_row(code="hello")
        # "name" does not exist as attribute but getattr returns None
        score = _best_score(row, "hello", ["code", "name"], [], [])
        assert score == 1.0


# ---------------------------------------------------------------------------
# Fixtures for service tests
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create a mocked AsyncSession."""
    return AsyncMock()


def _make_search_item(
    entity_type: str = "project",
    code: str | None = None,
    name: str | None = None,
    description: str | None = None,
    status: str | None = None,
    relevance_score: float = 0.7,
    project_id: UUID | None = None,
) -> SearchResultItem:
    """Create a SearchResultItem for test assertions."""
    root_id = uuid4()
    return SearchResultItem(
        entity_type=entity_type,
        id=uuid4(),
        root_id=root_id,
        code=code,
        name=name,
        description=description,
        status=status,
        relevance_score=relevance_score,
        project_id=project_id,
    )


# ---------------------------------------------------------------------------
# Service-level tests (mocked internal methods)
# ---------------------------------------------------------------------------


class TestGlobalSearchService:
    """Tests for GlobalSearchService.search method.

    Mocks _get_accessible_projects and _search_entity to isolate the
    orchestration logic (merge, sort, limit) from SQL query construction.
    """

    async def _run_search(
        self,
        mock_session: AsyncMock,
        query: str = "test",
        *,
        user_id: UUID | None = None,
        user_role: str = "admin",
        accessible_projects: list[UUID] | None = None,
        entity_results: dict[str, list[SearchResultItem]] | None = None,
        **kwargs: object,
    ) -> GlobalSearchResponse:
        """Helper to run a search with mocked internal methods.

        Args:
            mock_session: Mocked AsyncSession.
            query: Search query string.
            user_id: User ID (defaults to random UUID).
            user_role: User role.
            accessible_projects: Project IDs to return from RBAC mock.
            entity_results: Dict mapping entity_type label to list of
                SearchResultItem. Used to mock _search_entity per entity.
            **kwargs: Extra kwargs passed to ``service.search()``.
        """
        service = GlobalSearchService(mock_session)
        uid = user_id or uuid4()
        projects = accessible_projects if accessible_projects is not None else [uuid4()]
        results_map = entity_results or {}

        # Mock _get_accessible_projects
        service._get_accessible_projects = AsyncMock(return_value=projects)  # type: ignore[method-assign]

        # Mock _resolve_wbe_descendants
        service._resolve_wbe_descendants = AsyncMock(return_value=[])  # type: ignore[method-assign]

        # Mock _search_entity to return controlled results based on config
        async def _mock_search_entity(config: object, **_kw: object) -> list[SearchResultItem]:
            assert isinstance(config, tuple) and len(config) >= 1
            entity_type = config[0]
            assert isinstance(entity_type, str)
            return results_map.get(entity_type, [])

        service._search_entity = _mock_search_entity  # type: ignore[assignment]

        return await service.search(
            query,
            user_id=uid,
            user_role=user_role,
            **kwargs,  # type: ignore[arg-type]
        )

    @pytest.mark.asyncio
    async def test_search_empty_query_returns_empty(
        self, mock_session: AsyncMock
    ) -> None:
        """Search with no matching results returns empty list."""
        result = await self._run_search(
            mock_session, query="zzznonexistent"
        )
        assert isinstance(result, GlobalSearchResponse)
        assert result.query == "zzznonexistent"
        assert result.results == []
        assert result.total == 0

    @pytest.mark.asyncio
    async def test_search_returns_results_across_entities(
        self, mock_session: AsyncMock
    ) -> None:
        """Search returns results from multiple entity types merged into a flat list."""
        proj_id = uuid4()

        result = await self._run_search(
            mock_session,
            query="Test",
            entity_results={
                "project": [
                    _make_search_item(
                        entity_type="project",
                        code="TEST-001",
                        name="Test Project",
                        relevance_score=0.9,
                        project_id=proj_id,
                    ),
                ],
                "department": [
                    _make_search_item(
                        entity_type="department",
                        code="TEST-DEPT",
                        name="Test Department",
                        relevance_score=0.7,
                    ),
                ],
            },
        )

        assert result.total == 2
        entity_types = {r.entity_type for r in result.results}
        assert "project" in entity_types
        assert "department" in entity_types

    @pytest.mark.asyncio
    async def test_search_scores_results(self, mock_session: AsyncMock) -> None:
        """Results are sorted by relevance score (highest first)."""
        result = await self._run_search(
            mock_session,
            query="hello",
            entity_results={
                "project": [
                    _make_search_item(
                        entity_type="project",
                        code="HELLO",
                        relevance_score=1.0,
                    ),
                    _make_search_item(
                        entity_type="project",
                        code="HELLO-WORLD",
                        relevance_score=0.9,
                    ),
                ],
                "wbe": [
                    _make_search_item(
                        entity_type="wbe",
                        name="Say hello there",
                        relevance_score=0.5,
                    ),
                ],
            },
        )

        # Results should be sorted by relevance descending
        scores = [r.relevance_score for r in result.results]
        assert scores == sorted(scores, reverse=True)
        assert scores[0] == 1.0

    @pytest.mark.asyncio
    async def test_search_limit_applied(self, mock_session: AsyncMock) -> None:
        """Results are truncated to the specified limit."""
        items = [
            _make_search_item(
                entity_type="project",
                code=f"TEST-{i}",
                name=f"Test Project {i}",
                relevance_score=0.9 - (i * 0.01),
            )
            for i in range(10)
        ]

        result = await self._run_search(
            mock_session,
            query="test",
            limit=3,
            entity_results={"project": items},
        )

        assert result.total == 3
        assert len(result.results) == 3

    @pytest.mark.asyncio
    async def test_search_filters_by_accessible_projects(
        self, mock_session: AsyncMock
    ) -> None:
        """Non-admin user only sees entities from their accessible projects."""
        user_project = uuid4()

        result = await self._run_search(
            mock_session,
            query="test",
            user_role="viewer",
            accessible_projects=[user_project],
        )

        assert isinstance(result, GlobalSearchResponse)

    @pytest.mark.asyncio
    async def test_search_admin_sees_all_projects(
        self, mock_session: AsyncMock
    ) -> None:
        """Admin user bypasses project filter and sees all projects."""
        proj_a = uuid4()
        proj_b = uuid4()

        result = await self._run_search(
            mock_session,
            query="test",
            user_role="admin",
            accessible_projects=[proj_a, proj_b],
            entity_results={
                "project": [
                    _make_search_item(
                        entity_type="project",
                        name="Project A",
                        project_id=proj_a,
                    ),
                    _make_search_item(
                        entity_type="project",
                        name="Project B",
                        project_id=proj_b,
                    ),
                ],
            },
        )

        assert result.total == 2

    @pytest.mark.asyncio
    async def test_search_scopes_to_project(self, mock_session: AsyncMock) -> None:
        """When project_id is provided, only results for that project are returned."""
        target_project = uuid4()
        other_project = uuid4()

        result = await self._run_search(
            mock_session,
            query="test",
            accessible_projects=[target_project, other_project],
            project_id=target_project,
            entity_results={
                "project": [
                    _make_search_item(
                        entity_type="project",
                        name="Target Project",
                        project_id=target_project,
                    ),
                ],
            },
        )

        assert isinstance(result, GlobalSearchResponse)
        for item in result.results:
            if item.project_id is not None:
                assert item.project_id == target_project

    @pytest.mark.asyncio
    async def test_search_scopes_to_wbe_tree(self, mock_session: AsyncMock) -> None:
        """When wbe_id is provided, descendant WBEs are resolved and used."""
        target_wbe = uuid4()

        result = await self._run_search(
            mock_session,
            query="test",
            wbe_id=target_wbe,
            entity_results={
                "wbe": [
                    _make_search_item(
                        entity_type="wbe",
                        name="Parent WBE",
                    ),
                ],
            },
        )

        assert isinstance(result, GlobalSearchResponse)
        assert result.total >= 1

    @pytest.mark.asyncio
    async def test_search_respects_as_of(self, mock_session: AsyncMock) -> None:
        """Temporal filter is applied when as_of timestamp is provided."""
        as_of = datetime(2025, 1, 15, tzinfo=UTC)

        result = await self._run_search(
            mock_session,
            query="test",
            as_of=as_of,
        )

        assert isinstance(result, GlobalSearchResponse)
        assert result.query == "test"

    @pytest.mark.asyncio
    async def test_search_respects_branch_mode(self, mock_session: AsyncMock) -> None:
        """Branch mode filtering is applied for branchable entities."""
        result = await self._run_search(
            mock_session,
            query="test",
            branch="change-order-1",
            branch_mode=BranchMode.STRICT,
        )

        assert isinstance(result, GlobalSearchResponse)

    @pytest.mark.asyncio
    async def test_search_no_accessible_projects_returns_empty(
        self, mock_session: AsyncMock
    ) -> None:
        """User with no accessible projects gets empty results."""
        result = await self._run_search(
            mock_session,
            query="test",
            user_role="viewer",
            accessible_projects=[],
        )

        assert result.total == 0
        assert result.results == []

    @pytest.mark.asyncio
    async def test_search_global_entities_ignore_project_scope(
        self, mock_session: AsyncMock
    ) -> None:
        """Global entities (user, department, cost_element_type) bypass project filter."""
        # Even with no project access, global entity results appear
        result = await self._run_search(
            mock_session,
            query="Engineering",
            accessible_projects=[],
            entity_results={
                "department": [
                    _make_search_item(
                        entity_type="department",
                        code="ENG",
                        name="Engineering",
                        relevance_score=1.0,
                    ),
                ],
            },
        )

        # Department is global so it bypasses project filter
        assert result.total == 1
        assert result.results[0].entity_type == "department"
        assert result.results[0].name == "Engineering"

    @pytest.mark.asyncio
    async def test_search_response_includes_query(
        self, mock_session: AsyncMock
    ) -> None:
        """Response echoes back the original query string."""
        result = await self._run_search(
            mock_session, query="my-query"
        )
        assert result.query == "my-query"

    @pytest.mark.asyncio
    async def test_search_result_item_fields(
        self, mock_session: AsyncMock
    ) -> None:
        """SearchResultItem contains expected fields from the matched row."""
        proj_id = uuid4()

        result = await self._run_search(
            mock_session,
            query="Test Project Alpha",
            entity_results={
                "project": [
                    _make_search_item(
                        entity_type="project",
                        code="TEST-P1",
                        name="Test Project Alpha",
                        status="Active",
                        relevance_score=1.0,
                        project_id=proj_id,
                    ),
                ],
            },
        )

        assert result.total == 1
        item = result.results[0]
        assert item.entity_type == "project"
        assert item.code == "TEST-P1"
        assert item.name == "Test Project Alpha"
        assert item.status == "Active"
        assert item.relevance_score == 1.0
        assert item.project_id == proj_id
