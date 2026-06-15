"""Unit tests for the ``render_prompt`` braced-tag helper.

Each test maps to one of the robustness properties documented in the module
docstring of :mod:`app.ai.prompt_template`.
"""

from __future__ import annotations

from typing import Any

from app.ai.prompt_template import render_prompt
from app.ai.tools.subagent_task import build_task_tool


def test_known_tag_substituted() -> None:
    """A known tag is replaced with its value."""
    assert render_prompt("Hello {name}!", name="World") == "Hello World!"


def test_stray_braces_in_template_left_verbatim() -> None:
    """Braces that aren't a known tag are left as-is (no raise)."""
    assert render_prompt("Ratio is {a}/{b}", a="3") == "Ratio is 3/{b}"


def test_unmatched_open_brace_left_verbatim() -> None:
    """An unmatched ``{`` without a closing ``}`` is left as-is."""
    assert render_prompt("Open { but no close", a="x") == "Open { but no close"


def test_attribute_access_not_dereferenced() -> None:
    """``{x.attr}`` is not matched by the tag pattern, so left verbatim."""
    assert render_prompt("See {x.attr} here", x="v") == "See {x.attr} here"


def test_index_access_not_dereferenced() -> None:
    """``{x[0]}`` is not matched by the tag pattern, so left verbatim."""
    assert render_prompt("Item {x[0]} done", x="v") == "Item {x[0]} done"


def test_value_containing_braces_not_re_substituted() -> None:
    """Injected values are never re-scanned, so braces in a value are inert."""
    assert (
        render_prompt("Wrap {tag}", tag="{__class__} secret")
        == "Wrap {__class__} secret"
    )


def test_value_containing_same_tag_name_not_double_substituted() -> None:
    """A value containing the literal ``{tag}`` text is not re-expanded."""
    assert render_prompt("body {tag} end", tag="{tag}") == "body {tag} end"


def test_dunder_class_content_inert() -> None:
    """``{__class__}`` is treated as an unknown tag (not dereferenced)."""
    assert render_prompt("Type {__class__} here", name="x") == "Type {__class__} here"


def test_all_occurrences_replaced() -> None:
    """Every occurrence of a known tag is substituted (replace-all)."""
    assert render_prompt("{a} and {a} and {a}", a="Z") == "Z and Z and Z"


def test_empty_value() -> None:
    """An empty-string value substitutes to nothing."""
    assert render_prompt("a{name}b", name="") == "ab"


def test_unknown_tag_left_verbatim_no_raise() -> None:
    """An unknown tag is left verbatim without raising."""
    assert (
        render_prompt("Known {a}, unknown {missing}", a="1")
        == "Known 1, unknown {missing}"
    )


def test_multiple_known_tags() -> None:
    """Multiple distinct known tags in one template are all substituted."""
    assert (
        render_prompt(
            "{specialist_section} + {plan_section} + {available_agents}",
            specialist_section="S",
            plan_section="P",
            available_agents="A",
        )
        == "S + P + A"
    )


# ---------------------------------------------------------------------------
# Regression: build_task_tool no longer crashes on brace-laden descriptions.
#
# This is the live bug the migration fixes. ``build_task_tool`` previously
# called ``task_description.format(available_agents=...)`` where
# ``task_description`` can be a DB-stored admin template. A stray or unmatched
# brace in that template raised ValueError at tool-construction time.
# ``render_prompt`` leaves stray/unknown braces verbatim, so the tool builds.
# Confirmed empirically: with the old ``.format()`` this raises
# ``ValueError: expected '}' before end of string``.
# ---------------------------------------------------------------------------


def _fake_subagents() -> list[dict[str, Any]]:
    return [
        {
            "name": "evm_analyst",
            "description": "EVM metric analysis",
            "runnable": object(),
            "structured_output_schema": None,
        }
    ]


def test_build_task_tool_custom_template_with_unmatched_brace() -> None:
    """A DB-stored task_description with an unmatched brace must not crash."""
    bad_template = (
        "Launch subagent. Available: {available_agents}. Note: see {unmatched section"
    )
    tool = build_task_tool(_fake_subagents(), task_description=bad_template)
    assert tool.name == "task"
    # The known tag is resolved; the unmatched brace is left verbatim.
    assert "- evm_analyst: EVM metric analysis" in tool.description
    assert "{unmatched section" in tool.description


def test_build_task_tool_custom_template_with_attr_brace() -> None:
    """A ``{x.attr}``-style brace in a DB template must not be dereferenced."""
    template = "Agents: {available_agents} | format like {x.attr} here"
    tool = build_task_tool(_fake_subagents(), task_description=template)
    assert tool.name == "task"
    assert "{x.attr}" in tool.description  # left verbatim
    assert "- evm_analyst:" in tool.description  # known tag resolved
