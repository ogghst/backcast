"""Tests for Fix B: supervisor + ask_user clarification-discipline guardrail.

The supervisor re-asks questions the user has already answered because nothing
in its prompt forbids it and the ask_user tool description does not warn
against it.  These are soft guardrails: a dedicated ``## Clarification
discipline`` section is added to ``_BASE_SUPERVISOR_PROMPT`` and the ask_user
tool description is prefixed with a "do not re-ask" clause.
"""

from __future__ import annotations

from app.ai.supervisor_orchestrator import _BASE_SUPERVISOR_PROMPT
from app.ai.tools.ask_user import ask_user

# ===========================================================================
# Supervisor prompt: clarification-discipline section
# ===========================================================================


def test_supervisor_prompt_has_never_reask_clause() -> None:
    """The prompt must forbid re-asking an already-answered question."""
    assert "NEVER re-ask" in _BASE_SUPERVISOR_PROMPT


def test_supervisor_prompt_has_sparingly_clause() -> None:
    """The prompt must instruct using ask_user sparingly."""
    assert "sparingly" in _BASE_SUPERVISOR_PROMPT


def test_supervisor_prompt_has_clarification_discipline_section() -> None:
    """A dedicated ``## Clarification discipline`` section exists before Rules."""
    assert "## Clarification discipline" in _BASE_SUPERVISOR_PROMPT
    # The section must precede the Rules section.
    assert _BASE_SUPERVISOR_PROMPT.index("## Clarification discipline") < (
        _BASE_SUPERVISOR_PROMPT.index("## Rules")
    )


# ===========================================================================
# ask_user tool description guardrail prefix
# ===========================================================================


def test_ask_user_description_has_guardrail_prefix() -> None:
    """The ask_user tool description must lead with the do-not-re-ask clause."""
    desc = ask_user.description or ""
    assert "NEVER re-ask" in desc
    assert "genuinely-missing" in desc
    # The guardrail prefix must come BEFORE the legacy "Ask the user" sentence
    # so it is the first thing the model reads.
    assert desc.index("NEVER re-ask") < desc.index("Ask the user")
