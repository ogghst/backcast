"""Phase-3 tool-description hygiene regression tests.

Asserts that:
1. The duplicated ~90-token pagination sermon ("results are paginated -- the
   returned list may be a SUBSET ...") has been removed from every ``find_*``
   and list/search tool description.
2. Each trimmed tool still converts to a valid OpenAI tool schema via
   ``convert_to_openai_tool`` (smoke test -- no exception, well-formed JSON).
3. ``add_document`` and ``ask_user`` descriptions remain unambiguous about
   purpose and their load-bearing required inputs.

These are pure-description checks; no tool signatures, behavior, or params
are exercised here.
"""

from __future__ import annotations

import json

import pytest
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool

from app.ai.tools import ask_user as ask_user_module
from app.ai.tools import document_tools, project_tools
from app.ai.tools.templates import (
    change_order_template,
    control_account_template,
    cost_element_template,
    cost_event_template,
    cost_event_type_template,
    forecast_cost_progress_template,
    project_template,
    user_management_template,
    work_package_template,
)

# The duplicated pagination sermon that was stripped in Phase 3. Any sub-string
# unique to the old verbose block is sufficient -- this phrase appeared in every
# copy of the sermon and nowhere in the trimmed (one-line) descriptions.
_PAGINATION_SERMON_MARKER = "returned list may be a SUBSET"


def _desc(tool: BaseTool) -> str:
    """Pull the description string off a @ai_tool-decorated StructuredTool."""
    return getattr(tool, "description", "") or ""


# (module, attribute) pairs for every tool whose description was trimmed.
TRIMMED_TOOLS = [
    (project_tools, "list_projects"),
    (project_tools, "global_search"),
    (project_template, "find_wbs_elements"),
    (cost_element_template, "find_cost_elements"),
    (cost_element_template, "find_cost_element_types"),
    (cost_event_template, "find_cost_events"),
    (cost_event_type_template, "find_cost_event_types"),
    (control_account_template, "find_control_accounts"),
    (work_package_template, "find_work_packages"),
    (change_order_template, "find_change_orders"),
    (user_management_template, "find_users"),
    (user_management_template, "find_organizational_units"),
    (forecast_cost_progress_template, "list_cost_registrations"),
    (forecast_cost_progress_template, "get_progress_data"),
    (document_tools, "add_document"),
    (ask_user_module, "ask_user"),
]


def _resolve(module: object, attr: str) -> BaseTool:
    return getattr(module, attr)


@pytest.mark.parametrize(
    ("module", "attr"),
    TRIMMED_TOOLS,
    ids=[attr for _, attr in TRIMMED_TOOLS],
)
def test_trimmed_descriptions_drop_pagination_sermon(module: object, attr: str) -> None:
    """No trimmed tool description repeats the old verbose pagination block."""
    tool = _resolve(module, attr)
    description = _desc(tool)
    assert _PAGINATION_SERMON_MARKER not in description, (
        f"{attr} description still contains the duplicated pagination sermon; "
        f"it should rely on the short 'check total/has_more and page forward' "
        f"line plus the tool's own limit/offset params. Got: {description!r}"
    )
    # Sanity: every trimmed description is non-empty and meaningfully shorter
    # than its pre-Phase-3 form. add_document / ask_user legitimately keep more
    # load-bearing constraints (XOR content rule, allowed extensions, the
    # "only sanctioned way" semantics), so they get a higher cap than the
    # find_* tools whose entire job was to shed the sermon.
    assert len(description) > 0
    cap = 450 if attr in {"add_document", "ask_user"} else 320
    assert len(description) <= cap, (
        f"{attr} description is still verbose ({len(description)} chars > {cap}); "
        f"Phase 3 target is a concise WHAT-it-finds line. Got: {description!r}"
    )


@pytest.mark.parametrize(
    ("module", "attr"),
    TRIMMED_TOOLS,
    ids=[attr for _, attr in TRIMMED_TOOLS],
)
def test_trimmed_tools_convert_to_valid_openai_schema(
    module: object, attr: str
) -> None:
    """Smoke test: trimmed tools still produce a valid OpenAI tool schema."""
    tool = _resolve(module, attr)
    schema = convert_to_openai_tool(tool)  # must not raise
    # Round-trips through JSON and has the expected OpenAI tool shape.
    serialized = json.dumps(schema, default=str)
    assert '"name"' in serialized
    assert '"description"' in serialized
    assert '"parameters"' in serialized
    # Description in the schema matches the tool's attribute (no truncation).
    assert schema["function"]["description"] == _desc(tool)


def test_add_document_description_keeps_load_bearing_constraints() -> None:
    """Tightened, but the XOR content rule + extension requirement survive."""
    desc = _desc(document_tools.add_document)
    # The two load-bearing rules for calling the tool correctly.
    assert "content" in desc and "base64_content" in desc
    assert "exactly one" in desc.lower(), (
        "add_document must keep the XOR rule (provide exactly one of "
        "content / base64_content)."
    )
    assert "extension" in desc.lower()


def test_ask_user_description_keeps_only_sanctioned_way_semantics() -> None:
    """Tightened, but the 'only sanctioned way' + options hint survive."""
    desc = _desc(ask_user_module.ask_user)
    assert "only" in desc.lower(), (
        "ask_user must keep the 'ONLY sanctioned way to ask' guidance."
    )
    assert "options" in desc.lower()


def test_find_descriptions_keep_one_concise_pagination_hint() -> None:
    """Each find_* tool keeps a SHORT pagination hint (one line), not the sermon."""
    # Every find_* tool should still mention paging so the model knows to page
    # forward -- but as one short clause, not the old multi-sentence block.
    find_tools = [
        project_template.find_wbs_elements,
        cost_element_template.find_cost_elements,
        cost_element_template.find_cost_element_types,
        cost_event_template.find_cost_events,
        cost_event_type_template.find_cost_event_types,
        control_account_template.find_control_accounts,
        work_package_template.find_work_packages,
        change_order_template.find_change_orders,
        user_management_template.find_users,
        user_management_template.find_organizational_units,
    ]
    for tool in find_tools:
        desc = _desc(tool)
        # Must retain a concise paging cue.
        assert "page" in desc.lower() and (
            "has_more" in desc.lower() or "total" in desc.lower()
        ), f"{tool.name} dropped the paging cue entirely: {desc!r}"
