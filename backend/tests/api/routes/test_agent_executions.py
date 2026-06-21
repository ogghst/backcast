"""Route tests for the Agents History REST endpoints.

Covers the three endpoints added for Background Agent Execution +
Agents History:

- ``GET  /api/v1/ai/chat/executions`` — paginated history list.
- ``GET  /api/v1/ai/chat/executions/running-count`` — menu badge count.
- ``POST /api/v1/ai/chat/executions/{execution_id}/stop`` — real Stop.

The conftest wires ``current_user`` to ``TEST_USER_ID`` (the seeded admin)
and bypasses RBAC, so the ownership checks in these handlers are exercised
by varying the session's ``user_id`` column.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.event_types import ExecutionStatus
from app.api.dependencies.auth import UserIdentity, get_current_user
from app.db.session import async_session_maker
from app.main import app
from app.models.domain.ai import (
    AIAgentExecution,
    AIAssistantConfig,
    AIConversationSession,
)
from tests.conftest import TEST_USER_ID

PREFIX = "/ai/chat"

# Track AIAssistantConfig rows created by _make_assistant. The shared ``db``
# fixture COMMITS (so the ASGI client's separate sessions can see test data),
# so without explicit cleanup the "Test Assistant"/"Planner" rows — and their
# cascaded sessions/executions — accumulate in the dev DB across runs. The
# autouse fixture below deletes them after each test.
_created_assistant_ids: list[UUID] = []


@pytest_asyncio.fixture(autouse=True)
async def _cleanup_test_assistants() -> AsyncGenerator[None, None]:
    """Delete assistants created during the test.

    The ``assistant_config_id`` FK is ``ondelete=CASCADE``, so this also
    removes the test's sessions, messages, and executions.
    """
    yield
    if _created_assistant_ids:
        async with async_session_maker() as db:
            await db.execute(
                delete(AIAssistantConfig).where(
                    AIAssistantConfig.id.in_(_created_assistant_ids)
                )
            )
            await db.commit()
        _created_assistant_ids.clear()


@pytest.fixture
def isolated_user() -> UUID:
    """A fresh throwaway user_id, with get_current_user overridden to return it.

    The default conftest client authenticates as the seeded admin, whose
    shared dev-DB execution history makes count-sensitive assertions
    non-deterministic.  Tests that need exact counts override the
    dependency to a fresh user with no prior executions.
    """

    user_id = uuid.uuid4()

    async def _override() -> UserIdentity:
        return UserIdentity(user_id=user_id)

    app.dependency_overrides[get_current_user] = _override
    try:
        yield user_id
    finally:
        app.dependency_overrides.pop(get_current_user, None)


async def _make_assistant(db: AsyncSession, name: str = "Test Assistant") -> UUID:
    """Create a minimal AIAssistantConfig row and return its id.

    The id is recorded for autouse teardown (``_cleanup_test_assistants``).
    """
    asst = AIAssistantConfig(name=name, is_active=True, agent_type="main")
    db.add(asst)
    await db.flush()
    aid = UUID(str(asst.id))
    _created_assistant_ids.append(aid)
    return aid


async def _make_session(
    db: AsyncSession,
    user_id: UUID,
    assistant_id: UUID,
    *,
    context: dict | None = None,
    project_id: UUID | None = None,
) -> UUID:
    """Create an AIConversationSession row owned by *user_id* and return its id."""
    session = AIConversationSession(
        user_id=user_id,
        assistant_config_id=assistant_id,
        context=context if context is not None else {"type": "general"},
        project_id=project_id,
    )
    db.add(session)
    await db.flush()
    return UUID(str(session.id))


async def _make_execution(
    db: AsyncSession,
    session_id: UUID,
    *,
    status: str = ExecutionStatus.RUNNING,
    name: str | None = "do a thing",
    run_in_background: bool = False,
    started_at: datetime | None = None,
) -> UUID:
    """Create an AIAgentExecution row and return its id."""
    execution = AIAgentExecution(
        id=uuid.uuid4(),
        session_id=session_id,
        status=status,
        execution_mode="standard",
        run_in_background=run_in_background,
        name=name,
        started_at=started_at or datetime.now(tz=UTC),
    )
    db.add(execution)
    await db.flush()
    return UUID(str(execution.id))


# =====================================================================
# GET /executions
# =====================================================================


@pytest.mark.asyncio
async def test_list_executions_returns_only_owner_newest_first(
    client: AsyncClient, db: AsyncSession
) -> None:
    """GET /executions returns only the user's executions, newest started_at first."""
    asst = await _make_assistant(db)
    mine = await _make_session(db, TEST_USER_ID, asst)
    other_user = UUID("11111111-1111-1111-1111-111111111111")
    others = await _make_session(db, other_user, asst)

    base = datetime.now(tz=UTC) - timedelta(minutes=10)
    older = await _make_execution(db, mine, name="older", started_at=base)
    newer = await _make_execution(
        db, mine, name="newer", started_at=base + timedelta(minutes=5)
    )
    # Other user's execution must NOT appear.
    await _make_execution(
        db, others, name="theirs", started_at=base + timedelta(minutes=9)
    )
    await db.commit()

    resp = await client.get(f"{PREFIX}/executions", params={"limit": 50})
    assert resp.status_code == 200
    data = resp.json()
    ids = [item["id"] for item in data["items"]]
    assert str(newer) in ids
    assert str(older) in ids
    # Newest first.
    assert ids.index(str(newer)) < ids.index(str(older))
    # Other user's execution is excluded.
    assert all(item["name"] != "theirs" for item in data["items"]), (
        "another user's execution leaked into the list"
    )


@pytest.mark.asyncio
async def test_list_executions_status_filter_and_pagination(
    client: AsyncClient, db: AsyncSession, isolated_user: UUID
) -> None:
    """GET /executions respects the status filter and limit/offset pagination."""
    asst = await _make_assistant(db)
    mine = await _make_session(db, isolated_user, asst)
    await _make_execution(db, mine, status=ExecutionStatus.RUNNING)
    await _make_execution(db, mine, status=ExecutionStatus.RUNNING)
    await _make_execution(db, mine, status=ExecutionStatus.COMPLETED)
    await db.commit()

    # Status filter (pass the .value so httpx sends "running", not the enum repr).
    resp = await client.get(
        f"{PREFIX}/executions", params={"status": ExecutionStatus.RUNNING.value}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert all(item["status"] == ExecutionStatus.RUNNING for item in data["items"])
    assert data["total"] == 2

    # Pagination: limit=1, offset=0 -> one item, has_more True.
    resp2 = await client.get(
        f"{PREFIX}/executions",
        params={"status": ExecutionStatus.RUNNING.value, "limit": 1, "offset": 0},
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert len(data2["items"]) == 1
    assert data2["has_more"] is True


@pytest.mark.asyncio
async def test_list_executions_derives_context_and_name(
    client: AsyncClient, db: AsyncSession
) -> None:
    """GET /executions derives the context block from the session JSONB and
    surfaces the persisted name + run_in_background flag."""
    asst = await _make_assistant(db, name="Planner")
    proj = UUID("22222222-2222-2222-2222-222222222222")
    mine = await _make_session(
        db,
        TEST_USER_ID,
        asst,
        context={"type": "project", "id": str(proj), "name": "Apollo"},
        project_id=proj,
    )
    eid = await _make_execution(
        db, mine, name="build the rocket", run_in_background=True
    )
    await db.commit()

    resp = await client.get(f"{PREFIX}/executions")
    assert resp.status_code == 200
    item = next(i for i in resp.json()["items"] if i["id"] == str(eid))
    assert item["name"] == "build the rocket"
    assert item["run_in_background"] is True
    assert item["assistant_name"] == "Planner"
    assert item["context"]["type"] == "project"
    assert item["context"]["name"] == "Apollo"
    assert item["context"]["project_id"] == str(proj)


# =====================================================================
# GET /executions/running-count
# =====================================================================


@pytest.mark.asyncio
async def test_running_count_counts_active_states(
    client: AsyncClient, db: AsyncSession, isolated_user: UUID
) -> None:
    """GET /executions/running-count counts running + awaiting_approval only."""
    asst = await _make_assistant(db)
    mine = await _make_session(db, isolated_user, asst)
    await _make_execution(db, mine, status=ExecutionStatus.RUNNING)
    await _make_execution(db, mine, status=ExecutionStatus.AWAITING_APPROVAL)
    await _make_execution(db, mine, status=ExecutionStatus.COMPLETED)
    await _make_execution(db, mine, status=ExecutionStatus.STOPPED)
    await db.commit()

    resp = await client.get(f"{PREFIX}/executions/running-count")
    assert resp.status_code == 200
    assert resp.json() == {"count": 2}


# =====================================================================
# POST /executions/{execution_id}/stop
# =====================================================================


@pytest.mark.asyncio
async def test_stop_unknown_execution_returns_404(client: AsyncClient) -> None:
    """POST /executions/{id}/stop returns 404 for an unknown execution id."""
    unknown = uuid.uuid4()
    resp = await client.post(f"{PREFIX}/executions/{unknown}/stop")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_stop_other_users_execution_returns_404_not_403(
    client: AsyncClient, db: AsyncSession
) -> None:
    """POST /executions/{id}/stop returns 404 (NOT 403) for another user's
    execution to avoid leaking existence."""
    asst = await _make_assistant(db)
    other_user = UUID("33333333-3333-3333-3333-333333333333")
    others = await _make_session(db, other_user, asst)
    eid = await _make_execution(db, others, status=ExecutionStatus.RUNNING)
    await db.commit()

    resp = await client.post(f"{PREFIX}/executions/{eid}/stop")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Execution not found"


@pytest.mark.asyncio
async def test_stop_owner_execution_invokes_request_stop_and_returns_204(
    client: AsyncClient, db: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """POST /executions/{id}/stop returns 204 for the owner and calls
    AgentService.request_stop."""
    asst = await _make_assistant(db)
    mine = await _make_session(db, TEST_USER_ID, asst)
    eid = await _make_execution(db, mine, status=ExecutionStatus.RUNNING)
    await db.commit()

    calls: list[str] = []

    # Patch request_stop at the route module's AgentService reference so the
    # endpoint calls our spy instead of the in-memory lifecycle.
    from app.api.routes import ai_chat

    def _fake_request_stop(execution_id: str) -> bool:
        calls.append(execution_id)
        return True

    monkeypatch.setattr(ai_chat.AgentService, "request_stop", _fake_request_stop)

    resp = await client.post(f"{PREFIX}/executions/{eid}/stop")
    assert resp.status_code == 204
    assert calls == [str(eid)]


@pytest.mark.asyncio
async def test_stop_returns_404_when_request_stop_reports_terminal(
    client: AsyncClient, db: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """POST /executions/{id}/stop returns 404 when request_stop reports the
    execution is unknown/terminal (already finished)."""
    asst = await _make_assistant(db)
    mine = await _make_session(db, TEST_USER_ID, asst)
    eid = await _make_execution(db, mine, status=ExecutionStatus.RUNNING)
    await db.commit()

    from app.api.routes import ai_chat

    monkeypatch.setattr(ai_chat.AgentService, "request_stop", lambda _eid: False)

    resp = await client.post(f"{PREFIX}/executions/{eid}/stop")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Execution not found or already terminal"
