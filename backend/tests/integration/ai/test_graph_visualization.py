"""Integration tests for graph visualization export."""

from unittest.mock import Mock

import pytest

from app.ai.graph import create_graph, export_graphviz
from app.ai.tools.project_tools import get_project, list_projects
from app.ai.tools.types import ToolContext


@pytest.mark.asyncio
async def test_export_graphviz_produces_valid_dot_format():
    """Test that export_graphviz() produces valid DOT format.

    This is a RED test - the function doesn't exist yet.

    Expected behavior:
    - Returns a non-empty string
    - Contains valid DOT format keywords (digraph, node, edge)
    - Includes graph structure information
    """
    # Arrange: Create a simple graph for testing
    mock_llm = Mock()
    mock_session = Mock()
    context = ToolContext(
        session=mock_session,  # Mock for testing
        user_id="test-user",
    )

    # Create tools from @ai_tool decorated functions
    from app.ai.tools.decorator import to_langchain_tool

    tools = [
        to_langchain_tool(list_projects, context),
        to_langchain_tool(get_project, context),
    ]

    graph = create_graph(mock_llm, tools)

    # Act: Export graph to DOT format
    dot_output = export_graphviz(graph)

    # Assert: Verify DOT format validity
    assert isinstance(dot_output, str), "export_graphviz should return a string"
    assert len(dot_output) > 0, "DOT output should not be empty"

    # Check for DOT format keywords
    assert "digraph" in dot_output.lower(), "DOT format should contain 'digraph'"
    assert "{" in dot_output and "}" in dot_output, "DOT format should contain braces"

    # Check for node/edge representations
    # DOT graphs typically contain node definitions or edge definitions
    # The exact format depends on the implementation

    # Verify it's structured as a valid DOT graph
    lines = dot_output.strip().split("\n")
    assert len(lines) > 1, "DOT output should have multiple lines"

    # First line should declare the graph type
    first_line = lines[0].strip()
    assert first_line.startswith("digraph"), "First line should declare digraph"


@pytest.mark.asyncio
async def test_export_graphviz_includes_node_information():
    """Test that export_graphviz() includes node information.

    Expected behavior:
    - Includes agent node
    - Includes tools node
    - Shows node connections
    """
    # Arrange
    mock_llm = Mock()
    mock_session = Mock()
    context = ToolContext(
        session=mock_session,
        user_id="test-user",
    )

    from app.ai.tools.decorator import to_langchain_tool

    tools = [
        to_langchain_tool(list_projects, context),
    ]

    graph = create_graph(mock_llm, tools)

    # Act
    dot_output = export_graphviz(graph)

    # Assert
    # Should contain references to the nodes in our graph
    # The exact format depends on implementation, but should include:
    # - Agent node
    # - Tools node
    assert "agent" in dot_output.lower() or "node" in dot_output.lower(), (
        "DOT output should reference graph nodes"
    )


@pytest.mark.asyncio
async def test_export_graphviz_handles_empty_gracefully():
    """Test that export_graphviz() handles edge cases gracefully.

    Expected behavior:
    - Doesn't crash on minimal graphs
    - Returns valid DOT even with no tools
    """
    # Arrange: Create graph with no tools
    mock_llm = Mock()
    graph = create_graph(mock_llm, [])

    # Act
    dot_output = export_graphviz(graph)

    # Assert
    assert dot_output is not None, "Should return output even for empty tool list"
    assert isinstance(dot_output, str), "Should return string"
    # Should still be valid DOT format
    assert "digraph" in dot_output.lower() or "graph" in dot_output.lower(), (
        "Should contain graph declaration"
    )


@pytest.mark.asyncio
async def test_export_graphviz_is_deterministic():
    """Test that export_graphviz() produces consistent output.

    Expected behavior:
    - Same graph produces same DOT output
    - Output is stable across multiple calls
    """
    # Arrange
    mock_llm = Mock()
    mock_session = Mock()
    context = ToolContext(
        session=mock_session,
        user_id="test-user",
    )

    from app.ai.tools.decorator import to_langchain_tool

    tools = [
        to_langchain_tool(list_projects, context),
    ]

    graph = create_graph(mock_llm, tools)

    # Act: Export twice
    dot_output_1 = export_graphviz(graph)
    dot_output_2 = export_graphviz(graph)

    # Assert: Should be identical
    assert dot_output_1 == dot_output_2, (
        "export_graphviz should produce deterministic output"
    )
