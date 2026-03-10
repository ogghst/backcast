"""Test that CRUD tool template is syntactically correct and can be imported."""

import pytest


def test_crud_template_can_be_imported() -> None:
    """Test that the CRUD template can be imported without errors."""
    # This test just verifies the template is syntactically correct
    # We don't execute the functions, just import them
    try:
        from app.ai.tools.templates import crud_template
        assert crud_template is not None
    except Exception as e:
        pytest.fail(f"Failed to import CRUD template: {e}")


def test_crud_template_has_required_functions() -> None:
    """Test that the CRUD template has all required example functions."""
    from app.ai.tools.templates import crud_template

    # Check that all CRUD functions exist
    assert hasattr(crud_template, "list_projects")
    assert hasattr(crud_template, "get_project")
    assert hasattr(crud_template, "create_project")
    assert hasattr(crud_template, "update_project")
    assert hasattr(crud_template, "list_wbes")
    assert hasattr(crud_template, "get_wbe")
    assert hasattr(crud_template, "create_wbe")


def test_crud_template_functions_have_decorators() -> None:
    """Test that CRUD template functions have @ai_tool decorators."""
    from app.ai.tools.templates import crud_template

    # Check that functions have the _is_ai_tool attribute set by decorator
    functions = [
        "list_projects",
        "get_project",
        "create_project",
        "update_project",
        "list_wbes",
        "get_wbe",
        "create_wbe",
    ]

    for func_name in functions:
        func = getattr(crud_template, func_name)
        # All should have _is_ai_tool attribute from decorator
        assert hasattr(func, "_is_ai_tool"), f"{func_name} missing @ai_tool decorator"
        assert func._is_ai_tool is True, f"{func_name} decorator not properly applied"
