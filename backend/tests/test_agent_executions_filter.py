"""Filter tests for ``GET /ai/chat/executions`` (the Agents History / "See runs"
list): ``schedule_id`` + ``started_from`` / ``started_to``.

Uses the running dev DB and the ``client`` fixture (authed as the seeded admin
``TEST_USER_ID``). Inserts a session owned by the test user plus executions with
varying ``schedule_id`` / ``started_at``, then asserts the filters narrow the
list correctly.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.db.session import async_session_maker
from app.models.domain.ai import (
    AIAgentExecution,
    AIAssistantConfig,
    AIConversationSession,
)
from tests.conftest import TEST_USER_ID


async def _make_session_owned_by_test_user() -> UUID:
    """Insert a conversation session owned by TEST_USER_ID; return its id."""
    async with async_session_maker() as db:
        cfg = (await db.execute(select(AIAssistantConfig.id).limit(1))).scalar_one()
        session = AIConversationSession(
            user_id=TEST_USER_ID,
            assistant_config_id=cfg,
            context={"type": "general"},
        )
        db.add(session)
        await db.commit()
        return session.id


async def _add_execution(
    *,
    session_id: UUID,
    schedule_id: UUID | None,
    started_at: datetime,
    status: str = "completed",
) -> None:
    async with async_session_maker() as db:
        db.add(
            AIAgentExecution(
                session_id=session_id,
                schedule_id=schedule_id,
                status=status,
                execution_mode="standard",
                run_in_background=True,
                started_at=started_at,
            )
        )
        await db.commit()


async def _cleanup(session_id: UUID) -> None:
    async with async_session_maker() as db:
        await db.execute(
            AIAgentExecution.__table__.delete().where(
                AIAgentExecution.session_id == session_id
            )
        )
        await db.execute(
            AIConversationSession.__table__.delete().where(
                AIConversationSession.id == session_id
            )
        )
        await db.commit()


@pytest.mark.asyncio
async def test_executions_filter_by_schedule_and_date(client: AsyncClient) -> None:
    """schedule_id narrows to that schedule's runs; started_from/to bound started_at."""
    session_id = await _make_session_owned_by_test_user()
    target = uuid4()
    other = uuid4()
    now = datetime.now(UTC)
    try:
        # target schedule: one recent (1h ago) + one old (3d ago)
        await _add_execution(
            session_id=session_id,
            schedule_id=target,
            started_at=now - timedelta(hours=1),
        )
        await _add_execution(
            session_id=session_id,
            schedule_id=target,
            started_at=now - timedelta(days=3),
        )
        # a different schedule + an unscheduled run, both recent (must be excluded)
        await _add_execution(
            session_id=session_id,
            schedule_id=other,
            started_at=now - timedelta(hours=1),
        )
        await _add_execution(
            session_id=session_id, schedule_id=None, started_at=now - timedelta(hours=1)
        )

        # schedule_id filter → exactly target's 2 runs
        r = await client.get(
            "/ai/chat/executions",
            params={"schedule_id": str(target), "limit": 50},
        )
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        assert len(items) == 2
        assert all(it["schedule_id"] == str(target) for it in items)
        assert r.json()["total"] == 2

        # + started_from (1d ago) → only the recent target run
        r = await client.get(
            "/ai/chat/executions",
            params={
                "schedule_id": str(target),
                "started_from": (now - timedelta(days=1)).isoformat(),
                "limit": 50,
            },
        )
        assert r.status_code == 200, r.text
        assert len(r.json()["items"]) == 1

        # + started_to (1d ago) → only the old target run
        r = await client.get(
            "/ai/chat/executions",
            params={
                "schedule_id": str(target),
                "started_to": (now - timedelta(days=1)).isoformat(),
                "limit": 50,
            },
        )
        assert r.status_code == 200, r.text
        assert len(r.json()["items"]) == 1

        # date range alone (no schedule_id) excludes the old run but keeps the 3 recent
        r = await client.get(
            "/ai/chat/executions",
            params={
                "started_from": (now - timedelta(days=1)).isoformat(),
                "limit": 50,
            },
        )
        items = r.json()["items"]
        assert all(
            it["started_at"] >= (now - timedelta(days=1)).isoformat() for it in items
        )
        assert any(it["schedule_id"] == str(target) for it in items)
    finally:
        await _cleanup(session_id)
