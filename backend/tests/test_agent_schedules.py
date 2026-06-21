"""Tests for the agent scheduling backend (WS-1 + WS-2).

Covers:
- compute_next_run valid/invalid
- create with invalid cron → 422 (validation before DB write)
- create + read round-trip (next_run_at set + in the future)
- trigger overlap → 409 (overlap check short-circuits before create_task)
- toggle flips is_active + clears next_run_at
- context-scope configuration (global / project / WBE): project_id is derived
  from the validated SessionContext, and authorization is enforced
  (project access + WBE existence). Service-level _authorize_scope is unit
  tested directly with a mocked RBAC service.

RBAC is bypassed globally in conftest (TEST_USER_ID is the seeded admin).
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker
from app.models.domain.ai import AIAgentExecution
from app.models.schemas.ai_agent_schedule import compute_next_run
from app.services import agent_schedule_service as agent_schedule_service_module

# Seeded project + WBE used for context-scope tests (verified present in dev DB).
SEEDED_PROJECT_ID = "10000000-0000-4000-8000-000000000001"
SEEDED_WBE_ID = "20000000-0000-4000-8000-000000000001"


def test_compute_next_run_valid() -> None:
    """A valid cron expression returns a future UTC datetime."""
    nxt = compute_next_run("*/5 * * * *")
    assert isinstance(nxt, datetime)
    assert nxt.tzinfo is not None
    assert nxt > datetime.now(UTC)


def test_compute_next_run_invalid_cron_raises() -> None:
    """An invalid cron expression raises ValueError (surfaces as 422)."""
    with pytest.raises(ValueError):
        compute_next_run("not a cron")


async def _get_assistant_config_id() -> UUID:
    """Return an existing assistant config id from the seeded DB."""
    from app.models.domain.ai import AIAssistantConfig

    async with async_session_maker() as db:
        row = (
            await db.execute(select(AIAssistantConfig.id).limit(1))
        ).scalar_one_or_none()
    assert row is not None, "test DB must have at least one AIAssistantConfig"
    return UUID(str(row))


@pytest.mark.asyncio
async def test_create_schedule_invalid_cron_422(client: AsyncClient) -> None:
    """Invalid cron_expr returns 422 (validation runs before DB insert)."""
    config_id = await _get_assistant_config_id()
    resp = await client.post(
        "/ai/agent-schedules",
        json={
            "name": "bad cron",
            "prompt": "hello",
            "assistant_config_id": str(config_id),
            "cron_expr": "garbage",
            "timezone": "UTC",
        },
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_create_and_read_schedule(client: AsyncClient) -> None:
    """A valid schedule round-trips and next_run_at is set + future."""
    config_id = await _get_assistant_config_id()
    payload = {
        "name": "nightly summary",
        "prompt": "Summarize today's cost events",
        "assistant_config_id": str(config_id),
        "execution_mode": "standard",
        "cron_expr": "0 9 * * *",
        "timezone": "UTC",
        "is_active": True,
    }
    create_resp = await client.post("/ai/agent-schedules", json=payload)
    assert create_resp.status_code == 201, create_resp.text
    created = create_resp.json()
    schedule_id = created["id"]
    assert created["next_run_at"] is not None
    nxt = datetime.fromisoformat(created["next_run_at"])
    assert nxt > datetime.now(UTC)

    # read it back
    get_resp = await client.get(f"/ai/agent-schedules/{schedule_id}")
    assert get_resp.status_code == 200, get_resp.text
    fetched = get_resp.json()
    assert fetched["id"] == schedule_id
    assert fetched["name"] == "nightly summary"
    assert fetched["next_run_at"] == created["next_run_at"]

    # cleanup
    del_resp = await client.delete(f"/ai/agent-schedules/{schedule_id}")
    assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_trigger_overlap_returns_409(client: AsyncClient) -> None:
    """An active execution for the schedule blocks a trigger with 409.

    The overlap check short-circuits BEFORE asyncio.create_task, so no agent
    run actually starts — we only assert the 409.
    """
    config_id = await _get_assistant_config_id()
    create_resp = await client.post(
        "/ai/agent-schedules",
        json={
            "name": "overlap test",
            "prompt": "hi",
            "assistant_config_id": str(config_id),
            "cron_expr": "*/10 * * * *",
            "timezone": "UTC",
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    schedule_id = create_resp.json()["id"]

    # Insert an active execution referencing this schedule directly.
    async with async_session_maker() as db:
        # need a real session_id to satisfy the FK; reuse an existing one.
        from app.models.domain.ai import AIConversationSession

        session_row = (
            await db.execute(select(AIConversationSession.id).limit(1))
        ).scalar_one_or_none()
        assert session_row is not None, "test DB must have a conversation session"
        db.add(
            AIAgentExecution(
                session_id=str(session_row),
                status="running",
                execution_mode="standard",
                run_in_background=True,
                schedule_id=str(UUID(schedule_id)),
            )
        )
        await db.commit()

    try:
        trig_resp = await client.post(f"/ai/agent-schedules/{schedule_id}/trigger")
        assert trig_resp.status_code == 409, trig_resp.text
    finally:
        # cleanup: delete the schedule (FK on executions is RESTRICT-by-default
        # nullable, so remove the blocking execution first).
        async with async_session_maker() as db:
            await db.execute(
                AIAgentExecution.__table__.delete().where(
                    AIAgentExecution.schedule_id == str(UUID(schedule_id))
                )
            )
            await db.commit()
        del_resp = await client.delete(f"/ai/agent-schedules/{schedule_id}")
        assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_trigger_success_creates_running_execution(client: AsyncClient) -> None:
    """A trigger with no active execution creates a fresh session + a RUNNING
    execution row and returns 200.

    Regression: schedule UUID columns return UUID objects at runtime
    (PG_UUID as_uuid=True), and the trigger used to wrap them in ``UUID(...)``,
    which raised ``AttributeError: 'UUID' object has no attribute 'replace'``.
    The fire-and-forget launcher is mocked so no real agent run starts; the
    synchronous part (create_session UUID coercion + the pre-created RUNNING
    row) is what this exercises.
    """
    config_id = await _get_assistant_config_id()
    create_resp = await client.post(
        "/ai/agent-schedules",
        json={
            "name": "trigger success test",
            "prompt": "hi",
            "assistant_config_id": str(config_id),
            "cron_expr": "*/10 * * * *",
            "timezone": "UTC",
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    schedule_id = create_resp.json()["id"]

    # No executions for this schedule before triggering.
    async with async_session_maker() as db:
        pre = (
            await db.execute(
                select(AIAgentExecution.id).where(
                    AIAgentExecution.schedule_id == str(UUID(schedule_id))
                )
            )
        ).all()
    assert pre == []

    # Mock the fire-and-forget launcher so no real agent run / LLM call happens.
    with patch.object(
        agent_schedule_service_module, "_run_schedule_execution", AsyncMock()
    ):
        trig_resp = await client.post(f"/ai/agent-schedules/{schedule_id}/trigger")

    assert trig_resp.status_code == 200, trig_resp.text
    body = trig_resp.json()
    assert body["execution_id"]
    assert body["session_id"]

    # A RUNNING execution row was created inside the locked transaction.
    async with async_session_maker() as db:
        row = (
            await db.execute(
                select(AIAgentExecution).where(
                    AIAgentExecution.id == UUID(body["execution_id"])
                )
            )
        ).scalar_one_or_none()
    assert row is not None, "pre-created RUNNING execution row missing"
    assert row.status == "running"
    assert row.run_in_background is True
    assert str(row.schedule_id) == str(UUID(schedule_id))

    # cleanup
    async with async_session_maker() as db:
        await db.execute(
            AIAgentExecution.__table__.delete().where(
                AIAgentExecution.schedule_id == str(UUID(schedule_id))
            )
        )
        await db.commit()
    del_resp = await client.delete(f"/ai/agent-schedules/{schedule_id}")
    assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_toggle_schedule(client: AsyncClient) -> None:
    """Toggle flips is_active and clears next_run_at on deactivation."""
    config_id = await _get_assistant_config_id()
    create_resp = await client.post(
        "/ai/agent-schedules",
        json={
            "name": "toggle test",
            "prompt": "hi",
            "assistant_config_id": str(config_id),
            "cron_expr": "*/15 * * * *",
            "timezone": "UTC",
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    schedule_id = create_resp.json()["id"]
    assert create_resp.json()["is_active"] is True
    assert create_resp.json()["next_run_at"] is not None

    # toggle off → inactive + next_run_at cleared
    off_resp = await client.post(f"/ai/agent-schedules/{schedule_id}/toggle")
    assert off_resp.status_code == 200, off_resp.text
    off = off_resp.json()
    assert off["is_active"] is False
    assert off["next_run_at"] is None

    # toggle back on → active + next_run_at repopulated
    on_resp = await client.post(f"/ai/agent-schedules/{schedule_id}/toggle")
    assert on_resp.status_code == 200, on_resp.text
    on = on_resp.json()
    assert on["is_active"] is True
    assert on["next_run_at"] is not None

    # cleanup
    del_resp = await client.delete(f"/ai/agent-schedules/{schedule_id}")
    assert del_resp.status_code == 204


# ---------------------------------------------------------------------------
# Context-scope configuration (global / project / WBE)
# ---------------------------------------------------------------------------


async def _create_schedule(client: AsyncClient, payload: dict) -> dict:
    """Create a schedule and return the parsed JSON body, asserting 201."""
    resp = await client.post("/ai/agent-schedules", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _cleanup_schedule(client: AsyncClient, schedule_id: str) -> None:
    """Delete a schedule created during a test (best-effort)."""
    await client.delete(f"/ai/agent-schedules/{schedule_id}")


def _base_context_payload(context: dict | None) -> dict:
    """Minimal valid create payload, optionally overriding context."""
    payload: dict = {
        "name": "ctx scope test",
        "prompt": "hi",
        "cron_expr": "*/15 * * * *",
        "timezone": "UTC",
    }
    if context is not None:
        payload["context"] = context
    return payload


@pytest.mark.asyncio
async def test_create_schedule_global_context(client: AsyncClient) -> None:
    """An explicit {type:general} context yields project_id=None."""
    config_id = await _get_assistant_config_id()
    created = await _create_schedule(
        client,
        _base_context_payload({"type": "general"})
        | {"assistant_config_id": str(config_id)},
    )
    schedule_id = created["id"]
    try:
        assert created["project_id"] is None
        assert created["context"] == {"type": "general"}

        # read back
        fetched = (await client.get(f"/ai/agent-schedules/{schedule_id}")).json()
        assert fetched["project_id"] is None
        assert fetched["context"]["type"] == "general"
    finally:
        await _cleanup_schedule(client, schedule_id)


@pytest.mark.asyncio
async def test_create_schedule_project_context(client: AsyncClient) -> None:
    """A {type:project, id:<pid>} context derives project_id=<pid>."""
    config_id = await _get_assistant_config_id()
    created = await _create_schedule(
        client,
        _base_context_payload(
            {"type": "project", "id": SEEDED_PROJECT_ID, "name": "Line Alpha"}
        )
        | {"assistant_config_id": str(config_id)},
    )
    schedule_id = created["id"]
    try:
        assert created["project_id"] == SEEDED_PROJECT_ID
        assert created["context"]["type"] == "project"
        assert created["context"]["id"] == SEEDED_PROJECT_ID

        fetched = (await client.get(f"/ai/agent-schedules/{schedule_id}")).json()
        assert fetched["project_id"] == SEEDED_PROJECT_ID
        assert fetched["context"]["type"] == "project"
    finally:
        await _cleanup_schedule(client, schedule_id)


@pytest.mark.asyncio
async def test_create_schedule_wbe_context(client: AsyncClient) -> None:
    """A {type:wbe, id:<wbe>, project_id:<pid>} context derives project_id=<pid>."""
    config_id = await _get_assistant_config_id()
    created = await _create_schedule(
        client,
        _base_context_payload(
            {
                "type": "wbe",
                "id": SEEDED_WBE_ID,
                "project_id": SEEDED_PROJECT_ID,
                "name": "Assembly Station 1",
            }
        )
        | {"assistant_config_id": str(config_id)},
    )
    schedule_id = created["id"]
    try:
        assert created["project_id"] == SEEDED_PROJECT_ID
        assert created["context"]["type"] == "wbe"
        assert created["context"]["id"] == SEEDED_WBE_ID

        fetched = (await client.get(f"/ai/agent-schedules/{schedule_id}")).json()
        assert fetched["project_id"] == SEEDED_PROJECT_ID
        assert fetched["context"]["type"] == "wbe"
    finally:
        await _cleanup_schedule(client, schedule_id)


@pytest.mark.asyncio
async def test_create_schedule_invalid_context_422(client: AsyncClient) -> None:
    """A WBE context missing project_id is rejected with 422."""
    config_id = await _get_assistant_config_id()
    resp = await client.post(
        "/ai/agent-schedules",
        json=_base_context_payload({"type": "wbe", "id": SEEDED_WBE_ID})
        | {"assistant_config_id": str(config_id)},
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_create_schedule_derives_project_id_from_context(
    client: AsyncClient,
) -> None:
    """A project context overrides a mismatched/None project_id (server-derived)."""
    config_id = await _get_assistant_config_id()
    created = await _create_schedule(
        client,
        _base_context_payload({"type": "project", "id": SEEDED_PROJECT_ID})
        # Explicitly WRONG project_id — the validator must overwrite it.
        | {
            "assistant_config_id": str(config_id),
            "project_id": "00000000-0000-4000-8000-000000000001",
        },
    )
    schedule_id = created["id"]
    try:
        assert created["project_id"] == SEEDED_PROJECT_ID, created["project_id"]
    finally:
        await _cleanup_schedule(client, schedule_id)


@pytest.mark.asyncio
async def test_update_schedule_context_replaces_scope(client: AsyncClient) -> None:
    """Patching context replaces the scope + derives a new project_id."""
    config_id = await _get_assistant_config_id()
    # Start as global.
    created = await _create_schedule(
        client,
        _base_context_payload({"type": "general"})
        | {"assistant_config_id": str(config_id)},
    )
    schedule_id = created["id"]
    try:
        assert created["project_id"] is None

        # Patch to project scope.
        patch_resp = await client.put(
            f"/ai/agent-schedules/{schedule_id}",
            json={
                "context": {
                    "type": "project",
                    "id": SEEDED_PROJECT_ID,
                    "name": "Line Alpha",
                }
            },
        )
        assert patch_resp.status_code == 200, patch_resp.text
        patched = patch_resp.json()
        assert patched["context"]["type"] == "project"
        assert patched["project_id"] == SEEDED_PROJECT_ID

        # Read back reflects the replaced scope.
        fetched = (await client.get(f"/ai/agent-schedules/{schedule_id}")).json()
        assert fetched["context"]["type"] == "project"
        assert fetched["project_id"] == SEEDED_PROJECT_ID
    finally:
        await _cleanup_schedule(client, schedule_id)


# ---------------------------------------------------------------------------
# _authorize_scope unit tests (RBAC mocked — no non-admin user needed)
# ---------------------------------------------------------------------------


class _FakeRBAC:
    """Minimal RBAC service stub returning a fixed accessible-projects list."""

    def __init__(self, accessible: list[UUID]) -> None:
        self._accessible = accessible

    async def get_accessible_projects(self, user_id: UUID) -> list[UUID]:  # noqa: ARG002
        return self._accessible


@pytest.mark.asyncio
async def test_authorize_scope_denies_project_access(db: AsyncSession) -> None:
    """A project the owner cannot access raises ValueError."""
    svc = agent_schedule_service_module.AgentScheduleService(db)
    inaccessible = UUID("00000000-0000-4000-8000-000000000099")
    owner = UUID("11111111-1111-4111-8111-111111111111")
    fake = _FakeRBAC(accessible=[])
    with patch.object(
        agent_schedule_service_module,
        "get_unified_rbac_service",
        return_value=fake,
    ):
        with pytest.raises(ValueError, match="No access to project"):
            await svc._authorize_scope(
                owner_user_id=owner,
                project_id=inaccessible,
                context={"type": "project", "id": str(inaccessible)},
            )


@pytest.mark.asyncio
async def test_authorize_scope_wbe_not_found_in_project(db: AsyncSession) -> None:
    """A WBE not owned by the (accessible) project raises ValueError."""
    svc = agent_schedule_service_module.AgentScheduleService(db)
    owner = UUID("11111111-1111-4111-8111-111111111111")
    bogus_wbe = UUID("00000000-0000-4000-8000-000000000099")
    fake = _FakeRBAC(accessible=[UUID(SEEDED_PROJECT_ID)])
    with patch.object(
        agent_schedule_service_module,
        "get_unified_rbac_service",
        return_value=fake,
    ):
        with pytest.raises(ValueError, match="WBS element .* not found in project"):
            await svc._authorize_scope(
                owner_user_id=owner,
                project_id=UUID(SEEDED_PROJECT_ID),
                context={
                    "type": "wbe",
                    "id": str(bogus_wbe),
                    "project_id": SEEDED_PROJECT_ID,
                },
            )
