"""Service-level tests for the main-agent model_id invariant.

The read-side validator ``AIAssistantConfigPublic.validate_main_agent_model``
raises when a main agent has ``model_id IS NULL``, which 500s the
``GET /api/v1/ai/config/assistants`` list endpoint if any such row exists.
The invariant is enforced at three layers:

* Create schema (``AIAssistantConfigCreate`` inherits the validator) -> 422.
* Service create (defense-in-depth for direct callers).
* Service update (the real gap: partial updates previously bypassed it).

Isolation: the shared ``db`` fixture commits at teardown, which would persist
the configs these tests create/mutate and pollute the live ``/config/assistants``
list. Each mutating test therefore uses the ``isolated_db`` fixture, which rolls
back at teardown so no test rows survive.
"""

from collections.abc import AsyncGenerator
from uuid import UUID

import pytest
import pytest_asyncio
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker
from app.models.schemas.ai import AIAssistantConfigCreate, AIAssistantConfigUpdate
from app.services.ai_config_service import AIConfigService

# Canonical glm-4.7 seed model id (stable, verified in ai_models).
GLM47_MODEL_ID = UUID("11111111-1111-1111-1111-111111111112")


@pytest_asyncio.fixture
async def isolated_db() -> AsyncGenerator[AsyncSession, None]:
    """A session that is rolled back at teardown (never committed).

    Unlike the shared ``db`` fixture, this does NOT commit, so the configs the
    service creates via ``flush()`` never reach the live DB. The full rollback
    undoes both the service's flushed changes and any in-flight mutations.
    """
    async with async_session_maker() as session:
        yield session
        await session.rollback()
        await session.close()


def test_create_schema_rejects_main_agent_without_model_id() -> None:
    """The Create schema rejects a main agent without model_id (422 at API)."""
    with pytest.raises(ValidationError, match="model_id is required for main agents"):
        AIAssistantConfigCreate(
            name="Test Main No Model",
            agent_type="main",
            model_id=None,
        )


def test_service_create_rejects_main_agent_without_model_id() -> None:
    """The service-layer create guard rejects a main agent without model_id.

    The Create schema already blocks this at the API boundary (422), so to
    exercise the service-layer guard directly we call the helper it delegates
    to. This proves the invariant holds for any direct service caller.
    """
    from app.services.ai_config_service import _enforce_main_agent_has_model

    with pytest.raises(ValueError, match="model_id is required for main agents"):
        _enforce_main_agent_has_model("main", None)


def test_service_guard_allows_specialist_without_model_id() -> None:
    """The service-layer guard allows a specialist to omit model_id."""
    from app.services.ai_config_service import _enforce_main_agent_has_model

    # Must not raise.
    _enforce_main_agent_has_model("specialist", None)
    _enforce_main_agent_has_model("specialist", GLM47_MODEL_ID)
    _enforce_main_agent_has_model("main", GLM47_MODEL_ID)


@pytest.mark.asyncio
async def test_create_specialist_without_model_id_is_allowed(
    isolated_db: AsyncSession,
) -> None:
    """A specialist may legitimately omit model_id (inherits from main)."""
    service = AIConfigService(isolated_db)
    config_in = AIAssistantConfigCreate(
        name="Test Specialist No Model",
        agent_type="specialist",
        model_id=None,
    )
    created = await service.create_assistant_config(config_in)
    assert created.agent_type == "specialist"
    assert created.model_id is None


@pytest.mark.asyncio
async def test_create_main_agent_with_model_id_succeeds(
    isolated_db: AsyncSession,
) -> None:
    """A main agent created with a valid model_id is accepted."""
    service = AIConfigService(isolated_db)
    config_in = AIAssistantConfigCreate(
        name="Test Main With Model",
        agent_type="main",
        model_id=GLM47_MODEL_ID,
    )
    created = await service.create_assistant_config(config_in)
    assert created.agent_type == "main"
    assert created.model_id == GLM47_MODEL_ID


@pytest.mark.asyncio
async def test_update_main_agent_clearing_model_id_is_rejected(
    isolated_db: AsyncSession,
) -> None:
    """A partial update must not leave a main agent without a model_id."""
    service = AIConfigService(isolated_db)
    created = await service.create_assistant_config(
        AIAssistantConfigCreate(
            name="Test Main Update Clear",
            agent_type="main",
            model_id=GLM47_MODEL_ID,
        )
    )
    with pytest.raises(ValueError, match="model_id is required for main agents"):
        await service.update_assistant_config(
            created.id, AIAssistantConfigUpdate(model_id=None)
        )


@pytest.mark.asyncio
async def test_update_specialist_to_main_without_model_id_is_rejected(
    isolated_db: AsyncSession,
) -> None:
    """Flipping a specialist to a main agent without setting model_id is rejected."""
    service = AIConfigService(isolated_db)
    created = await service.create_assistant_config(
        AIAssistantConfigCreate(
            name="Test Specialist Flip To Main",
            agent_type="specialist",
            model_id=None,
        )
    )
    with pytest.raises(ValueError, match="model_id is required for main agents"):
        await service.update_assistant_config(
            created.id, AIAssistantConfigUpdate(agent_type="main")
        )
