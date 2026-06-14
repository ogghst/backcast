"""FU-2: AI config constants must be sourced from the pydantic ``Settings``
singleton (which reads ``backend/.env``), not from a raw ``os.environ.get``
that never sees ``.env``.

Scope:
    * ``app.ai.config`` constants must equal the corresponding ``settings.X``.
    * A fresh ``Settings(_env_file=".env")`` must surface the real ``.env``
      values, proving ``.env`` actually flows through.
    * Bool env parsing must work for the migrated boolean fields.
"""

from pathlib import Path

import pytest

# Import the module-level constants (kept stable so all consumers keep working).
from app.ai.config import (
    AI_CONTEXT_KEEP_RECENT,
    AI_CONTEXT_SUMMARY_THRESHOLD_PCT,
    AI_CONTEXT_TOKEN_LIMIT,
    AI_DELEGATION_ENFORCED,
    AI_MCP_TOOL_CATEGORY_PREFIX,
    AI_SEQUENTIAL_TOOL_CALLS,
    AI_TOOLS_DEFAULT_PAGE_SIZE,
)
from app.core.config import Settings, settings

# backend/.env relative to this test file: tests/ -> backend/
BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BACKEND_DIR / ".env"


# ---------------------------------------------------------------------------
# 1. Wiring: every app.ai.config constant is sourced from settings.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("constant", "attr"),
    [
        (AI_CONTEXT_TOKEN_LIMIT, "AI_CONTEXT_TOKEN_LIMIT"),
        (AI_CONTEXT_SUMMARY_THRESHOLD_PCT, "AI_CONTEXT_SUMMARY_THRESHOLD_PCT"),
        (AI_CONTEXT_KEEP_RECENT, "AI_CONTEXT_KEEP_RECENT"),
        (AI_DELEGATION_ENFORCED, "AI_DELEGATION_ENFORCED"),
        (AI_SEQUENTIAL_TOOL_CALLS, "AI_SEQUENTIAL_TOOL_CALLS"),
        (AI_MCP_TOOL_CATEGORY_PREFIX, "AI_MCP_TOOL_CATEGORY_PREFIX"),
        (AI_TOOLS_DEFAULT_PAGE_SIZE, "AI_TOOLS_DEFAULT_PAGE_SIZE"),
    ],
)
def test_ai_config_constants_sourced_from_settings(constant: object, attr: str) -> None:
    """Each ``app.ai.config`` constant must equal ``settings.<attr>``.

    This proves the constant is sourced from the Settings singleton rather than
    a stale ``os.environ.get`` that bypasses ``.env`` loading.
    """
    assert constant == getattr(settings, attr)


# ---------------------------------------------------------------------------
# 2. .env actually flows through (self-contained: fresh Settings pointed at .env).
# ---------------------------------------------------------------------------


def test_env_file_governs_ai_context_values() -> None:
    """``backend/.env`` values must surface on a fresh ``Settings``.

    Instantiates ``Settings`` pointed explicitly at ``backend/.env`` so the test
    does not depend on whatever global env was active at import time.
    """
    if not ENV_FILE.exists():  # pragma: no cover - sanity guard
        pytest.skip(f"{ENV_FILE} not present; cannot verify .env flow")

    env_settings = Settings(_env_file=str(ENV_FILE))

    # The real values currently hardcoded in backend/.env.
    assert env_settings.AI_CONTEXT_TOKEN_LIMIT == 500000
    assert env_settings.AI_CONTEXT_KEEP_RECENT == 49


# ---------------------------------------------------------------------------
# 3. Bool parsing: boolean fields parse env strings correctly.
# ---------------------------------------------------------------------------


def test_bool_field_parsed_from_env() -> None:
    """Boolean AI fields must be parsed as real bools by pydantic v2.

    ``backend/.env`` sets ``AI_DELEGATION_ENFORCED=false`` and
    ``AI_SEQUENTIAL_TOOL_CALLS=true``; the freshly-loaded Settings must reflect
    parsed booleans (not strings), proving the bool migration is sound.
    """
    if not ENV_FILE.exists():  # pragma: no cover - sanity guard
        pytest.skip(f"{ENV_FILE} not present; cannot verify bool parsing")

    env_settings = Settings(_env_file=str(ENV_FILE))

    assert isinstance(env_settings.AI_DELEGATION_ENFORCED, bool)
    assert isinstance(env_settings.AI_SEQUENTIAL_TOOL_CALLS, bool)
    # .env governs these values (do not hardcode the code default here).
    assert env_settings.AI_DELEGATION_ENFORCED is False
    assert env_settings.AI_SEQUENTIAL_TOOL_CALLS is True


def test_bool_defaults_documented() -> None:
    """The boolean AI fields declare the documented defaults on the model.

    Guards against an accidental type/annotation change during the migration by
    inspecting the field-level defaults directly (independent of env vars).
    """
    fields = Settings.model_fields
    assert fields["AI_DELEGATION_ENFORCED"].default is True
    assert fields["AI_SEQUENTIAL_TOOL_CALLS"].default is True
    assert fields["AI_DELEGATION_ENFORCED"].annotation is bool
    assert fields["AI_SEQUENTIAL_TOOL_CALLS"].annotation is bool
