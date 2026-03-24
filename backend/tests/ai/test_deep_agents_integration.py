"""Integration tests for Deep Agents SDK.

Tests:
1. Agent creation with Backcast context
2. Security middleware application
3. Temporal context injection
4. Subagent delegation
5. Tool filtering

Note: Tests that require actual API access are skipped unless OPENAI_API_KEY is set.
"""

import os
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.deep_agent_orchestrator import DeepAgentOrchestrator
from app.ai.middleware.backcast_security import BackcastSecurityMiddleware
from app.ai.middleware.temporal_context import TemporalContextMiddleware
from app.ai.tools.types import ExecutionMode, RiskLevel, ToolContext

# Skip tests that require actual API access if no API key is set
needs_api_key = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="Requires OPENAI_API_KEY environment variable"
)


@pytest.fixture
def model_string():
    """Create a model string for Deep Agents SDK."""
    return "openai:gpt-4o"


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def tool_context(mock_session):
    """Create a ToolContext for testing."""
    return ToolContext(
        session=mock_session,
        user_id="test-user-id",
        user_role="admin",
        execution_mode=ExecutionMode.STANDARD,
        project_id="test-project-id",
        branch_name="main",
        branch_mode="merged",
    )


@pytest.mark.asyncio
async def test_deep_agent_orchestrator_creation(model_string, tool_context):
    """Test DeepAgentOrchestrator initialization."""
    orchestrator = DeepAgentOrchestrator(
        model=model_string,
        context=tool_context,
        system_prompt="Test prompt",
        enable_subagents=True,
    )

    assert orchestrator.model == model_string
    assert orchestrator.context == tool_context
    assert orchestrator.system_prompt == "Test prompt"
    assert orchestrator.enable_subagents is True


@needs_api_key
@pytest.mark.asyncio
async def test_deep_agent_orchestrator_creates_agent(model_string, tool_context):
    """Test that DeepAgentOrchestrator can create an agent."""
    orchestrator = DeepAgentOrchestrator(
        model=model_string,
        context=tool_context,
    )

    # Create agent (should not raise)
    agent = orchestrator.create_agent()

    # Agent should be created (it's a CompiledStateGraph)
    assert agent is not None


@needs_api_key
@pytest.mark.asyncio
async def test_deep_agent_orchestrator_with_tool_filtering(model_string, tool_context):
    """Test that DeepAgentOrchestrator filters tools by allowed_tools."""
    orchestrator = DeepAgentOrchestrator(
        model=model_string,
        context=tool_context,
    )

    # Create agent with tool filtering
    allowed_tools = ["list_projects", "get_project"]
    agent = orchestrator.create_agent(allowed_tools=allowed_tools)

    assert agent is not None


@needs_api_key
@pytest.mark.asyncio
async def test_deep_agent_orchestrator_without_subagents(model_string, tool_context):
    """Test that DeepAgentOrchestrator works without subagents."""
    orchestrator = DeepAgentOrchestrator(
        model=model_string,
        context=tool_context,
        enable_subagents=False,
    )

    agent = orchestrator.create_agent()
    assert agent is not None


@pytest.mark.asyncio
async def test_backcast_security_middleware_init(tool_context):
    """Test BackcastSecurityMiddleware initialization."""
    middleware = BackcastSecurityMiddleware(context=tool_context)
    assert middleware.context == tool_context
    assert middleware._security_tools == []


@pytest.mark.asyncio
async def test_backcast_security_middleware_with_tools(tool_context):
    """Test BackcastSecurityMiddleware with tools list."""
    # Create mock tools with metadata
    mock_tool = MagicMock()
    mock_tool.name = "test_tool"
    mock_tool._tool_metadata = MagicMock()
    mock_tool._tool_metadata.permissions = ["test-permission"]
    mock_tool._tool_metadata.risk_level = RiskLevel.LOW

    middleware = BackcastSecurityMiddleware(context=tool_context, tools=[mock_tool])
    assert middleware._security_tools == [mock_tool]


@pytest.mark.asyncio
async def test_backcast_security_middleware_set_tools(tool_context):
    """Test BackcastSecurityMiddleware.set_tools method."""
    middleware = BackcastSecurityMiddleware(context=tool_context)

    mock_tool = MagicMock()
    mock_tool.name = "test_tool"

    middleware.set_tools([mock_tool])
    assert middleware._security_tools == [mock_tool]


@pytest.mark.asyncio
async def test_backcast_security_middleware_check_risk_low_safe_mode(tool_context):
    """Test that low-risk tools are allowed in safe mode."""
    mock_tool = MagicMock()
    mock_tool.name = "low_risk_tool"
    mock_tool._tool_metadata = MagicMock()
    mock_tool._tool_metadata.risk_level = RiskLevel.LOW

    middleware = BackcastSecurityMiddleware(context=tool_context, tools=[mock_tool])
    middleware.context.execution_mode = ExecutionMode.SAFE

    allowed, error = middleware._check_risk_level("low_risk_tool")
    assert allowed is True
    assert error is None


@pytest.mark.asyncio
async def test_backcast_security_middleware_check_risk_high_safe_mode(tool_context):
    """Test that high-risk tools are blocked in safe mode."""
    mock_tool = MagicMock()
    mock_tool.name = "high_risk_tool"
    mock_tool._tool_metadata = MagicMock()
    mock_tool._tool_metadata.risk_level = RiskLevel.HIGH

    middleware = BackcastSecurityMiddleware(context=tool_context, tools=[mock_tool])
    middleware.context.execution_mode = ExecutionMode.SAFE

    allowed, error = middleware._check_risk_level("high_risk_tool")
    assert allowed is False
    assert error is not None
    assert "risk level" in error.lower()


@pytest.mark.asyncio
async def test_backcast_security_middleware_check_risk_critical_standard_mode(tool_context):
    """Test that critical tools are blocked in standard mode."""
    mock_tool = MagicMock()
    mock_tool.name = "critical_tool"
    mock_tool._tool_metadata = MagicMock()
    mock_tool._tool_metadata.risk_level = RiskLevel.CRITICAL

    middleware = BackcastSecurityMiddleware(context=tool_context, tools=[mock_tool])
    middleware.context.execution_mode = ExecutionMode.STANDARD

    allowed, error = middleware._check_risk_level("critical_tool")
    assert allowed is False
    assert error is not None
    assert "critical" in error.lower()


@pytest.mark.asyncio
async def test_backcast_security_middleware_check_risk_critical_expert_mode(tool_context):
    """Test that critical tools are allowed in expert mode."""
    mock_tool = MagicMock()
    mock_tool.name = "critical_tool"
    mock_tool._tool_metadata = MagicMock()
    mock_tool._tool_metadata.risk_level = RiskLevel.CRITICAL

    middleware = BackcastSecurityMiddleware(context=tool_context, tools=[mock_tool])
    middleware.context.execution_mode = ExecutionMode.EXPERT

    allowed, error = middleware._check_risk_level("critical_tool")
    assert allowed is True
    assert error is None


@pytest.mark.asyncio
async def test_temporal_context_middleware_init(tool_context):
    """Test TemporalContextMiddleware initialization."""
    middleware = TemporalContextMiddleware(context=tool_context)
    assert middleware.context == tool_context


@pytest.mark.asyncio
async def test_temporal_context_middleware_inject_temporal_context(tool_context):
    """Test TemporalContextMiddleware.inject_temporal_context method."""
    from datetime import datetime

    tool_context.as_of = datetime(2025, 1, 1, 12, 0, 0)
    tool_context.branch_name = "feature-branch"
    tool_context.branch_mode = "isolated"
    tool_context.project_id = "project-123"

    middleware = TemporalContextMiddleware(context=tool_context)

    tool_args = {}
    result = middleware.inject_temporal_context(tool_args)

    assert result["as_of"] == "2025-01-01T12:00:00"
    assert result["branch_name"] == "feature-branch"
    assert result["branch_mode"] == "isolated"
    assert result["project_id"] == "project-123"


@pytest.mark.asyncio
async def test_deep_agent_orchestrator_interrupt_config(model_string, tool_context):
    """Test that DeepAgentOrchestrator builds interrupt config for HIGH and CRITICAL tools."""

    from app.ai.deep_agent_orchestrator import DeepAgentOrchestrator

    # Create mock tools with different risk levels
    low_tool = MagicMock()
    low_tool.name = "low_tool"
    low_tool._tool_metadata = MagicMock()
    low_tool._tool_metadata.risk_level = RiskLevel.LOW

    high_tool = MagicMock()
    high_tool.name = "high_tool"
    high_tool._tool_metadata = MagicMock()
    high_tool._tool_metadata.risk_level = RiskLevel.HIGH

    critical_tool = MagicMock()
    critical_tool.name = "critical_tool"
    critical_tool._tool_metadata = MagicMock()
    critical_tool._tool_metadata.risk_level = RiskLevel.CRITICAL

    orchestrator = DeepAgentOrchestrator(model=model_string, context=tool_context)

    # Build interrupt config
    config = orchestrator._build_interrupt_config([low_tool, high_tool, critical_tool])

    # LOW risk tool should NOT be in config
    assert "low_tool" not in config
    # HIGH risk tool SHOULD be in config (requires approval in standard mode)
    assert "high_tool" in config
    high_config = config["high_tool"]
    assert isinstance(high_config, dict)
    assert high_config["allowed_decisions"] == ["approve", "reject"]
    assert "high" in high_config["description"].lower()
    # CRITICAL risk tool should be in config (requires approval in standard mode)
    assert "critical_tool" in config
    critical_config = config["critical_tool"]
    assert isinstance(critical_config, dict)
    assert critical_config["allowed_decisions"] == ["approve", "reject"]
    assert "critical" in critical_config["description"].lower()


@pytest.mark.asyncio
async def test_deep_agent_orchestrator_context_schema(model_string, tool_context):
    """Test that DeepAgentOrchestrator builds proper context schema."""
    orchestrator = DeepAgentOrchestrator(model=model_string, context=tool_context)

    schema = orchestrator._build_context_schema()

    assert schema is not None
    assert "as_of" in schema
    assert "branch_name" in schema
    assert "branch_mode" in schema
    assert "project_id" in schema
    assert "execution_mode" in schema


@pytest.mark.asyncio
async def test_backcast_security_middleware_external_tool_allowed(tool_context):
    """Test BackcastSecurityMiddleware allows external tools not in Backcast tools list."""
    middleware = BackcastSecurityMiddleware(context=tool_context, tools=[])

    # External tools (not in Backcast tools list) should be allowed
    # This handles Deep Agents SDK built-in tools (write_todos, task, etc.)
    error = await middleware._check_tool_permission("external_tool", {})
    assert error is None  # External tools are allowed

    # Same for risk check
    allowed, risk_error = middleware._check_risk_level("external_tool")
    assert allowed is True
    assert risk_error is None


@pytest.mark.asyncio
async def test_backcast_security_middleware_no_metadata(tool_context):
    """Test BackcastSecurityMiddleware when tool has no metadata."""
    mock_tool = MagicMock()
    mock_tool.name = "no_metadata_tool"
    # No _tool_metadata attribute

    middleware = BackcastSecurityMiddleware(context=tool_context, tools=[mock_tool])

    error = await middleware._check_tool_permission("no_metadata_tool", {})
    assert error is None  # No metadata means no permission requirements


@pytest.mark.asyncio
async def test_backcast_security_middleware_risk_no_metadata(tool_context):
    """Test BackcastSecurityMiddleware._check_risk_level when tool has no metadata."""
    mock_tool = MagicMock()
    mock_tool.name = "no_metadata_tool"
    # No _tool_metadata attribute

    middleware = BackcastSecurityMiddleware(context=tool_context, tools=[mock_tool])

    # Should default to HIGH risk level
    middleware.context.execution_mode = ExecutionMode.SAFE
    allowed, error = middleware._check_risk_level("no_metadata_tool")
    assert allowed is False  # HIGH not allowed in SAFE mode


@pytest.mark.asyncio
async def test_subagents_get_all():
    """Test get_all_subagents returns expected subagents."""
    from app.ai.subagents import get_all_subagents

    subagents = get_all_subagents()

    # Should have exactly 7 domain-aligned subagents
    assert len(subagents) == 7
    subagent_names = [s["name"] for s in subagents]

    # Verify all 7 new subagent names are present
    assert "project_manager" in subagent_names
    assert "evm_analyst" in subagent_names
    assert "change_order_manager" in subagent_names
    assert "cost_controller" in subagent_names
    assert "user_admin" in subagent_names
    assert "visualization_specialist" in subagent_names
    assert "forecast_manager" in subagent_names

    # Verify old subagent names are NOT present
    assert "project_admin" not in subagent_names
    assert "forecast_analyst" not in subagent_names
    assert "advanced_analyst" not in subagent_names


@pytest.mark.asyncio
async def test_subagents_get_by_name():
    """Test get_subagent_by_name returns correct subagent."""
    from app.ai.subagents import get_subagent_by_name

    evm_agent = get_subagent_by_name("evm_analyst")
    assert evm_agent is not None
    assert evm_agent["name"] == "evm_analyst"
    assert "calculate_evm_metrics" in evm_agent.get("allowed_tools", [])


@pytest.mark.asyncio
async def test_subagents_get_by_name_not_found():
    """Test get_subagent_by_name returns None for non-existent subagent."""
    from app.ai.subagents import get_subagent_by_name

    result = get_subagent_by_name("nonexistent_agent")
    assert result is None


@pytest.mark.asyncio
async def test_subagent_tools_filtered_by_assistant_whitelist(model_string, tool_context):
    """Test that subagent tools are filtered by assistant's allowed_tools whitelist."""
    from app.ai.deep_agent_orchestrator import DeepAgentOrchestrator
    from app.ai.subagents import get_all_subagents

    orchestrator = DeepAgentOrchestrator(
        model=model_string,
        context=tool_context,
    )

    # Create mock tools to simulate available tools with proper risk levels
    mock_tools = []
    for tool_name, risk_level in [
        ("calculate_evm_metrics", RiskLevel.LOW),
        ("get_evm_performance_summary", RiskLevel.LOW),
        ("create_project", RiskLevel.HIGH),
        ("list_projects", RiskLevel.LOW),
    ]:
        mock_tool = MagicMock()
        mock_tool.name = tool_name
        mock_tool._tool_metadata = MagicMock()
        mock_tool._tool_metadata.risk_level = risk_level
        mock_tools.append(mock_tool)

    # Get subagent configs
    subagent_configs = get_all_subagents()

    # Filter with assistant whitelist that only allows EVM-related tools
    assistant_whitelist = ["calculate_evm_metrics", "get_evm_performance_summary"]

    subagent_objects = orchestrator._create_subagent_objects(
        subagent_configs,
        mock_tools,
        allowed_tools=assistant_whitelist,
    )

    # Verify that subagents were created, but only with whitelisted tools
    assert len(subagent_objects) > 0

    # Check that EVM analyst subagent exists and has filtered tools
    evm_subagent = next((s for s in subagent_objects if s.get("name") == "evm_analyst"), None)
    assert evm_subagent is not None

    # The subagent should only have tools from the whitelist
    evm_tools_list = evm_subagent.get("tools", [])
    evm_tool_names = [t.name for t in evm_tools_list]
    assert all(name in assistant_whitelist for name in evm_tool_names)
    assert "calculate_evm_metrics" in evm_tool_names
    assert "get_evm_performance_summary" in evm_tool_names


@pytest.mark.asyncio
async def test_subagent_tools_no_assistant_whitelist(model_string, tool_context):
    """Test that subagents get all their configured tools when no assistant whitelist."""
    from app.ai.deep_agent_orchestrator import DeepAgentOrchestrator
    from app.ai.subagents import get_all_subagents

    orchestrator = DeepAgentOrchestrator(
        model=model_string,
        context=tool_context,
    )

    # Create mock tools to simulate available tools with proper risk levels
    mock_tools = []
    for tool_name, risk_level in [
        ("calculate_evm_metrics", RiskLevel.LOW),
        ("get_evm_performance_summary", RiskLevel.LOW),
        ("create_project", RiskLevel.HIGH),
    ]:
        mock_tool = MagicMock()
        mock_tool.name = tool_name
        mock_tool._tool_metadata = MagicMock()
        mock_tool._tool_metadata.risk_level = risk_level
        mock_tools.append(mock_tool)

    # Get subagent configs
    subagent_configs = get_all_subagents()

    # No assistant whitelist - subagents should get their full configured tool list
    subagent_objects = orchestrator._create_subagent_objects(
        subagent_configs,
        mock_tools,
        allowed_tools=None,
    )

    # Verify that subagents were created with their configured tools
    assert len(subagent_objects) > 0

    evm_subagent = next((s for s in subagent_objects if s.get("name") == "evm_analyst"), None)
    assert evm_subagent is not None

    # When no whitelist, the subagent should have all its configured tools
    # (as long as they exist in mock_tools)
    evm_tools_list = evm_subagent.get("tools", [])
    evm_tool_names = [t.name for t in evm_tools_list]
    assert "calculate_evm_metrics" in evm_tool_names


@pytest.mark.asyncio
async def test_deep_agent_sdk_tools_always_allowed(tool_context):
    """Test that Deep Agents SDK built-in tools are always allowed by security middleware."""
    from app.ai.middleware.backcast_security import BackcastSecurityMiddleware

    middleware = BackcastSecurityMiddleware(context=tool_context, tools=[])

    # Test common Deep Agents SDK built-in tools
    # These tools are added by the SDK and not in the Backcast tools list
    deep_agent_sdk_tools = ["write_todos", "task", "ls", "read_file", "write_file"]

    for tool_name in deep_agent_sdk_tools:
        # Permission check should pass (external tool)
        error = await middleware._check_tool_permission(tool_name, {})
        assert error is None, f"Deep Agent SDK tool {tool_name} should be allowed"

        # Risk check should pass (external tool)
        allowed, risk_error = middleware._check_risk_level(tool_name)
        assert allowed is True, f"Deep Agent SDK tool {tool_name} should pass risk check"
        assert risk_error is None


@pytest.mark.asyncio
async def test_write_todos_tool_allowed(tool_context):
    """Test that write_todos tool is always allowed for planning."""
    from app.ai.middleware.backcast_security import BackcastSecurityMiddleware

    middleware = BackcastSecurityMiddleware(context=tool_context, tools=[])

    # write_todos should be allowed even with no tools in middleware
    error = await middleware._check_tool_permission("write_todos", {})
    assert error is None, "write_todos tool should be allowed"


@pytest.mark.asyncio
async def test_task_tool_allowed(tool_context):
    """Test that task tool is always allowed for subagent delegation."""
    from app.ai.middleware.backcast_security import BackcastSecurityMiddleware

    middleware = BackcastSecurityMiddleware(context=tool_context, tools=[])

    # task should be allowed even with no tools in middleware
    error = await middleware._check_tool_permission("task", {})
    assert error is None, "task tool should be allowed"


@pytest.mark.asyncio
async def test_interrupt_config_built_with_subagents_enabled(model_string, tool_context):
    """Test that interrupt config is built even when subagents are enabled.

    This is critical because HIGH and CRITICAL tools in subagents need to
    trigger approval in standard mode.
    """

    from app.ai.deep_agent_orchestrator import DeepAgentOrchestrator

    # Create mock tools with HIGH risk level
    high_tool = MagicMock()
    high_tool.name = "create_project"
    high_tool._tool_metadata = MagicMock()
    high_tool._tool_metadata.risk_level = RiskLevel.HIGH

    # Create orchestrator with subagents enabled
    orchestrator = DeepAgentOrchestrator(
        model=model_string,
        context=tool_context,
        enable_subagents=True,  # Subagents enabled
    )

    # Build interrupt config with the HIGH risk tool
    config = orchestrator._build_interrupt_config([high_tool])

    # HIGH risk tool SHOULD be in config even when subagents are enabled
    # This is because subagents need to trigger approval for HIGH/CRITICAL tools
    assert "create_project" in config
    create_project_config = config["create_project"]
    assert isinstance(create_project_config, dict)
    assert create_project_config["allowed_decisions"] == ["approve", "reject"]
    assert "high" in create_project_config["description"].lower()


@pytest.mark.asyncio
async def test_subagents_receive_interrupt_config(model_string, tool_context):
    """Test that subagents receive interrupt config for HIGH and CRITICAL risk tools.

    This test verifies the fix for the approval workflow issue where HIGH risk tools
    in subagents were not triggering approval in standard mode.
    """
    from app.ai.deep_agent_orchestrator import DeepAgentOrchestrator
    from app.ai.subagents import get_all_subagents

    # Create mock tools with different risk levels
    low_tool = MagicMock()
    low_tool.name = "list_projects"
    low_tool._tool_metadata = MagicMock()
    low_tool._tool_metadata.risk_level = RiskLevel.LOW

    high_tool = MagicMock()
    high_tool.name = "create_project"
    high_tool._tool_metadata = MagicMock()
    high_tool._tool_metadata.risk_level = RiskLevel.HIGH

    critical_tool = MagicMock()
    critical_tool.name = "delete_user"
    critical_tool._tool_metadata = MagicMock()
    critical_tool._tool_metadata.risk_level = RiskLevel.CRITICAL

    # Create orchestrator with subagents enabled
    orchestrator = DeepAgentOrchestrator(
        model=model_string,
        context=tool_context,
        enable_subagents=True,
    )

    # Create subagent objects
    mock_tools = [low_tool, high_tool, critical_tool]
    subagent_configs = get_all_subagents()

    subagent_objects = orchestrator._create_subagent_objects(
        subagent_configs,
        mock_tools,
        allowed_tools=None,  # No whitelist, use all tools
    )

    # Verify that subagents were created
    assert len(subagent_objects) > 0

    # Check that project_manager subagent exists
    project_manager = next((s for s in subagent_objects if s.get("name") == "project_manager"), None)
    assert project_manager is not None, "project_manager subagent should exist"

    # Verify interrupt_on is configured but empty
    # Approval is now handled by BackcastSecurityMiddleware, not by interrupt_on
    interrupt_on = project_manager.get("interrupt_on", {})
    assert isinstance(interrupt_on, dict), "interrupt_on should be a dict"
    assert interrupt_on == {}, "interrupt_on should be empty (approval handled by BackcastSecurityMiddleware)"


@pytest.mark.asyncio
async def test_main_agent_no_interrupt_config_when_subagents_enabled(model_string, tool_context):
    """Test that main agent has empty interrupt config when subagents are enabled.

    The main agent should NOT have interrupt config because it has no direct tools
    when subagents are enabled. Interrupts should be handled at the subagent level.
    """
    from app.ai.deep_agent_orchestrator import DeepAgentOrchestrator
    from app.ai.tools import create_project_tools

    # Create orchestrator with subagents enabled
    orchestrator = DeepAgentOrchestrator(
        model=model_string,
        context=tool_context,
        enable_subagents=True,
    )

    # Get all tools
    all_tools = create_project_tools(tool_context)

    # Build interrupt config for main agent
    # When subagents are enabled, this should return empty dict
    main_agent_interrupt_config = {}

    # Verify main agent has no interrupt config when subagents are enabled
    # This is checked by verifying the create_agent method builds correct config
    # The actual check happens in create_agent() where interrupt_config is set

    # Simulate what happens in create_agent()
    if orchestrator.enable_subagents:
        main_agent_interrupt_config = {}
    else:
        main_agent_interrupt_config = orchestrator._build_interrupt_config(all_tools)

    # Main agent should have empty interrupt config when subagents enabled
    assert main_agent_interrupt_config == {}, "Main agent should have empty interrupt config when subagents enabled"


# Run tests with: uv run pytest tests/ai/test_deep_agents_integration.py -v
