"""Phase-2 specialist-config invariants + sync_specialists.py regression tests.

Asserts the Phase-2 + migration changes hold:

1. **Seed invariants** (``seed/seed_system_config.json``):
   - Every main assistant's ``delegation_config.direct_tools`` is small (<= 5).
   - No main assistant lost ``ask_user`` (load-bearing for clarification loops).
   - ``general_purpose`` ``allowed_tools`` is a concrete list with NO ``"*"``
     wildcard (the 12.1k-token footgun is gone).
   - Every tool name referenced in seed lists is a real registered tool.
   - ``allowed_specialists`` is preserved on each main assistant.

2. **sync_specialists.py migration fixes**:
   - Specialist names are derived from the seed (no hardcoded tuple), so the
     script cannot silently skip a seed-declared specialist.
   - ``main()`` calls ``app.ai.subagents.db_loader.invalidate_cache`` after
     committing, so the 5-minute TTL cache is cleared immediately.
   - A post-sync roster assertion exists.

These are pure-config / static checks; no DB or LLM is exercised.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2]
SEED_FILE = BACKEND_DIR / "seed" / "seed_system_config.json"
SYNC_SCRIPT = BACKEND_DIR / "scripts" / "sync_specialists.py"


def _load_seed() -> dict[str, Any]:
    with open(SEED_FILE) as f:
        return json.load(f)


def _registered_tool_names() -> set[str]:
    """Ground-truth tool names from the BaseTool instances (excl. dynamic MCP).

    Mirrors ``create_project_tools`` — enumerates the module-level ``@ai_tool``
    objects directly so we don't need a live ``ToolContext``/session.
    """
    from langchain_core.tools import BaseTool

    from app.ai.tools import (
        ask_user as ask_user_module,
    )
    from app.ai.tools import (
        briefing_tools,
        context_tools,
        document_tools,
        project_tools,
        temporal_tools,
    )
    from app.ai.tools.templates import (
        advanced_analysis_template,
        analysis_template,
        change_order_template,
        control_account_template,
        cost_element_template,
        cost_event_template,
        cost_event_type_template,
        diagram_template,
        forecast_cost_progress_template,
        project_template,
        user_management_template,
        work_package_template,
    )

    modules = [
        project_tools,
        project_template,
        cost_element_template,
        cost_event_template,
        cost_event_type_template,
        forecast_cost_progress_template,
        control_account_template,
        work_package_template,
        change_order_template,
        analysis_template,
        advanced_analysis_template,
        user_management_template,
        diagram_template,
        briefing_tools,
        context_tools,
        document_tools,
        temporal_tools,
        ask_user_module,
    ]
    names: set[str] = set()
    for mod in modules:
        for _name, obj in inspect.getmembers(mod):
            if isinstance(obj, BaseTool):
                names.add(obj.name)
    return names


# ---------------------------------------------------------------------------
# Seed invariants
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def seed() -> dict[str, Any]:
    return _load_seed()


def test_seed_main_assistants_direct_tools_are_small(seed: dict[str, Any]) -> None:
    """Phase-2: main assistants bind <= 5 direct_tools (was ~26).

    The bound is 5 (not 4) to accommodate ``set_project_context``, the
    cross-turn project-scope direct tool added alongside this work.
    """
    for a in seed["ai_assistant_configs"]:
        dt = a["delegation_config"]["direct_tools"]
        assert len(dt) <= 5, f"{a['name']} has {len(dt)} direct_tools (expected <=5)"


def test_seed_main_assistants_keep_ask_user(seed: dict[str, Any]) -> None:
    """ask_user must never be dropped from a main assistant's direct_tools."""
    for a in seed["ai_assistant_configs"]:
        assert "ask_user" in a["delegation_config"]["direct_tools"], a["name"]


def test_seed_main_assistants_preserve_allowed_specialists(
    seed: dict[str, Any],
) -> None:
    """allowed_specialists must remain a non-empty list on every main assistant."""
    for a in seed["ai_assistant_configs"]:
        allowed = a["delegation_config"].get("allowed_specialists")
        assert isinstance(allowed, list) and allowed, a["name"]


def test_seed_general_purpose_has_no_wildcard(seed: dict[str, Any]) -> None:
    """Phase-2: general_purpose must NOT use the '*' wildcard (was 12.1k tok)."""
    gp = next(
        s for s in seed["ai_specialist_configs"] if s["name"] == "general_purpose"
    )
    assert gp["allowed_tools"] != ["*"]
    assert "*" not in gp["allowed_tools"]
    assert isinstance(gp["allowed_tools"], list) and len(gp["allowed_tools"]) >= 8


def test_seed_referenced_tool_names_are_registered(seed: dict[str, Any]) -> None:
    """Every tool name in seed direct_tools / allowed_tools is a real tool.

    Static ``@ai_tool`` names are validated against the registry. Tools
    sourced from external MCP servers (e.g. ``tavily_*``) are loaded
    dynamically by ``MCPClientManager`` at runtime, so they are not in the
    static registry — they are allowed when the seed declares a matching
    ``mcp_servers`` entry with that prefix.
    """
    registry = _registered_tool_names()

    # Build the set of MCP tool-name prefixes from the seed's mcp_servers
    # (e.g. "tavily" server -> allow any "tavily_*" tool name).
    mcp_prefixes: set[str] = set()
    for srv in seed.get("mcp_servers", []):
        name = srv.get("name")
        if name:
            mcp_prefixes.add(f"{name}_")

    def _is_known(owner: str, tool: str) -> bool:
        if tool in registry:
            return True
        return any(tool.startswith(p) for p in mcp_prefixes)

    referenced: list[tuple[str, str]] = []
    for a in seed["ai_assistant_configs"]:
        for t in a["delegation_config"]["direct_tools"]:
            referenced.append((a["name"], t))
    for s in seed["ai_specialist_configs"]:
        for t in s.get("allowed_tools") or []:
            referenced.append((s["name"], t))
    unknown = [(owner, t) for owner, t in referenced if not _is_known(owner, t)]
    assert not unknown, f"unknown tool names in seed: {unknown}"


# ---------------------------------------------------------------------------
# sync_specialists.py migration fixes
# ---------------------------------------------------------------------------


def _sync_module() -> ModuleType:
    import importlib.util

    spec = importlib.util.spec_from_file_location("sync_specialists", SYNC_SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_sync_specialists_no_hardcoded_name_tuple() -> None:
    """Migration (a): the hardcoded SPECIALIST_NAMES tuple is gone."""
    src = SYNC_SCRIPT.read_text()
    assert "SPECIALIST_NAMES" not in src, (
        "sync_specialists.py still defines SPECIALIST_NAMES; derive from seed instead"
    )


def test_sync_specialists_derives_names_from_seed() -> None:
    """Migration (a): specialist names come from the seed's specialist-config keys."""
    mod = _sync_module()
    seed_names = {s["name"] for s in _load_seed()["ai_specialist_configs"]}
    assert set(mod._seed_specialist_names()) == seed_names


def test_sync_specialists_calls_invalidate_cache() -> None:
    """Migration (b): main() clears the db_loader cache after commit."""
    src = SYNC_SCRIPT.read_text()
    assert "invalidate_cache()" in src
    # It must be the real db_loader symbol, not a local no-op.
    mod = _sync_module()
    assert mod.invalidate_cache.__module__.startswith("app.ai.subagents.db_loader")


def test_sync_specialists_has_roster_assertion() -> None:
    """Migration (c): a post-sync assertion re-reads the DB roster."""
    mod = _sync_module()
    assert hasattr(mod, "assert_roster")
    assert inspect.iscoroutinefunction(mod.assert_roster)
    src = SYNC_SCRIPT.read_text()
    assert "assert_roster" in src
