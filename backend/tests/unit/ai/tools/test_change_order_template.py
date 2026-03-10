"""Test that Change Order tool template is syntactically correct and can be imported."""

import pytest


def test_change_order_template_can_be_imported() -> None:
    """Test that the Change Order template can be imported without errors."""
    try:
        from app.ai.tools.templates import change_order_template
        assert change_order_template is not None
    except Exception as e:
        pytest.fail(f"Failed to import Change Order template: {e}")


def test_change_order_template_has_required_functions() -> None:
    """Test that the Change Order template has all required example functions."""
    from app.ai.tools.templates import change_order_template

    # Check that all Change Order functions exist
    assert hasattr(change_order_template, "list_change_orders")
    assert hasattr(change_order_template, "get_change_order")
    assert hasattr(change_order_template, "create_change_order")
    assert hasattr(change_order_template, "generate_change_order_draft")
    assert hasattr(change_order_template, "submit_change_order_for_approval")
    assert hasattr(change_order_template, "approve_change_order")
    assert hasattr(change_order_template, "reject_change_order")
    assert hasattr(change_order_template, "analyze_change_order_impact")


def test_change_order_template_functions_have_decorators() -> None:
    """Test that Change Order template functions have @ai_tool decorators."""
    from app.ai.tools.templates import change_order_template

    # Check that functions have the _is_ai_tool attribute set by decorator
    functions = [
        "list_change_orders",
        "get_change_order",
        "create_change_order",
        "generate_change_order_draft",
        "submit_change_order_for_approval",
        "approve_change_order",
        "reject_change_order",
        "analyze_change_order_impact",
    ]

    for func_name in functions:
        func = getattr(change_order_template, func_name)
        # All should have _is_ai_tool attribute from decorator
        assert hasattr(func, "_is_ai_tool"), f"{func_name} missing @ai_tool decorator"
        assert func._is_ai_tool is True, f"{func_name} decorator not properly applied"
